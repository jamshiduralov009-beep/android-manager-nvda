"""
Android Emulator Boshqaruv Paneli
NVDA Screen Reader bilan to'liq mos keladi.

Qo'llab-quvvatlanadigan emulyatorlar:
  - BlueStacks 5 / BlueStacks X
  - LDPlayer 9
  - NoxPlayer
  - WSA (Windows Subsystem for Android)
  - MuMu Player
  - Genymotion

Muallif: Jamshid Uralov
GitHub: github.com/jamshiduralov009-beep/android-manager-nvda
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import threading
import os
import sys

# ─── ADB yo'llari ────────────────────────────────────────────────────────────

ADB_LOCATIONS = [
    "adb",
    r"C:\Users\Jamshid\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe",
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files (x86)\BlueStacks\HD-Adb.exe",
    r"C:\LDPlayer\LDPlayer9\adb.exe",
    r"C:\Program Files\Nox\bin\adb.exe",
    r"C:\Program Files (x86)\Nox\bin\adb.exe",
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 "Android", "Sdk", "platform-tools", "adb.exe"),
]

# Emulyator portlari
EMULATOR_PORTS = {
    "BlueStacks":  ["127.0.0.1:5555", "127.0.0.1:5556",
                    "127.0.0.1:5565", "127.0.0.1:5575"],
    "LDPlayer":    ["127.0.0.1:5555", "127.0.0.1:5556",
                    "emulator-5554", "emulator-5556"],
    "NoxPlayer":   ["127.0.0.1:62001"],
    "WSA":         ["127.0.0.1:58526"],
    "MuMu":        ["127.0.0.1:7555"],
    "Genymotion":  ["192.168.56.101:5555"],
}


# ─── ADB funksiyalari ─────────────────────────────────────────────────────────

def find_adb():
    for path in ADB_LOCATIONS:
        try:
            r = subprocess.run(
                [path, "version"],
                capture_output=True, timeout=3
            )
            if r.returncode == 0:
                return path
        except Exception:
            continue
    return None


def adb(cmd_list, adb_path, timeout=20):
    """ADB buyrug'ini ishga tushirib, (stdout, stderr, kod) qaytaradi."""
    try:
        r = subprocess.run(
            [adb_path] + cmd_list,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "Vaqt tugadi", 1
    except FileNotFoundError:
        return "", "ADB topilmadi", 1
    except Exception as e:
        return "", str(e), 1


def connect_emulator(port, adb_path):
    out, err, code = adb(["connect", port], adb_path, timeout=5)
    return "connected" in out.lower() or "already" in out.lower()


def get_devices(adb_path):
    out, _, _ = adb(["devices"], adb_path)
    devices = []
    for line in out.splitlines():
        line = line.strip()
        if line and "List of" not in line and "\t" in line:
            serial, state = line.split("\t", 1)
            if state.strip() == "device":
                devices.append(serial.strip())
    return devices


def get_packages(serial, adb_path, system=False):
    flag = [] if system else ["-3"]
    out, _, _ = adb(["-s", serial, "shell", "pm", "list", "packages"] + flag,
                    adb_path, timeout=30)
    pkgs = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("package:"):
            pkgs.append(line[8:].strip())
    return sorted(pkgs)


def launch_app(serial, pkg, adb_path):
    out, err, code = adb(
        ["-s", serial, "shell", "monkey", "-p", pkg,
         "-c", "android.intent.category.LAUNCHER", "1"],
        adb_path,
    )
    return code == 0, out + err


def stop_app(serial, pkg, adb_path):
    out, err, code = adb(["-s", serial, "shell", "am", "force-stop", pkg], adb_path)
    return code == 0


def uninstall_app(serial, pkg, adb_path):
    out, err, code = adb(["-s", serial, "uninstall", pkg], adb_path)
    return "Success" in out


def clear_data(serial, pkg, adb_path):
    out, err, code = adb(["-s", serial, "shell", "pm", "clear", pkg], adb_path)
    return "Success" in out


def get_app_info(serial, pkg, adb_path):
    out, _, _ = adb(["-s", serial, "shell", "dumpsys", "package", pkg], adb_path, 15)
    info = {}
    for line in out.splitlines():
        line = line.strip()
        for key in ["versionName", "versionCode", "firstInstallTime",
                    "lastUpdateTime", "dataDir"]:
            if key + "=" in line:
                val = line.split("=", 1)[-1].strip()
                info[key] = val
    return info


# ─── Asosiy oyna ─────────────────────────────────────────────────────────────
#
# NVDA uchun maxsus qoidalar:
#   1. Barcha interaktiv elementlar klaviatura orqali bosilishi kerak
#   2. tk.Listbox ishlatiladi (Treeview emas — NVDA Treeview'ni qiyin o'qiydi)
#   3. tk.Button'lar oddiy matn bilan — emoji minimal
#   4. Har bir tugmada aniq, qisqa matn
#   5. messagebox ishlatiladi — NVDA uni to'liq o'qiydi
#   6. Focus boshqaruvi to'g'ri
#   7. Tab tartib to'g'ri
#
# ─────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()

        # ── Oyna sozlamalari ──────────────────────────────────────────────
        self.title("Android Emulator Paneli - NVDA")
        self.geometry("860x600")
        self.minsize(640, 480)
        self.configure(bg="#f0f0f0")   # Oddiy Windows rangi — NVDA uchun eng mos

        # ── Holat o'zgaruvchilari ─────────────────────────────────────────
        self.adb_path   = find_adb()
        self.devices    = []
        self.packages   = []
        self.shown_pkgs = []           # Qidiruv filterlangani

        # ── UI ───────────────────────────────────────────────────────────
        self._menu()
        self._toolbar()
        self._body()
        self._statusbar()

        # ── Klaviatura yorliqlari ─────────────────────────────────────────
        self.bind("<F5>",          lambda e: self._cmd_refresh_devices())
        self.bind("<F6>",          lambda e: self._cmd_load_apps())
        self.bind("<Control-q>",   lambda e: self.destroy())

        # ── Ishga tushish ─────────────────────────────────────────────────
        if self.adb_path:
            self._set_status(f"ADB topildi: {self.adb_path}")
            self.after(600, self._cmd_refresh_devices)
        else:
            self._set_status("ADB topilmadi. Emulyatorni yoqib, F5 bosing.")
            messagebox.showwarning(
                "ADB topilmadi",
                "ADB dasturi topilmadi.\n\n"
                "Iltimos:\n"
                "1. BlueStacks, LDPlayer yoki boshqa emulyatorni yoqing.\n"
                "2. Dastur otomatik ADB ni topadi.\n"
                "3. F5 ni bosing.",
            )

    # ════════════════════ UI QURILISHI ════════════════════════════════════════

    def _menu(self):
        """Menyu — NVDA Alt orqali o'qiydi."""
        mb = tk.Menu(self)
        self.config(menu=mb)

        # Bog'lanish
        m_conn = tk.Menu(mb, tearoff=0)
        m_conn.add_command(
            label="Emulyatorni aniqlash  F5",
            command=self._cmd_refresh_devices,
            accelerator="F5",
        )
        m_conn.add_command(
            label="Qo'lda IP:port ulash",
            command=self._cmd_manual_connect,
        )
        m_conn.add_separator()
        m_conn.add_command(label="Dasturdan chiqish  Ctrl+Q",
                           command=self.destroy, accelerator="Ctrl+Q")
        mb.add_cascade(label="Bog'lanish", menu=m_conn)

        # Ilovalar
        m_app = tk.Menu(mb, tearoff=0)
        m_app.add_command(label="Foydalanuvchi ilovalarini yuklash  F6",
                          command=self._cmd_load_apps, accelerator="F6")
        m_app.add_command(label="Barcha ilovalarni yuklash",
                          command=self._cmd_load_all_apps)
        m_app.add_separator()
        m_app.add_command(label="Ilovani ishga tushirish  Enter",
                          command=self._cmd_launch)
        m_app.add_command(label="Ilovani to'xtatish",
                          command=self._cmd_stop)
        m_app.add_command(label="Ilova ma'lumotlari",
                          command=self._cmd_info)
        m_app.add_separator()
        m_app.add_command(label="Kesh va ma'lumotlarni tozalash",
                          command=self._cmd_clear_data)
        m_app.add_command(label="Ilovani o'chirish  Delete",
                          command=self._cmd_uninstall)
        mb.add_cascade(label="Ilovalar", menu=m_app)

        # Yordam
        m_help = tk.Menu(mb, tearoff=0)
        m_help.add_command(label="Keyboard yorliqlari", command=self._dlg_shortcuts)
        m_help.add_command(label="Dastur haqida",       command=self._dlg_about)
        mb.add_cascade(label="Yordam", menu=m_help)

    def _toolbar(self):
        """Tugmalar paneli."""
        bar = tk.Frame(self, bg="#e1e1e1", bd=1, relief=tk.SUNKEN)
        bar.pack(side=tk.TOP, fill=tk.X)

        def btn(parent, text, cmd):
            b = tk.Button(
                parent, text=text, command=cmd,
                relief=tk.RAISED, padx=6, pady=3,
                font=("Segoe UI", 9),
            )
            b.pack(side=tk.LEFT, padx=2, pady=2)
            return b

        btn(bar, "Aniqlash (F5)",     self._cmd_refresh_devices)
        btn(bar, "Ilovalar (F6)",     self._cmd_load_apps)
        btn(bar, "Ishga tushirish",   self._cmd_launch)
        btn(bar, "To'xtatish",        self._cmd_stop)
        btn(bar, "Ma'lumotlar",       self._cmd_info)
        btn(bar, "Kesh tozalash",     self._cmd_clear_data)
        btn(bar, "O'chirish (Del)",   self._cmd_uninstall)

        # Qurilma tanlash
        tk.Label(bar, text="  Qurilma:", bg="#e1e1e1",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 2))

        self.dev_var = tk.StringVar(value="Hech qanday qurilma")
        self.dev_listbox_bar = tk.OptionMenu(bar, self.dev_var, "Hech qanday qurilma")
        self.dev_listbox_bar.config(font=("Segoe UI", 9), width=24)
        self.dev_listbox_bar.pack(side=tk.LEFT, padx=2)

    def _body(self):
        """Asosiy maydon: chap — ro'yxat, o'ng — ma'lumotlar."""
        body = tk.Frame(self, bg="#f0f0f0")
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # ── Chap ustun ───────────────────────────────────────────────────
        left = tk.Frame(body, bg="#f0f0f0")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Sarlavha (NVDA h tugmasi bilan sarlavhalarga sakrashi uchun)
        tk.Label(
            left,
            text="O'rnatilgan ilovalar",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0",
            anchor="w",
        ).pack(fill=tk.X)

        # Qidiruv
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter)
        search = tk.Entry(
            left,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
        )
        search.pack(fill=tk.X, pady=(2, 4))
        # Placeholder o'rniga label
        tk.Label(left, text="(Yuqorida qidiruv maydoni)",
                 font=("Segoe UI", 8), bg="#f0f0f0", fg="#666").pack(anchor="w")

        # Listbox + Scrollbar
        lf = tk.Frame(left, bg="#f0f0f0")
        lf.pack(fill=tk.BOTH, expand=True)

        sb_y = tk.Scrollbar(lf, orient=tk.VERTICAL)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(
            lf,
            yscrollcommand=sb_y.set,
            font=("Consolas", 10),
            activestyle="underline",
            selectmode=tk.SINGLE,
            exportselection=False,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        sb_y.config(command=self.listbox.yview)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Return>",          lambda e: self._cmd_launch())
        self.listbox.bind("<Delete>",          lambda e: self._cmd_uninstall())

        self.count_lbl = tk.Label(
            left, text="0 ta ilova", font=("Segoe UI", 9),
            bg="#f0f0f0", anchor="w",
        )
        self.count_lbl.pack(anchor="w")

        # ── Ajratuvchi ───────────────────────────────────────────────────
        tk.Frame(body, width=4, bg="#c0c0c0").pack(
            side=tk.LEFT, fill=tk.Y, padx=4
        )

        # ── O'ng ustun ───────────────────────────────────────────────────
        right = tk.Frame(body, bg="#f0f0f0", width=320)
        right.pack(side=tk.LEFT, fill=tk.BOTH)
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Ilova ma'lumotlari va log",
            font=("Segoe UI", 10, "bold"),
            bg="#f0f0f0",
            anchor="w",
        ).pack(fill=tk.X)

        # Ma'lumotlar maydoni — oddiy Text (NVDA o'qiydi)
        txt_scroll = tk.Scrollbar(right, orient=tk.VERTICAL)
        txt_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.info_box = tk.Text(
            right,
            yscrollcommand=txt_scroll.set,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            width=38,
        )
        self.info_box.pack(fill=tk.BOTH, expand=True)
        txt_scroll.config(command=self.info_box.yview)

    def _statusbar(self):
        """Status bar — NVDA NVDA+End bilan o'qiydi."""
        self.status_var = tk.StringVar(value="Tayyor.")
        bar = tk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor="w",
            padx=6,
            font=("Segoe UI", 9),
        )
        bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ════════════════════ YORDAMCHI METODLAR ═════════════════════════════════

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _log(self, text: str, clear=False):
        self.info_box.config(state=tk.NORMAL)
        if clear:
            self.info_box.delete("1.0", tk.END)
        self.info_box.insert(tk.END, text + "\n")
        self.info_box.see(tk.END)
        self.info_box.config(state=tk.DISABLED)

    def _selected_pkg(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning(
                "Tanlanmagan",
                "Avval ro'yxatdan ilova tanlang.\n"
                "Strelka tugmalari bilan yuring, keyin amalni bajaring.",
            )
            return None
        idx = sel[0]
        if idx >= len(self.shown_pkgs):
            return None
        return self.shown_pkgs[idx]

    def _selected_device(self):
        d = self.dev_var.get()
        if not d or d == "Hech qanday qurilma":
            messagebox.showerror(
                "Qurilma yo'q",
                "Emulyator topilmadi.\n\n"
                "Iltimos:\n"
                "1. BlueStacks, LDPlayer yoki boshqa emulyatorni yoqing.\n"
                "2. F5 ni bosing.",
            )
            return None
        return d

    def _run_bg(self, fn, *args):
        """Funksiyani background threadda ishlatadi."""
        threading.Thread(target=fn, args=args, daemon=True).start()

    # ════════════════════ QURILMA AMALLARI ═══════════════════════════════════

    def _cmd_refresh_devices(self):
        if not self.adb_path:
            self.adb_path = find_adb()
        if not self.adb_path:
            messagebox.showerror(
                "ADB topilmadi",
                "Platform Tools o'rnatilmagan yoki emulyator yoqilmagan.\n\n"
                "BlueStacks yoki LDPlayer ni yoqib, qayta urining.",
            )
            return
        self._set_status("Emulyatorlar aniqlanmoqda...")
        self._log("Emulyatorlar qidirilmoqda...", clear=True)
        self._run_bg(self._bg_refresh_devices)

    def _bg_refresh_devices(self):
        # Avval ma'lum portlarga ulanib ko'ramiz
        for emu, ports in EMULATOR_PORTS.items():
            for port in ports:
                connect_emulator(port, self.adb_path)

        devices = get_devices(self.adb_path)
        self.devices = devices
        self.after(0, self._update_device_list, devices)

    def _update_device_list(self, devices):
        menu = self.dev_listbox_bar["menu"]
        menu.delete(0, tk.END)
        if devices:
            for d in devices:
                menu.add_command(
                    label=d,
                    command=lambda v=d: self.dev_var.set(v),
                )
            self.dev_var.set(devices[0])
            self._set_status(f"{len(devices)} ta emulyator/qurilma topildi.")
            self._log(
                f"Topilgan qurilmalar ({len(devices)} ta):\n"
                + "\n".join(f"  - {d}" for d in devices)
                + "\n\nIlovalarni yuklash uchun F6 ni bosing.",
                clear=True,
            )
        else:
            menu.add_command(
                label="Hech qanday qurilma",
                command=lambda: self.dev_var.set("Hech qanday qurilma"),
            )
            self.dev_var.set("Hech qanday qurilma")
            self._set_status("Emulyator topilmadi. Emulyatorni yoqib F5 bosing.")
            self._log(
                "Emulyator topilmadi.\n\n"
                "Nima qilish kerak:\n"
                "1. BlueStacks 5 yoki LDPlayer 9 ni ishga tushiring.\n"
                "2. Emulyator to'liq yuklanishini kuting.\n"
                "3. F5 ni bosing.\n\n"
                "Yoki: 'Bog'lanish > Qo'lda IP:port ulash' menyusini ishting.",
                clear=True,
            )

    def _cmd_manual_connect(self):
        addr = simpledialog.askstring(
            "Qo'lda ulash",
            "IP:port kiriting (masalan: 127.0.0.1:5555):",
            parent=self,
        )
        if not addr:
            return
        self._set_status(f"Ulanmoqda: {addr}")
        self._run_bg(self._bg_manual_connect, addr.strip())

    def _bg_manual_connect(self, addr):
        ok = connect_emulator(addr, self.adb_path)
        devices = get_devices(self.adb_path)
        self.devices = devices
        if ok or devices:
            self.after(0, self._update_device_list, devices)
            self.after(0, self._set_status, f"Ulandi: {addr}")
        else:
            self.after(0, self._set_status, f"Ulanmadi: {addr}")
            self.after(0, messagebox.showerror, "Ulanmadi",
                       f"'{addr}' ga ulanib bo'lmadi.\n"
                       "Emulyator ishlab turganini tekshiring.")

    # ════════════════════ ILOVA AMALLARI ═════════════════════════════════════

    def _cmd_load_apps(self):
        dev = self._selected_device()
        if not dev:
            return
        self._set_status("Ilovalar yuklanmoqda...")
        self._log("Foydalanuvchi ilovalari yuklanmoqda...", clear=True)
        self._run_bg(self._bg_load_apps, dev, False)

    def _cmd_load_all_apps(self):
        dev = self._selected_device()
        if not dev:
            return
        self._set_status("Barcha ilovalar yuklanmoqda...")
        self._log("Barcha ilovalar yuklanmoqda (tizim ham)...", clear=True)
        self._run_bg(self._bg_load_apps, dev, True)

    def _bg_load_apps(self, dev, system):
        pkgs = get_packages(dev, self.adb_path, system)
        self.packages = pkgs
        self.after(0, self._populate_list, pkgs)

    def _populate_list(self, pkgs):
        self.shown_pkgs = list(pkgs)
        self.listbox.delete(0, tk.END)
        for p in pkgs:
            self.listbox.insert(tk.END, p)
        n = len(pkgs)
        self.count_lbl.config(text=f"{n} ta ilova")
        self._set_status(f"{n} ta ilova yuklandi. Strelka bilan tanlang.")
        self._log(
            f"Jami {n} ta ilova topildi.\n\n"
            "Qidiruv maydoni: paket nomini yozing.\n"
            "Enter: ishga tushirish.\n"
            "Delete: o'chirish.",
            clear=True,
        )
        if pkgs:
            self.listbox.focus_set()
            self.listbox.selection_set(0)
            self.listbox.activate(0)

    def _filter(self, *args):
        q = self.search_var.get().lower().strip()
        if q:
            filtered = [p for p in self.packages if q in p.lower()]
        else:
            filtered = list(self.packages)
        self.shown_pkgs = filtered
        self.listbox.delete(0, tk.END)
        for p in filtered:
            self.listbox.insert(tk.END, p)
        self.count_lbl.config(text=f"{len(filtered)} ta ilova")

    def _on_select(self, event=None):
        pkg = self._selected_pkg()
        if not pkg:
            return
        self._set_status(f"Tanlandi: {pkg}")
        dev = self.dev_var.get()
        if dev and dev != "Hech qanday qurilma":
            self._run_bg(self._bg_show_info, dev, pkg)

    def _bg_show_info(self, dev, pkg):
        info = get_app_info(dev, pkg, self.adb_path)
        lines = [f"Paket: {pkg}", ""]
        for k, v in info.items():
            labels = {
                "versionName":      "Versiya",
                "versionCode":      "Versiya kodi",
                "firstInstallTime": "O'rnatilgan vaqt",
                "lastUpdateTime":   "Yangilangan vaqt",
                "dataDir":          "Ma'lumotlar papkasi",
            }
            lines.append(f"{labels.get(k, k)}: {v}")
        self.after(0, self._log, "\n".join(lines), True)

    def _cmd_launch(self):
        pkg = self._selected_pkg()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        self._set_status(f"Ishga tushirilmoqda: {pkg}")
        self._run_bg(self._bg_launch, dev, pkg)

    def _bg_launch(self, dev, pkg):
        ok, msg = launch_app(dev, pkg, self.adb_path)
        if ok:
            self.after(0, self._set_status, f"Ishga tushirildi: {pkg}")
            self.after(0, self._log, f"Muvaffaqiyat: {pkg} ishga tushdi.")
        else:
            self.after(0, self._set_status, "Xato: ishga tushirish amalga oshmadi.")
            self.after(0, messagebox.showerror, "Xato",
                       f"'{pkg}' ishga tushmadi.\n\n{msg}")

    def _cmd_stop(self):
        pkg = self._selected_pkg()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        self._run_bg(self._bg_stop, dev, pkg)

    def _bg_stop(self, dev, pkg):
        ok = stop_app(dev, pkg, self.adb_path)
        msg = f"To'xtatildi: {pkg}" if ok else f"To'xtatilmadi: {pkg}"
        self.after(0, self._set_status, msg)
        self.after(0, self._log, msg)

    def _cmd_info(self):
        self._on_select()

    def _cmd_clear_data(self):
        pkg = self._selected_pkg()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        if not messagebox.askyesno(
            "Tasdiqlang",
            f"'{pkg}' ilovasining barcha kesh va ma'lumotlari o'chiriladi.\n\n"
            "Davom etamizmi?",
        ):
            return
        self._run_bg(self._bg_clear_data, dev, pkg)

    def _bg_clear_data(self, dev, pkg):
        ok = clear_data(dev, pkg, self.adb_path)
        msg = f"Tozalandi: {pkg}" if ok else f"Tozalanmadi: {pkg}"
        self.after(0, self._set_status, msg)
        self.after(0, self._log, msg)

    def _cmd_uninstall(self):
        pkg = self._selected_pkg()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        if not messagebox.askyesno(
            "O'chirishni tasdiqlang",
            f"'{pkg}' emulyatordan o'chiriladi.\n\nDavom etamizmi?",
        ):
            return
        self._run_bg(self._bg_uninstall, dev, pkg)

    def _bg_uninstall(self, dev, pkg):
        ok = uninstall_app(dev, pkg, self.adb_path)
        if ok:
            self.after(0, self._set_status, f"O'chirildi: {pkg}")
            self.after(0, self._log, f"O'chirildi: {pkg}")
            # Ro'yxatdan ham olib tashlaymiz
            self.packages = [p for p in self.packages if p != pkg]
            self.after(0, self._populate_list, self.packages)
        else:
            self.after(0, messagebox.showerror, "Xato",
                       f"'{pkg}' o'chirilmadi.\nTizim ilovasi bo'lishi mumkin.")

    # ════════════════════ DIALOG OYNALAR ═════════════════════════════════════

    def _dlg_shortcuts(self):
        win = tk.Toplevel(self)
        win.title("Keyboard yorliqlari")
        win.geometry("440x380")
        win.resizable(False, False)

        sb = tk.Scrollbar(win)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        t = tk.Text(win, yscrollcommand=sb.set, font=("Consolas", 10),
                    wrap=tk.WORD, padx=8, pady=8)
        t.pack(fill=tk.BOTH, expand=True)
        sb.config(command=t.yview)

        t.insert(tk.END, """\
KEYBOARD YORLIQLARI
(NVDA bilan ishlash uchun)
══════════════════════════════════

F5          Emulyatorni aniqlash / yangilash
F6          Ilovalar ro'yxatini yuklash
Enter       Tanlangan ilovani ishga tushirish
Delete      Tanlangan ilovani o'chirish
Ctrl+Q      Dasturdan chiqish

Tab / Shift+Tab   Elementlar orasida yurish
Strelkalar        Ro'yxatda yurish
Alt+B             Bog'lanish menyusi
Alt+I             Ilovalar menyusi
Alt+Y             Yordam menyusi

NVDA bilan:
  NVDA+Tab       Joriy elementni o'qish
  NVDA+Yuqori    Joriy qatorni o'qish
  NVDA+A         Hamma matnni o'qish
  H              Sarlavhalar orasida sakrash

ESLATMA:
  Ro'yxatga fokus qilib, strelka bilan
  yuring — NVDA har bir ilova nomini
  o'qib beradi.
""")
        t.config(state=tk.DISABLED)
        win.grab_set()
        win.focus_set()

    def _dlg_about(self):
        messagebox.showinfo(
            "Dastur haqida",
            "Android Emulator Paneli\n"
            "Versiya: 3.0.0\n"
            "\n"
            "NVDA va barcha ekran o'quvchi dasturlar\n"
            "bilan to'liq mos keladi.\n"
            "\n"
            "Qo'llab-quvvatlanadigan emulyatorlar:\n"
            "  BlueStacks 5 / BlueStacks X\n"
            "  LDPlayer 9\n"
            "  NoxPlayer\n"
            "  WSA (Windows Subsystem for Android)\n"
            "  MuMu Player\n"
            "  Genymotion\n"
            "\n"
            "GitHub:\n"
            "github.com/jamshiduralov009-beep/android-manager-nvda",
        )


# ─── Ishga tushirish ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
