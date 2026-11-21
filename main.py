"""
Android APK Manager – NVDA
==========================
Telefon ulash SHART EMAS.
APK fayllarini kompyuterda boshqaring – NVDA bilan to'liq mos.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import os
import zipfile
import struct
import threading
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime


# ─────────────────────── APK parser (hech qanday kutubxonasiz) ──────────────

def parse_apk(apk_path: str) -> dict:
    """APK fayldan asosiy ma'lumotlarni o'qiydi (telefon shart emas)."""
    info = {
        "fayl_nomi": os.path.basename(apk_path),
        "fayl_hajmi": "",
        "paket_nomi": "Aniqlanmadi",
        "versiya_nomi": "Aniqlanmadi",
        "versiya_kodi": "Aniqlanmadi",
        "min_sdk": "Aniqlanmadi",
        "target_sdk": "Aniqlanmadi",
        "ruxsatlar": [],
        "faoliyatlar": [],
        "xizmatlar": [],
        "yaratilgan": "",
    }

    try:
        size = os.path.getsize(apk_path)
        if size < 1024 * 1024:
            info["fayl_hajmi"] = f"{size // 1024} KB"
        else:
            info["fayl_hajmi"] = f"{size / (1024*1024):.1f} MB"

        mtime = os.path.getmtime(apk_path)
        info["yaratilgan"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        with zipfile.ZipFile(apk_path, 'r') as z:
            names = z.namelist()

            # AndroidManifest.xml ni binary o'qish
            if "AndroidManifest.xml" in names:
                raw = z.read("AndroidManifest.xml")
                text = _extract_manifest_text(raw)

                pkg = re.search(r'package="([^"]+)"', text)
                if pkg:
                    info["paket_nomi"] = pkg.group(1)

                vname = re.search(r'versionName="([^"]+)"', text)
                if vname:
                    info["versiya_nomi"] = vname.group(1)

                vcode = re.search(r'versionCode="([^"]+)"', text)
                if vcode:
                    info["versiya_kodi"] = vcode.group(1)

                min_sdk = re.search(r'minSdkVersion="([^"]+)"', text)
                if min_sdk:
                    info["min_sdk"] = _sdk_to_android(min_sdk.group(1))

                tgt_sdk = re.search(r'targetSdkVersion="([^"]+)"', text)
                if tgt_sdk:
                    info["target_sdk"] = _sdk_to_android(tgt_sdk.group(1))

                perms = re.findall(r'uses-permission[^>]*name="([^"]+)"', text)
                info["ruxsatlar"] = list(set(perms))[:20]

                acts = re.findall(r'activity[^>]*name="([^"]+)"', text)
                info["faoliyatlar"] = [a.split(".")[-1] for a in acts[:10]]

                svcs = re.findall(r'service[^>]*name="([^"]+)"', text)
                info["xizmatlar"] = [s.split(".")[-1] for s in svcs[:10]]

    except Exception as e:
        info["xato"] = str(e)

    return info


def _extract_manifest_text(raw: bytes) -> str:
    """Binary AndroidManifest.xml dan matn qismlarini chiqaradi."""
    try:
        # Android binary XML dan o'qiladigan qatorlarni topamiz
        result = []
        i = 0
        while i < len(raw) - 2:
            if raw[i] == 0 and raw[i+1] != 0:
                # Skip null bytes between characters
                i += 1
                continue
            if 0x20 <= raw[i] <= 0x7e:
                j = i
                while j < len(raw) and 0x20 <= raw[j] <= 0x7e:
                    j += 1
                word = raw[i:j].decode("ascii", errors="ignore")
                if len(word) >= 3:
                    result.append(word)
                i = j
            else:
                i += 1
        return " ".join(result)
    except Exception:
        return ""


def _sdk_to_android(sdk_str: str) -> str:
    sdk_map = {
        "21": "5.0 Lollipop", "22": "5.1 Lollipop", "23": "6.0 Marshmallow",
        "24": "7.0 Nougat", "25": "7.1 Nougat", "26": "8.0 Oreo",
        "27": "8.1 Oreo", "28": "9.0 Pie", "29": "10 Q",
        "30": "11 R", "31": "12 S", "32": "12L",
        "33": "13 Tiramisu", "34": "14 Upside Down Cake",
        "35": "15 Vanilla Ice Cream",
    }
    try:
        num = str(int(sdk_str, 16) if sdk_str.startswith("0x") else int(sdk_str))
        return sdk_map.get(num, f"API {num}")
    except Exception:
        return sdk_str


# ─────────────────────── Asosiy oyna ────────────────────────────────────────

class ApkManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Android APK Manager – NVDA")
        self.geometry("1000x680")
        self.resizable(True, True)
        self.configure(bg="#1e1e2e")

        # APK ro'yxati
        self.apk_list = []          # (path, info)
        self.current_folder = ""

        self._build_menu()
        self._build_toolbar()
        self._build_main()
        self._build_status()

        # Keyboard
        self.bind("<F5>",           lambda e: self.scan_folder())
        self.bind("<Control-o>",    lambda e: self.open_folder())
        self.bind("<Control-f>",    lambda e: self.focus_search())
        self.bind("<Control-q>",    lambda e: self.quit())
        self.bind("<Delete>",       lambda e: self.delete_apk())

        self._log("Xush kelibsiz! 👋\n\n"
                  "Foydalanish:\n"
                  "1. 'Papka ochish' tugmasini bosing yoki Ctrl+O\n"
                  "2. APK fayllari saqlangan papkani tanlang\n"
                  "3. Ro'yxatdan APK ni tanlang – ma'lumotlar ko'rinadi\n\n"
                  "⚠️ Telefon ulash KERAK EMAS!", clear=True)

    # ── Menyu ────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = tk.Menu(self)
        self.config(menu=mb)

        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label="Papka ochish (Ctrl+O)",   command=self.open_folder)
        fm.add_command(label="APK fayl qo'shish",        command=self.add_apk_file)
        fm.add_separator()
        fm.add_command(label="Chiqish (Ctrl+Q)",         command=self.quit)
        mb.add_cascade(label="Fayl", menu=fm)

        am = tk.Menu(mb, tearoff=0)
        am.add_command(label="APK ma'lumotlari",          command=self.show_apk_info)
        am.add_command(label="APK ni nusxalash",           command=self.copy_apk)
        am.add_command(label="APK ni o'chirish",           command=self.delete_apk)
        am.add_separator()
        am.add_command(label="APK ni ochish (Explorer)",   command=self.open_in_explorer)
        mb.add_cascade(label="APK amallar", menu=am)

        hm = tk.Menu(mb, tearoff=0)
        hm.add_command(label="Keyboard yorliqlari",        command=self.show_shortcuts)
        hm.add_command(label="Dastur haqida",              command=self.show_about)
        mb.add_cascade(label="Yordam", menu=hm)

    # ── Toolbar ──────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = tk.Frame(self, bg="#313244", pady=4)
        bar.pack(side=tk.TOP, fill=tk.X)

        s = dict(bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                 activeforeground="#cdd6f4", relief=tk.FLAT,
                 padx=10, pady=4, cursor="hand2", font=("Segoe UI", 10))

        btns = [
            ("📂  Papka ochish (Ctrl+O)", self.open_folder),
            ("➕  APK qo'shish",           self.add_apk_file),
            ("🔄  Yangilash (F5)",          self.scan_folder),
            ("📋  Ma'lumotlar",             self.show_apk_info),
            ("📁  Explorerde ochish",        self.open_in_explorer),
            ("🗑  O'chirish (Del)",          self.delete_apk),
        ]
        for text, cmd in btns:
            tk.Button(bar, text=text, command=cmd, **s).pack(side=tk.LEFT, padx=2)

        # Papka ko'rsatish
        self.folder_lbl = tk.Label(bar, text="  📁 Papka tanlanmagan",
                                   bg="#313244", fg="#f9e2af",
                                   font=("Segoe UI", 9))
        self.folder_lbl.pack(side=tk.LEFT, padx=10)

    # ── Asosiy maydon ────────────────────────────────────────────────────────

    def _build_main(self):
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                               bg="#1e1e2e", sashwidth=5)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ── Chap: ro'yxat ──────────────────────────────────────────────────
        left = tk.Frame(paned, bg="#1e1e2e")
        paned.add(left, minsize=320)

        tk.Label(left, text="📦 APK Fayllar ro'yxati",
                 bg="#1e1e2e", fg="#89b4fa",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))

        # Qidiruv
        sf = tk.Frame(left, bg="#1e1e2e")
        sf.pack(fill=tk.X, pady=(0, 4))
        tk.Label(sf, text="🔍 Qidirish:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter)
        self.search_entry = tk.Entry(sf, textvariable=self.search_var,
                                     bg="#313244", fg="#cdd6f4",
                                     insertbackground="#cdd6f4",
                                     font=("Segoe UI", 10), relief=tk.FLAT)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Listbox
        lf = tk.Frame(left, bg="#1e1e2e")
        lf.pack(fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(lf, orient=tk.VERTICAL)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(
            lf, yscrollcommand=sb.set,
            bg="#313244", fg="#cdd6f4",
            selectbackground="#89b4fa", selectforeground="#1e1e2e",
            font=("Segoe UI", 10), activestyle="dotbox",
            takefocus=True, exportselection=False,
        )
        self.listbox.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.listbox.yview)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self.listbox.bind("<Return>",  lambda e: self.show_apk_info())
        self.listbox.bind("<Delete>",  lambda e: self.delete_apk())

        # Hisoblagich
        self.count_lbl = tk.Label(left, text="0 ta APK",
                                   bg="#1e1e2e", fg="#6c7086",
                                   font=("Segoe UI", 9))
        self.count_lbl.pack(anchor="w")

        # ── O'ng: ma'lumotlar ──────────────────────────────────────────────
        right = tk.Frame(paned, bg="#1e1e2e")
        paned.add(right, minsize=380)

        tk.Label(right, text="📄 APK Ma'lumotlari",
                 bg="#1e1e2e", fg="#89b4fa",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 4))

        self.info_text = scrolledtext.ScrolledText(
            right,
            bg="#313244", fg="#a6e3a1",
            insertbackground="#cdd6f4",
            font=("Consolas", 10), wrap=tk.WORD,
            state=tk.DISABLED, takefocus=True,
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

    # ── Status bar ───────────────────────────────────────────────────────────

    def _build_status(self):
        self.status_var = tk.StringVar(value="Tayyor. Papka oching – Ctrl+O")
        tk.Label(self, textvariable=self.status_var,
                 bg="#313244", fg="#a6e3a1",
                 font=("Segoe UI", 9), anchor="w", padx=8
                 ).pack(side=tk.BOTTOM, fill=tk.X)

    # ── Log yordamchisi ──────────────────────────────────────────────────────

    def _log(self, msg: str, clear=False):
        self.info_text.config(state=tk.NORMAL)
        if clear:
            self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, msg + "\n")
        self.info_text.see(tk.END)
        self.info_text.config(state=tk.DISABLED)

    def _status(self, msg: str):
        self.status_var.set(msg)

    # ── Papka va fayl amallar ────────────────────────────────────────────────

    def open_folder(self):
        folder = filedialog.askdirectory(title="APK fayllar papkasini tanlang")
        if folder:
            self.current_folder = folder
            short = folder if len(folder) <= 50 else "..." + folder[-47:]
            self.folder_lbl.config(text=f"  📁 {short}")
            self.scan_folder()

    def add_apk_file(self):
        files = filedialog.askopenfilenames(
            title="APK fayl(lar)ni tanlang",
            filetypes=[("Android APK", "*.apk"), ("Barcha fayllar", "*.*")]
        )
        for f in files:
            if f not in [a[0] for a in self.apk_list]:
                info = parse_apk(f)
                self.apk_list.append((f, info))
        self._refresh_listbox()

    def scan_folder(self):
        if not self.current_folder:
            self.open_folder()
            return
        self._status("APK fayllar skanlanmoqda...")
        self._log(f"📂 Skanlanmoqda: {self.current_folder}", clear=True)

        def task():
            found = []
            for root, _, files in os.walk(self.current_folder):
                for f in files:
                    if f.lower().endswith(".apk"):
                        fp = os.path.join(root, f)
                        found.append(fp)
            # Parse
            result = []
            for fp in found:
                info = parse_apk(fp)
                result.append((fp, info))
            self.after(0, lambda: self._load_results(result))

        threading.Thread(target=task, daemon=True).start()

    def _load_results(self, result):
        self.apk_list = result
        self._refresh_listbox()
        self._log(f"✅ {len(result)} ta APK topildi.\n\n"
                  "Ro'yxatdan APK ni tanlang — ma'lumotlar shu yerda ko'rinadi.\n"
                  "Telefon ulash kerak emas!", clear=True)
        self._status(f"{len(result)} ta APK topildi.")

    def _refresh_listbox(self):
        q = self.search_var.get().lower()
        self.listbox.delete(0, tk.END)
        shown = 0
        for path, info in self.apk_list:
            name = info.get("fayl_nomi", os.path.basename(path))
            pkg  = info.get("paket_nomi", "")
            if q and q not in name.lower() and q not in pkg.lower():
                continue
            display = f"{name}  [{pkg}]" if pkg != "Aniqlanmadi" else name
            self.listbox.insert(tk.END, display)
            shown += 1
        self.count_lbl.config(text=f"{shown} ta APK")

    def _filter(self, *args):
        self._refresh_listbox()

    def focus_search(self):
        self.search_entry.focus_set()

    # ── Tanlash hodisasi ─────────────────────────────────────────────────────

    def _on_select(self, event=None):
        idx = self._selected_idx()
        if idx is None:
            return
        path, info = self.apk_list[idx]

        lines = [
            f"📦 APK Ma'lumotlari",
            f"{'═'*45}",
            f"📄 Fayl nomi   : {info.get('fayl_nomi', '—')}",
            f"📦 Paket nomi  : {info.get('paket_nomi', '—')}",
            f"🔖 Versiya     : {info.get('versiya_nomi', '—')}  (kod: {info.get('versiya_kodi', '—')})",
            f"📏 Hajmi       : {info.get('fayl_hajmi', '—')}",
            f"📅 Sana        : {info.get('yaratilgan', '—')}",
            f"",
            f"📱 Android talablari:",
            f"   Min SDK  : {info.get('min_sdk', '—')}",
            f"   Target   : {info.get('target_sdk', '—')}",
            f"",
            f"📂 To'liq yo'l : {path}",
        ]

        perms = info.get("ruxsatlar", [])
        if perms:
            lines += ["", f"🔑 Ruxsatlar ({len(perms)} ta):"]
            for p in perms[:15]:
                short = p.replace("android.permission.", "")
                lines.append(f"   • {short}")
            if len(perms) > 15:
                lines.append(f"   ... va {len(perms)-15} ta yana")

        acts = info.get("faoliyatlar", [])
        if acts:
            lines += ["", f"⚡ Activities ({len(acts)} ta):"]
            for a in acts:
                lines.append(f"   • {a}")

        self._log("\n".join(lines), clear=True)

    # ── APK amallar ──────────────────────────────────────────────────────────

    def show_apk_info(self):
        self._on_select()

    def copy_apk(self):
        idx = self._selected_idx()
        if idx is None:
            return
        path, info = self.apk_list[idx]
        dest = filedialog.askdirectory(title="Nusxa saqlanadigan papkani tanlang")
        if dest:
            shutil.copy2(path, dest)
            self._log(f"✅ Nusxalandi: {dest}")
            self._status(f"Nusxalandi → {dest}")

    def delete_apk(self):
        idx = self._selected_idx()
        if idx is None:
            return
        path, info = self.apk_list[idx]
        name = info.get("fayl_nomi", os.path.basename(path))
        if not messagebox.askyesno("O'chirishni tasdiqlang",
                                   f"'{name}' faylini diskdan o'chirmoqchimisiz?\n\n"
                                   f"Bu amal qaytarib bo'lmaydi!"):
            return
        try:
            os.remove(path)
            self.apk_list.pop(idx)
            self._refresh_listbox()
            self._log(f"🗑 O'chirildi: {name}", clear=True)
            self._status(f"O'chirildi: {name}")
        except Exception as e:
            messagebox.showerror("Xato", str(e))

    def open_in_explorer(self):
        idx = self._selected_idx()
        if idx is None:
            return
        path, _ = self.apk_list[idx]
        subprocess.run(["explorer", "/select,", path])

    # ── Yordamchi ────────────────────────────────────────────────────────────

    def _selected_idx(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Tanlanmagan",
                                   "Iltimos, ro'yxatdan APK faylni tanlang.")
            return None
        q   = self.search_var.get().lower()
        shown_indices = []
        for i, (path, info) in enumerate(self.apk_list):
            name = info.get("fayl_nomi", os.path.basename(path))
            pkg  = info.get("paket_nomi", "")
            if q and q not in name.lower() and q not in pkg.lower():
                continue
            shown_indices.append(i)
        try:
            return shown_indices[sel[0]]
        except IndexError:
            return None

    def show_shortcuts(self):
        win = tk.Toplevel(self)
        win.title("Keyboard yorliqlari")
        win.geometry("460x360")
        win.configure(bg="#1e1e2e")
        st = scrolledtext.ScrolledText(win, bg="#313244", fg="#cdd6f4",
                                       font=("Consolas", 10), wrap=tk.WORD)
        st.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        st.insert(tk.END, """
