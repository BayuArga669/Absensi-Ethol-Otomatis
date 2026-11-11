# 🎓 ETHOL PENS - Auto Attendance Tool

> ⚠️ **Disclaimer**: Tool ini dibuat **hanya untuk keperluan eksperimen dan pembelajaran web automation**. Penggunaan untuk memalsukan kehadiran dapat melanggar kebijakan akademik kampus.

## Cara Kerja

```
┌─────────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────────┐
│  Login CAS   │───>│  Get Kuliah  │───>│  Monitor Aktif   │───>│ Auto Presensi  │
│  SSO PENS    │    │  Semester    │    │  Setiap 30 detik │    │  Saat Terbuka  │
└─────────────┘    └──────────────┘    └──────────────────┘    └────────────────┘
```

1. **Login** via CAS SSO PENS menggunakan Selenium (headless Chrome)
2. **Ambil** daftar matakuliah semester aktif via API
3. **Monitor** presensi aktif di semua matakuliah setiap 30 detik
4. **Submit** otomatis saat dosen membuka sesi presensi

## Prerequisites

- Python 3.10+
- Google Chrome browser
- Koneksi internet

## Instalasi

```bash
# Install dependencies
pip install -r requirements.txt
```

## Konfigurasi

Edit file `config.json`:

```json
{
    "email": "yourname@ce.student.pens.ac.id",
    "password": "YourPassword",
    "tahun": 2026,
    "semester": 1,
    "check_interval_seconds": 30,
    "headless": true
}
```

| Field | Deskripsi |
|-------|-----------|
| `email` | Email akun PENS |
| `password` | Password akun PENS |
| `tahun` | Tahun ajaran (2026 = TA 2026/2027) |
| `semester` | 1 = Ganjil, 2 = Genap |
| `check_interval_seconds` | Interval pengecekan (detik) |
| `headless` | `true` = Chrome tanpa GUI, `false` = dengan GUI |

## Penggunaan

```bash
# Jalankan monitoring
python absen_otomatis.py

# Atau jalankan quick test dulu
python test_quick.py
```

### Output contoh:

```
╔══════════════════════════════════════════════════════════════╗
║         Auto Attendance Tool - PENS                          ║
║         Untuk keperluan eksperimen saja!                     ║
╚══════════════════════════════════════════════════════════════╝

🔐 Memulai proses login via CAS SSO...
✅ Login berhasil! Selamat datang, Bayu Arga Pratama Rinaldi (NRP: 3226600066)

📚 Memuat daftar matakuliah...
   • [220887] Matematika 1
   • [220890] Fisika 1: Mekanika
   • ...

🔄 Mulai monitoring presensi (setiap 30 detik)...

[11:30:00] 🔍 Cek #1 - Memeriksa presensi aktif...
[11:30:30] 🔍 Cek #2 - Memeriksa presensi aktif...
🟢 PRESENSI AKTIF DITEMUKAN!
   Matakuliah: Matematika 1
   ✅ PRESENSI BERHASIL!
```

## Struktur File

```
Absen Otomatis/
├── absen_otomatis.py    # Script utama
├── config.json          # Konfigurasi credential & settings
├── requirements.txt     # Python dependencies
├── test_quick.py        # Quick test script
├── README.md            # Dokumentasi ini
└── logs/                # Log harian (auto-generated)
    └── absensi_YYYYMMDD.log
```

## Catatan Teknis

- Login menggunakan **CAS SSO PENS** (`login.pens.ac.id`)
- Autentikasi via **JWT token** (cookie `token`)
- API endpoint presensi: `POST /api/presensi/mahasiswa`
- Token di-validasi ulang setiap 5 menit
- Jika token expired, akan auto re-login
- Sesi presensi yang sudah di-submit tidak akan di-submit ulang
