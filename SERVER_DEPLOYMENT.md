# ☁️ Panduan Menjalankan di Server (VPS / Cloud) 24 Jam

Karena tool ini sudah **Pure HTTP (tanpa Selenium / Chrome)**, konsumsi resource-nya sangat ringan (RAM hanya ~20MB, CPU 0%).

---

## 1. Persiapan di Server

Clone / upload folder ini ke server Anda, lalu install dependencies:

```bash
# Update & pastikan python ada
sudo apt update && sudo apt install -y python3 python3-pip

# Masuk ke folder proyek
cd "Absen Otomatis"

# Install dependency (hanya requests)
pip3 install -r requirements.txt
```

Pastikan file `config.json` sudah terisi email & password akun PENS Anda.

---

## 2. Pilihan Menjalankan 24 Jam

Pilih salah satu metode berikut:

### Opsi A: Systemd Service (Paling Direkomendasikan ⭐)
Otomatis jalan saat server baru nyala (reboot) dan otomatis restart jika terjadi crash.

1. Buat file service:
```bash
sudo nano /etc/systemd/system/ethol-absen.service
```

2. Masukkan konfigurasi berikut (sesuaikan `User` dan path `WorkingDirectory`):
```ini
[Unit]
Description=ETHOL PENS Auto Attendance Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Absen Otomatis
ExecStart=/usr/bin/python3 absen_otomatis.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/Absen Otomatis/logs/systemd.log
StandardError=append:/home/ubuntu/Absen Otomatis/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

3. Jalankan dan aktifkan:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Aktifkan auto-start saat reboot
sudo systemctl enable ethol-absen

# Jalankan service sekarang
sudo systemctl start ethol-absen

# Cek status
sudo systemctl status ethol-absen
```

---

### Opsi B: Menggunakan PM2 (Sangat Mudah)
Jika Anda sudah punya Node.js & PM2 di server:

```bash
# Jalankan via PM2
pm2 start absen_otomatis.py --name ethol-absen --interpreter python3

# Simpan agar jalan setelah reboot
pm2 save
pm2 startup
```

---

### Opsi C: Menggunakan TMUX / Screen
Paling simpel tanpa konfigurasi service:

```bash
# Buka sesi tmux
tmux new -s absen

# Jalankan script
python3 absen_otomatis.py

# Keluar dari tmux tanpa mematikan proses:
# Tekan Ctrl+B lalu tekan D
```
Untuk membuka kembali: `tmux attach -t absen`

---

### Opsi D: Docker Container
Tersedia `Dockerfile` di folder ini jika Anda lebih suka containerized environment:

```bash
docker build -t ethol-absen .
docker run -d --name ethol-bot --restart always ethol-absen
```