⌨️  KEYBOARD YORLIQLARI  (NVDA bilan ishlash uchun)
══════════════════════════════════════════════════
Ctrl+O       – Papka ochish
Ctrl+F       – Qidiruvga o'tish
F5           – Papkani qayta skanlaish
Delete       – Tanlangan APK ni o'chirish
Ctrl+Q       – Dasturdan chiqish

Ro'yxatda navigatsiya:
↑ ↓          – APK lar orasida yurish
Enter        – APK ma'lumotlarini ko'rish
Tab          – Elementlar orasida yurish
Shift+Tab    – Orqaga yurish

NVDA bilan:
NVDA+Tab     – Joriy element haqida ma'lumot
H            – Sarlavhalar orasida yurish
        """)
        st.config(state=tk.DISABLED)
        win.grab_set()
        win.focus_set()

    def show_about(self):
        messagebox.showinfo(
            "Dastur haqida",
            "Android APK Manager – NVDA\n"
            "Versiya: 2.0.0\n\n"
            "✅ Telefon ulash KERAK EMAS\n"
            "✅ NVDA bilan to'liq mos\n"
            "✅ Barcha keyboard shortcut'lar mavjud\n\n"
            "Xususiyatlar:\n"
            "• APK fayllarini ko'rish va boshqarish\n"
            "• Paket nomi, versiya, ruxsatlar ko'rish\n"
            "• Min/Target Android versiyani ko'rish\n"
            "• APK nusxalash, o'chirish\n"
            "• Windows Explorer'da ochish\n\n"
            "GitHub: github.com/jamshiduralov009-beep/android-manager-nvda"
        )


# ─────────────────────── Ishga tushirish ────────────────────────────────────

if __name__ == "__main__":
    app = ApkManagerApp()
    app.mainloop()
