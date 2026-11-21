# Android Manager – NVDA 📱♿

**NVDA va barcha ekran o'quvchi dasturlar bilan to'liq mos keladigan Android qurilma boshqaruv ilovasi.**

> Bu dastur maxsus NVDA foydalanuvchilari uchun yaratilgan. Barcha elementlar accessibility label, keyboard navigation va focus management bilan jihozlangan.

---

## ✨ Xususiyatlar

- 📋 **Ilovalar ro'yxati** – O'rnatilgan barcha ilovalarni ko'rish
- 🔍 **Qidiruv** – Ilovalar orasida tezkor qidiruv
- ▶ **Ishga tushirish** – Ilovani to'g'ridan-to'g'ri kompyuterdan ishga tushirish
- ⏹ **To'xtatish** – Ilovani force-stop qilish
- 🗑 **O'chirish** – Ilovani qurilmadan o'chirish
- 🧹 **Kesh tozalash** – Ilova keshini tozalash
- 📷 **Skrinshot** – Qurilma ekranini rasmga olish
- 💻 **ADB terminal** – To'g'ridan-to'g'ri ADB buyruqlarini yuborish
- 📱 **Ko'p qurilma** – Bir vaqtda bir nechta qurilma bilan ishlash

---

## ♿ NVDA va Ekran O'quvchi Moslashuvi

Bu dastur quyidagi accessibility standartlarini qo'llaydi:

- ✅ Barcha tugmalar `takefocus=True` bilan keyboard orqali bosiladi
- ✅ `Listbox` ishlatiladi (Treeview emas) – NVDA bilan mukammal ishlaydi
- ✅ Tab/Shift+Tab bilan barcha elementlar orasida yurish mumkin
- ✅ Keyboard shortcut'lar (F5, Ctrl+R, Enter, Delete)
- ✅ Menyu orqali barcha amallar bajarish mumkin
- ✅ Status bar orqali holat xabarlari

---

## ⌨️ Keyboard Yorliqlari

| Tugma | Vazifa |
|-------|--------|
| `F5` | Qurilmalarni yangilash |
| `Ctrl+R` | Ilovalar ro'yxatini yangilash |
| `Ctrl+Q` | Dasturdan chiqish |
| `↑ ↓` | Ro'yxatda yurish |
| `Enter` | Ilovani ishga tushirish |
| `Delete` | Ilovani o'chirish |
| `Tab` / `Shift+Tab` | Elementlar orasida yurish |

---

## 🛠️ Talablar

- Windows 10/11
- Android qurilma + USB kabel yoki Wi-Fi
- Qurilmada **USB Debugging** yoqilgan bo'lishi kerak

> **ADB avtomatik topiladi.** Agar topilmasa, [Platform Tools](https://developer.android.com/tools/releases/platform-tools) yuklab oling.

---

## 🚀 Ishlatish

### Tayyor .exe (tavsiya)

1. [Releases](../../releases) sahifasidan `AndroidManager-NVDA.exe` yuklab oling
2. Android qurilmangizni USB orqali ulang
3. Qurilmada USB Debugging yoqing: `Settings > Developer Options > USB Debugging`
4. Dasturni ishga tushiring va `F5` bosing

### Python orqali

```bash
git clone https://github.com/jamshiduralov009-beep/android-manager-nvda
cd android-manager-nvda
pip install -r requirements.txt
python main.py
```

---

## 📦 .exe Qurish (Developers uchun)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "AndroidManager-NVDA" --icon app.ico main.py
```

---

## 📸 Ko'rinishi

```
┌─────────────────────────────────────────────────────┐
│ Android Manager – NVDA                              │
├──────────────────────────────────────────────────────│
│ [Yangilash] [Qurilmalar] [Ilovalar] [O'chirish]...  │
├─────────────────────┬────────────────────────────────│
│ Qidirish: [______]  │ === com.example.app ===        │
│                     │ versionName: 2.1.0             │
│ com.android.chrome  │ versionCode: 210               │
│ com.whatsapp        │ firstInstallTime: 2024-01-15   │
│ com.telegram.app    │                                │
│ ...                 │ > adb [______________] [▶]     │
└─────────────────────┴────────────────────────────────│
│ Status: 15 ta ilova topildi.                        │
└─────────────────────────────────────────────────────┘
```

---

## 📄 Litsenziya

MIT License – Bepul foydalaning va tarqating!

---

## 👨‍💻 Muallif

**Jamshid Uralov** – [@jamshiduralov009-beep](https://github.com/jamshiduralov009-beep)
