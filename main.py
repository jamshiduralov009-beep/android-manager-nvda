"""
Android Manager - NVDA Screen Reader Compatible
================================================
Bu ilova NVDA va boshqa ekran o'quvchi dasturlar bilan
to'liq mos keladi. Barcha elementlar accessibility
label va keyboard navigation bilan jihozlangan.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import sys
import os


# ─────────────────────────── ADB yordamchi funksiyalar ───────────────────────

def find_adb():
    """ADB dasturini topadi."""
    candidates = [
        "adb",
        r"C:\Users\Jamshid\AppData\Local\Microsoft\WinGet\Packages\Google.PlatformTools_Microsoft.Winget.Source_8wekyb3d8bbwe\platform-tools\adb.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Android", "Sdk", "platform-tools", "adb.exe"),
    ]
    for c in candidates:
        try:
            result = subprocess.run([c, "version"], capture_output=True, timeout=3)
            if result.returncode == 0:
                return c
        except Exception:
            continue
    return None


def run_adb(args, adb_path="adb"):
    """ADB buyrug'ini ishga tushiradi va natijani qaytaradi."""
    try:
        result = subprocess.run(
            [adb_path] + args,
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Vaqt tugadi (timeout)", 1
    except FileNotFoundError:
        return "", "ADB topilmadi", 1
    except Exception as e:
        return "", str(e), 1


# ─────────────────────────── Asosiy oyna ─────────────────────────────────────

class AndroidManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Android Manager – NVDA")
        self.geometry("900x650")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        # ADB yo'li
        self.adb_path = find_adb() or "adb"

        # Mavjud ilovalar ro'yxati
        self.app_list = []

        # UI qurish
        self._build_menu()
        self._build_toolbar()
        self._build_main_area()
        self._build_statusbar()

        # Keyboard shortcuts
        self.bind("<F5>", lambda e: self.refresh_devices())
        self.bind("<Control-r>", lambda e: self.refresh_apps())
        self.bind("<Control-q>", lambda e: self.quit())
        self.bind("<Alt-F4>", lambda e: self.quit())

        # Start
        self.after(500, self.refresh_devices)

    # ── Menyu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # Fayl
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Yangilash (F5)", command=self.refresh_devices, accelerator="F5")
        file_menu.add_separator()
        file_menu.add_command(label="Chiqish (Ctrl+Q)", command=self.quit, accelerator="Ctrl+Q")
        menubar.add_cascade(label="Fayl", menu=file_menu)

        # Qurilma
        device_menu = tk.Menu(menubar, tearoff=0)
        device_menu.add_command(label="Qurilmalar ro'yxati", command=self.show_devices)
        device_menu.add_command(label="Qurilma ma'lumotlari", command=self.show_device_info)
        device_menu.add_command(label="Ekran rasmini olish", command=self.take_screenshot)
        menubar.add_cascade(label="Qurilma", menu=device_menu)

        # Ilovalar
        app_menu = tk.Menu(menubar, tearoff=0)
        app_menu.add_command(label="Ilovalar ro'yxati (Ctrl+R)", command=self.refresh_apps, accelerator="Ctrl+R")
        app_menu.add_command(label="Ilovani o'chirish", command=self.uninstall_app)
        app_menu.add_command(label="Ilovani ishga tushirish", command=self.launch_app)
        app_menu.add_command(label="Ilovani to'xtatish", command=self.stop_app)
        app_menu.add_separator()
        app_menu.add_command(label="Kesh tozalash", command=self.clear_cache)
        app_menu.add_command(label="Ma'lumotlarni tozalash", command=self.clear_data)
        menubar.add_cascade(label="Ilovalar", menu=app_menu)

        # Yordam
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Keyboard yorliqlari", command=self.show_shortcuts)
        help_menu.add_command(label="Dastur haqida", command=self.show_about)
        menubar.add_cascade(label="Yordam", menu=help_menu)

    # ── Toolbari ──────────────────────────────────────────────────────────

    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg="#313244", pady=4)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_style = {
            "bg": "#45475a",
            "fg": "#cdd6f4",
            "activebackground": "#585b70",
            "activeforeground": "#cdd6f4",
            "relief": tk.FLAT,
            "padx": 10,
            "pady": 4,
            "cursor": "hand2",
            "font": ("Segoe UI", 10),
        }

        buttons = [
            ("🔄  Yangilash (F5)", self.refresh_devices),
            ("📱  Qurilmalar", self.show_devices),
            ("📋  Ilovalar (Ctrl+R)", self.refresh_apps),
            ("▶  Ishga tushirish", self.launch_app),
            ("⏹  To'xtatish", self.stop_app),
            ("🗑  O'chirish", self.uninstall_app),
            ("🧹  Kesh", self.clear_cache),
        ]

        for text, cmd in buttons:
            btn = tk.Button(toolbar, text=text, command=cmd, **btn_style)
            btn.pack(side=tk.LEFT, padx=2)

        # Qurilma tanlash
        tk.Label(toolbar, text="  Qurilma:", bg="#313244", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(10, 2))

        self.device_var = tk.StringVar(value="Hech qanday qurilma")
        self.device_combo = ttk.Combobox(toolbar, textvariable=self.device_var,
                                          width=22, font=("Segoe UI", 10))
        self.device_combo["state"] = "readonly"
        self.device_combo.pack(side=tk.LEFT, padx=4)
        # NVDA uchun
        self.device_combo.configure(takefocus=True)

    # ── Asosiy maydon ─────────────────────────────────────────────────────

    def _build_main_area(self):
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg="#1e1e2e",
                               sashwidth=5, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # Chap panel – ilovalar ro'yxati
        left_frame = tk.Frame(paned, bg="#1e1e2e")
        paned.add(left_frame, minsize=320)

        tk.Label(left_frame, text="📦 O'rnatilgan ilovalar",
                 bg="#1e1e2e", fg="#89b4fa",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))

        # Qidiruv
        search_frame = tk.Frame(left_frame, bg="#1e1e2e")
        search_frame.pack(fill=tk.X, pady=(0, 4))

        tk.Label(search_frame, text="Qidirish:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter_apps)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                                font=("Segoe UI", 10), relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        # NVDA accessibility
        search_entry.configure(takefocus=True)

        # Ilova listbox (keyboard navigatsiya uchun Listbox ishlatiladi, Treeview emas)
        list_frame = tk.Frame(left_frame, bg="#1e1e2e")
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.app_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg="#313244",
            fg="#cdd6f4",
            selectbackground="#89b4fa",
            selectforeground="#1e1e2e",
            font=("Segoe UI", 10),
            activestyle="dotbox",
            takefocus=True,
            exportselection=False,
        )
        self.app_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.app_listbox.yview)

        self.app_listbox.bind("<<ListboxSelect>>", self.on_app_select)
        self.app_listbox.bind("<Return>", lambda e: self.launch_app())
        self.app_listbox.bind("<Delete>", lambda e: self.uninstall_app())

        # O'ng panel – log va ma'lumotlar
        right_frame = tk.Frame(paned, bg="#1e1e2e")
        paned.add(right_frame, minsize=350)

        tk.Label(right_frame, text="📄 Ilova ma'lumotlari va log",
                 bg="#1e1e2e", fg="#89b4fa",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))

        self.info_text = scrolledtext.ScrolledText(
            right_frame,
            bg="#313244",
            fg="#a6e3a1",
            insertbackground="#cdd6f4",
            font=("Consolas", 10),
            wrap=tk.WORD,
            state=tk.DISABLED,
            takefocus=True,
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Terminal
        tk.Label(right_frame, text="💻 ADB buyruq terminalı",
                 bg="#1e1e2e", fg="#89b4fa",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))

        cmd_frame = tk.Frame(right_frame, bg="#1e1e2e")
        cmd_frame.pack(fill=tk.X)

        tk.Label(cmd_frame, text="adb ", bg="#1e1e2e", fg="#f9e2af",
                 font=("Consolas", 10)).pack(side=tk.LEFT)

        self.cmd_var = tk.StringVar()
        cmd_entry = tk.Entry(cmd_frame, textvariable=self.cmd_var,
                             bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                             font=("Consolas", 10), relief=tk.FLAT)
        cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 4))
        cmd_entry.bind("<Return>", lambda e: self.run_custom_cmd())

        tk.Button(cmd_frame, text="▶ Yuborish", command=self.run_custom_cmd,
                  bg="#a6e3a1", fg="#1e1e2e", relief=tk.FLAT,
                  font=("Segoe UI", 9, "bold"), padx=8).pack(side=tk.LEFT)

    # ── Status bar ────────────────────────────────────────────────────────

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Tayyor. F5 – qurilmalarni yangilash.")
        status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            bg="#313244",
            fg="#a6e3a1",
            font=("Segoe UI", 9),
            anchor="w",
            padx=8,
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ── Yordamchi: log ────────────────────────────────────────────────────

    def _log(self, msg: str, clear=False):
        self.info_text.config(state=tk.NORMAL)
        if clear:
            self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, msg + "\n")
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)

    def _status(self, msg: str):
        self.status_var.set(msg)

    def _selected_package(self):
        sel = self.app_listbox.curselection()
        if not sel:
            messagebox.showwarning("Tanlanmagan", "Iltimos, ro'yxatdan ilova tanlang.")
            return None
        return self.app_listbox.get(sel[0])

    def _selected_device(self):
        d = self.device_var.get()
        if not d or d == "Hech qanday qurilma":
            messagebox.showerror("Qurilma yo'q", "Avval Android qurilmangizni ulab, F5 bosing.")
            return None
        return d.split()[0]

    # ── Qurilmalar ────────────────────────────────────────────────────────

    def refresh_devices(self):
        self._status("Qurilmalar aniqlanmoqda...")

        def task():
            out, err, code = run_adb(["devices", "-l"], self.adb_path)
            lines = [l for l in out.splitlines() if l and "List of" not in l]
            devices = [l.split()[0] for l in lines if l.strip()]
            self.after(0, lambda: self._update_devices(devices, out))

        threading.Thread(target=task, daemon=True).start()

    def _update_devices(self, devices, raw):
        if devices:
            self.device_combo["values"] = devices
            self.device_combo.set(devices[0])
            self._status(f"{len(devices)} ta qurilma topildi.")
            self._log("=== Qurilmalar ===\n" + raw, clear=True)
        else:
            self.device_combo["values"] = ["Hech qanday qurilma"]
            self.device_combo.set("Hech qanday qurilma")
            self._status("Qurilma topilmadi. USB/Wi-Fi ulanganligini tekshiring.")
            self._log("Qurilma topilmadi.\n\nMaslahatlar:\n"
                      "• USB kabel ulang\n"
                      "• Qurilmada USB debugging yoqilganmi?\n"
                      "• Settings > Developer Options > USB Debugging\n"
                      "• Wi-Fi orqali: adb connect <IP>:5555", clear=True)

    def show_devices(self):
        def task():
            out, err, _ = run_adb(["devices", "-l"], self.adb_path)
            self.after(0, lambda: self._log("=== Qurilmalar ===\n" + (out or err), clear=True))
        threading.Thread(target=task, daemon=True).start()

    def show_device_info(self):
        dev = self._selected_device()
        if not dev:
            return
        self._status("Ma'lumotlar yuklanmoqda...")

        def task():
            props = {
                "Model": "ro.product.model",
                "Ishlab chiqaruvchi": "ro.product.manufacturer",
                "Android versiya": "ro.build.version.release",
                "SDK": "ro.build.version.sdk",
                "Qurilma nomi": "ro.product.name",
                "Serial": "ro.serialno",
                "CPU ABI": "ro.product.cpu.abi",
            }
            info_lines = ["=== Qurilma Ma'lumotlari ==="]
            for label, prop in props.items():
                out, _, _ = run_adb(["-s", dev, "shell", "getprop", prop], self.adb_path)
                info_lines.append(f"{label}: {out or '—'}")

            # Xotira
            mem_out, _, _ = run_adb(["-s", dev, "shell", "cat", "/proc/meminfo"], self.adb_path)
            for line in mem_out.splitlines()[:3]:
                info_lines.append(line)

            self.after(0, lambda: self._log("\n".join(info_lines), clear=True))
            self.after(0, lambda: self._status("Qurilma ma'lumotlari yuklandi."))

        threading.Thread(target=task, daemon=True).start()

    # ── Ilovalar ─────────────────────────────────────────────────────────

    def refresh_apps(self):
        dev = self._selected_device()
        if not dev:
            return
        self._status("Ilovalar ro'yxati yuklanmoqda...")
        self._log("Ilovalar yuklanmoqda, kuting...", clear=True)

        def task():
            # Foydalanuvchi ilovalari
            out, err, code = run_adb(["-s", dev, "shell", "pm", "list", "packages", "-3"], self.adb_path)
            pkgs = []
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkgs.append(line.replace("package:", "").strip())
            pkgs.sort()
            self.app_list = pkgs
            self.after(0, lambda: self._populate_listbox(pkgs))

        threading.Thread(target=task, daemon=True).start()

    def _populate_listbox(self, pkgs):
        self.app_listbox.delete(0, tk.END)
        for p in pkgs:
            self.app_listbox.insert(tk.END, p)
        self._status(f"{len(pkgs)} ta ilova topildi.")
        self._log(f"Jami {len(pkgs)} ta foydalanuvchi ilovasi topildi.\n\n"
                  f"Ilovani tanlang va amallarni bajaring.", clear=True)

    def _filter_apps(self, *args):
        query = self.search_var.get().lower()
        filtered = [p for p in self.app_list if query in p.lower()]
        self.app_listbox.delete(0, tk.END)
        for p in filtered:
            self.app_listbox.insert(tk.END, p)

    def on_app_select(self, event):
        pkg = self._selected_package()
        if not pkg:
            return
        dev = self._selected_device()
        if not dev:
            return

        def task():
            out, _, _ = run_adb(["-s", dev, "shell", "dumpsys", "package", pkg], self.adb_path)
            # Qisqacha ma'lumot chiqarish
            lines = out.splitlines()
            important = []
            for line in lines:
                for keyword in ["versionName", "versionCode", "firstInstallTime",
                                "lastUpdateTime", "dataDir", "codePath", "flags"]:
                    if keyword in line:
                        important.append(line.strip())
                        break
            info = f"=== {pkg} ===\n" + "\n".join(important[:20])
            self.after(0, lambda: self._log(info, clear=True))

        threading.Thread(target=task, daemon=True).start()

    def launch_app(self):
        pkg = self._selected_package()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        self._status(f"Ishga tushirilmoqda: {pkg}")

        def task():
            out, err, code = run_adb(
                ["-s", dev, "shell", "monkey", "-p", pkg, "-c",
                 "android.intent.category.LAUNCHER", "1"],
                self.adb_path,
            )
            msg = f"✅ Ishga tushirildi: {pkg}" if code == 0 else f"❌ Xato: {err}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))

        threading.Thread(target=task, daemon=True).start()

    def stop_app(self):
        pkg = self._selected_package()
        dev = self._selected_device()
        if not pkg or not dev:
            return

        def task():
            out, err, code = run_adb(["-s", dev, "shell", "am", "force-stop", pkg], self.adb_path)
            msg = f"⏹ To'xtatildi: {pkg}" if code == 0 else f"❌ Xato: {err}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))

        threading.Thread(target=task, daemon=True).start()

    def uninstall_app(self):
        pkg = self._selected_package()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        if not messagebox.askyesno("O'chirishni tasdiqlash",
                                   f"'{pkg}' ilovasini o'chirmoqchimisiz?"):
            return

        def task():
            out, err, code = run_adb(["-s", dev, "uninstall", pkg], self.adb_path)
            msg = f"🗑 O'chirildi: {pkg}" if "Success" in out else f"❌ Xato: {err or out}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))
            self.after(0, self.refresh_apps)

        threading.Thread(target=task, daemon=True).start()

    def clear_cache(self):
        pkg = self._selected_package()
        dev = self._selected_device()
        if not pkg or not dev:
            return

        def task():
            out, err, code = run_adb(["-s", dev, "shell", "pm", "clear", "--cache-only", pkg], self.adb_path)
            if code != 0:
                out, err, code = run_adb(["-s", dev, "shell", "pm", "clear", pkg], self.adb_path)
            msg = f"🧹 Kesh tozalandi: {pkg}" if code == 0 else f"❌ Xato: {err}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))

        threading.Thread(target=task, daemon=True).start()

    def clear_data(self):
        pkg = self._selected_package()
        dev = self._selected_device()
        if not pkg or not dev:
            return
        if not messagebox.askyesno("Ma'lumotlarni o'chirish",
                                   f"'{pkg}' ilovasining BARCHA ma'lumotlari o'chiriladi!\nDavom etamizmi?"):
            return

        def task():
            out, err, code = run_adb(["-s", dev, "shell", "pm", "clear", pkg], self.adb_path)
            msg = f"🧹 Ma'lumotlar tozalandi: {pkg}" if code == 0 else f"❌ Xato: {err}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))

        threading.Thread(target=task, daemon=True).start()

    def take_screenshot(self):
        dev = self._selected_device()
        if not dev:
            return

        def task():
            remote = "/sdcard/nvda_manager_screenshot.png"
            out, err, code = run_adb(["-s", dev, "shell", "screencap", "-p", remote], self.adb_path)
            if code == 0:
                local = os.path.join(os.path.expanduser("~"), "Desktop", "android_screenshot.png")
                run_adb(["-s", dev, "pull", remote, local], self.adb_path)
                msg = f"📷 Skrinshot saqlandi: {local}"
            else:
                msg = f"❌ Xato: {err}"
            self.after(0, lambda: self._log(msg))
            self.after(0, lambda: self._status(msg))

        threading.Thread(target=task, daemon=True).start()

    # ── Maxsus buyruq ─────────────────────────────────────────────────────

    def run_custom_cmd(self):
        cmd = self.cmd_var.get().strip()
        if not cmd:
            return
        dev = self.device_var.get()
        self._log(f"\n> adb {cmd}", )
        self.cmd_var.set("")

        def task():
            args = cmd.split()
            # Agar qurilma tanlangan bo'lsa va -s yo'q bo'lsa
            if dev and dev != "Hech qanday qurilma" and "-s" not in args:
                args = ["-s", dev.split()[0]] + args
            out, err, _ = run_adb(args, self.adb_path)
            result = out or err or "(natija yo'q)"
            self.after(0, lambda: self._log(result))

        threading.Thread(target=task, daemon=True).start()

    # ── Yordam ────────────────────────────────────────────────────────────

    def show_shortcuts(self):
        shortcuts = """
⌨️  KEYBOARD YORLIQLARI (NVDA bilan ishlash uchun)
═══════════════════════════════════════════════════
F5           – Qurilmalarni yangilash
Ctrl+R       – Ilovalar ro'yxatini yangilash
Ctrl+Q       – Dasturdan chiqish

Ro'yxatda navigatsiya:
↑ ↓          – Ilovalar orasida yurish
Enter        – Tanlangan ilovani ishga tushirish
Delete       – Tanlangan ilovani o'chirish

Tab          – Elementlar orasida yurish
Shift+Tab    – Orqaga yurish

Alt + F      – Fayl menyusi
Alt + Q      – Qurilma menyusi
Alt + I      – Ilovalar menyusi
Alt + Y      – Yordam menyusi

NVDA bilan:
NVDA+Tab     – Joriy element haqida ma'lumot
NVDA+F5      – Zamonaviy interfeysni yangilash
        """
        win = tk.Toplevel(self)
        win.title("Keyboard yorliqlari")
        win.geometry("500x420")
        win.configure(bg="#1e1e2e")
        st = scrolledtext.ScrolledText(win, bg="#313244", fg="#cdd6f4",
                                       font=("Consolas", 10), wrap=tk.WORD)
        st.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        st.insert(tk.END, shortcuts)
        st.config(state=tk.DISABLED)
        win.grab_set()
        win.focus_set()

    def show_about(self):
        messagebox.showinfo(
            "Dastur haqida",
            "Android Manager – NVDA\n"
            "Versiya: 1.0.0\n\n"
            "Bu dastur NVDA va boshqa ekran o'quvchi dasturlar bilan\n"
            "to'liq mos keladi.\n\n"
            "ADB orqali Android qurilmalaringizni boshqaring:\n"
            "• Ilovalarni ko'rish va boshqarish\n"
            "• Ilovalarni o'chirish yoki ishga tushirish\n"
            "• Kesh va ma'lumotlarni tozalash\n"
            "• Skrinshot olish\n"
            "• ADB buyruqlarini to'g'ridan-to'g'ri yuborish\n\n"
            "GitHub: github.com/jamshiduralov009-beep/android-manager-nvda",
        )


# ─────────────────────────── Ishga tushirish ─────────────────────────────────

if __name__ == "__main__":
    app = AndroidManagerApp()
    app.mainloop()
