"""
╔══════════════════════════════════════════════════════════════╗
║           ETHOL PENS - Auto Attendance Tool                  ║
║           Untuk keperluan eksperimen saja!                    ║
╚══════════════════════════════════════════════════════════════╝

Tool ini akan:
1. Login ke ETHOL via CAS SSO (pure HTTP, tanpa Chrome)
2. Ambil daftar kuliah semester aktif
3. Monitor presensi aktif secara berkala
4. Otomatis klik presensi saat dosen membuka sesi

Disclaimer: Hanya untuk eksperimen dan pembelajaran web automation.
"""

import sys
import io
import os
import re
import time
import json
import base64
import logging
from datetime import datetime

# Fix encoding for Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests

# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "email": "",
    "password": "",
    "tahun": 2026,
    "semester": 1,
    "check_interval_seconds": 30,
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for key, val in DEFAULT_CONFIG.items():
            if key not in cfg:
                cfg[key] = val
        return cfg
    return DEFAULT_CONFIG.copy()


# ══════════════════════════════════════════════════════════════
# Logging Setup
# ══════════════════════════════════════════════════════════════

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, f"absensi_{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8",
        ),
    ],
)
log = logging.getLogger("ethol-absen")

# ══════════════════════════════════════════════════════════════
# ETHOL API Client (Pure HTTP - No Chrome/Selenium needed!)
# ══════════════════════════════════════════════════════════════

BASE_URL = "https://ethol.pens.ac.id"
CAS_LOGIN_URL = "https://login.pens.ac.id/cas/login"
CAS_SERVICE = f"{BASE_URL}/api/auth/cas-callback"


class ETHOLClient:
    """Client for interacting with ETHOL PENS API via pure HTTP requests."""

    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None
        self.mahasiswa_nomor = None
        self.mahasiswa_nama = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        })

    def login(self) -> bool:
        """Login via CAS SSO using pure HTTP requests (no browser needed)."""
        log.info("🔐 Memulai login via CAS SSO...")

        try:
            # Step 1: GET CAS login page → extract hidden fields (lt, _eventId)
            cas_url = f"{CAS_LOGIN_URL}?service={requests.utils.quote(CAS_SERVICE)}"
            r = self.session.get(cas_url, allow_redirects=True, timeout=15)
            r.raise_for_status()

            lt_match = re.search(r'name="lt"\s+value="([^"]+)"', r.text)
            event_id_match = re.search(r'name="_eventId"\s+value="([^"]+)"', r.text)
            action_match = re.search(r'action="([^"]+)"', r.text)

            if not lt_match:
                log.error("❌ Gagal mendapatkan login ticket (lt) dari CAS.")
                return False

            lt = lt_match.group(1)
            event_id = event_id_match.group(1) if event_id_match else "submit"
            form_action = action_match.group(1) if action_match else cas_url

            # Build POST URL
            if form_action.startswith("/"):
                post_url = "https://login.pens.ac.id" + form_action
            else:
                post_url = form_action

            # Step 2: POST credentials to CAS
            login_data = {
                "username": self.email,
                "password": self.password,
                "lt": lt,
                "_eventId": event_id,
                "submit": "LOGIN",
            }

            r = self.session.post(post_url, data=login_data, allow_redirects=True, timeout=15)

            # Check if login failed (still on CAS page)
            if "cas/login" in r.url:
                log.error("❌ Login gagal! Cek email dan password.")
                return False

            # Step 3: Extract JWT token from cookies
            self.token = self.session.cookies.get("token", domain="ethol.pens.ac.id")
            self.refresh_token = self.session.cookies.get("refresh_token", domain="ethol.pens.ac.id")

            if not self.token:
                log.error("❌ Token tidak ditemukan setelah login.")
                return False

            # Update session headers with auth
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Referer": f"{BASE_URL}/mahasiswa/beranda",
            })

            # Step 4: Decode JWT to get user info
            self._decode_token()

            log.info(f"✅ Login berhasil! Selamat datang, {self.mahasiswa_nama}")
            log.info(f"   Mahasiswa nomor: {self.mahasiswa_nomor}")
            return True

        except requests.RequestException as e:
            log.error(f"❌ Network error saat login: {e}")
            return False
        except Exception as e:
            log.error(f"❌ Unexpected error saat login: {e}")
            return False

    def _decode_token(self):
        """Decode JWT token to extract user info."""
        try:
            payload = self.token.split(".")[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            self.mahasiswa_nomor = decoded.get("nomor")
            nrp = decoded.get("nipnrp", "N/A")
            self.mahasiswa_nama = f"{decoded.get('nama', 'Unknown')} (NRP: {nrp})"
        except Exception:
            # Fallback: get info from API
            try:
                r = self.session.get(f"{BASE_URL}/api/auth/validasi-token", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    self.mahasiswa_nomor = data.get("nomor")
                    self.mahasiswa_nama = f"{data.get('nama', 'Unknown')} (NRP: {data.get('nipnrp', 'N/A')})"
            except Exception:
                pass

    def validate_token(self) -> bool:
        """Check if current token is still valid."""
        try:
            r = self.session.get(f"{BASE_URL}/api/auth/validasi-token", timeout=10)
            if r.status_code == 200:
                return True
            # Token expired, try re-login
            return False
        except Exception:
            return False

    def get_kuliah_list(self, tahun: int, semester: int) -> list:
        """Get list of all courses for the semester."""
        r = self.session.get(
            f"{BASE_URL}/api/kuliah",
            params={"tahun": tahun, "semester": semester},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_active_presensi(self, kuliah_nomor: int, jenis_schema: int = 4) -> dict | None:
        """Check if there's an active attendance session for a course.

        Returns the active presensi dict if found (with open==1), else None.
        """
        r = self.session.get(
            f"{BASE_URL}/api/presensi/aktif-kuliah",
            params={"kuliah": kuliah_nomor, "jenis_schema": jenis_schema},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        if isinstance(data, list):
            for item in data:
                if item.get("open") == 1:
                    return item
        return None

    def submit_presensi(
        self,
        kuliah: int,
        jenis_schema: int,
        mahasiswa: int,
        key: str,
        kuliah_asal: int | None = None,
    ) -> dict:
        """Submit attendance for an active session."""
        payload = {
            "kuliah": kuliah,
            "jenis_schema": jenis_schema,
            "mahasiswa": mahasiswa,
            "key": key,
            "kuliah_asal": kuliah_asal,
        }
        r = self.session.post(
            f"{BASE_URL}/api/presensi/mahasiswa",
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_riwayat_presensi(self, kuliah: int, jenis_schema: int = 4) -> list:
        """Get attendance history for a course."""
        r = self.session.get(
            f"{BASE_URL}/api/presensi/riwayat",
            params={
                "kuliah": kuliah,
                "jenis_schema": jenis_schema,
                "nomor": self.mahasiswa_nomor,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()


# ══════════════════════════════════════════════════════════════
# Auto Attendance Monitor
# ══════════════════════════════════════════════════════════════


class AutoAttendanceMonitor:
    """Monitors and auto-submits attendance for all courses."""

    def __init__(self, client: ETHOLClient, tahun: int, semester: int, interval: int = 30):
        self.client = client
        self.tahun = tahun
        self.semester = semester
        self.interval = interval
        self.kuliah_list = []
        self.already_attended = set()  # Track sessions already attended (by key)
        self.stats = {"total_checks": 0, "total_presensi": 0, "errors": 0}

    def load_courses(self):
        """Load all courses for the semester."""
        log.info("📚 Memuat daftar matakuliah...")
        self.kuliah_list = self.client.get_kuliah_list(self.tahun, self.semester)
        log.info(f"   Ditemukan {len(self.kuliah_list)} matakuliah:")
        for kul in self.kuliah_list:
            mk = kul.get("matakuliah", {})
            dosen = kul.get("dosen", "N/A")
            gelar_dpn = (kul.get("gelar_dpn") or "").strip()
            gelar_blk = (kul.get("gelar_blk") or "").strip()
            nama_dosen = f"{gelar_dpn} {dosen}, {gelar_blk}".strip().strip(",").strip()
            log.info(f"   • [{kul['nomor']}] {mk.get('nama', 'N/A')} - {nama_dosen}")

    def check_and_attend(self):
        """Check all courses for active attendance and submit if found."""
        for kul in self.kuliah_list:
            nomor = kul["nomor"]
            kuliah_asal = kul.get("kuliah_asal")
            mk_nama = kul.get("matakuliah", {}).get("nama", "Unknown")
            jenis_schema = kul.get("jenisSchema", 4)

            try:
                active = self.client.get_active_presensi(nomor, jenis_schema)

                if active:
                    key = active.get("key")
                    if key in self.already_attended:
                        continue  # Already attended this session

                    log.info(f"🟢 PRESENSI AKTIF DITEMUKAN!")
                    log.info(f"   Matakuliah : {mk_nama}")
                    log.info(f"   Key        : {key}")
                    log.info(f"   Mencoba submit presensi...")

                    try:
                        result = self.client.submit_presensi(
                            kuliah=nomor,
                            jenis_schema=jenis_schema,
                            mahasiswa=self.client.mahasiswa_nomor,
                            key=key,
                            kuliah_asal=kuliah_asal,
                        )

                        if result.get("sukses"):
                            log.info(f"   ✅ PRESENSI BERHASIL! - {mk_nama}")
                            self.already_attended.add(key)
                            self.stats["total_presensi"] += 1
                        else:
                            pesan = result.get("pesan", "Unknown error")
                            log.warning(f"   ⚠️ Presensi response: {pesan}")
                            if "sudah" in pesan.lower():
                                self.already_attended.add(key)
                                log.info(f"   ℹ️ Sudah presensi sebelumnya.")

                    except Exception as e:
                        log.error(f"   ❌ Error submit presensi: {e}")
                        self.stats["errors"] += 1

            except Exception as e:
                log.error(f"   ❌ Error cek presensi {mk_nama}: {e}")
                self.stats["errors"] += 1

    def run(self):
        """Main monitoring loop."""
        log.info("=" * 60)
        log.info("🚀 ETHOL Auto Attendance Monitor - STARTED")
        log.info("=" * 60)
        log.info(f"   Tahun Ajaran  : {self.tahun}/{self.tahun + 1}")
        log.info(f"   Semester      : {'Ganjil' if self.semester == 1 else 'Genap'}")
        log.info(f"   Interval Cek  : {self.interval} detik")
        log.info(f"   Mode          : Pure HTTP (tanpa Chrome)")
        log.info("=" * 60)

        self.load_courses()

        log.info(f"\n🔄 Mulai monitoring presensi (setiap {self.interval} detik)...")
        log.info("   Tekan Ctrl+C untuk berhenti.\n")

        token_check_interval = 300  # Re-validate token every 5 minutes
        last_token_check = time.time()

        try:
            while True:
                self.stats["total_checks"] += 1
                now = datetime.now().strftime("%H:%M:%S")

                # Quiet log (only show check number every 10 checks to reduce noise)
                if self.stats["total_checks"] % 10 == 1 or self.stats["total_checks"] <= 3:
                    log.info(
                        f"[{now}] 🔍 Cek #{self.stats['total_checks']} "
                        f"(presensi: {self.stats['total_presensi']}, "
                        f"errors: {self.stats['errors']})"
                    )
                else:
                    log.debug(f"[{now}] Cek #{self.stats['total_checks']}")

                # Validate token periodically
                if time.time() - last_token_check > token_check_interval:
                    if not self.client.validate_token():
                        log.warning("⚠️ Token expired! Melakukan re-login...")
                        if not self.client.login():
                            log.error("❌ Re-login gagal. Retry dalam 60 detik...")
                            time.sleep(60)
                            continue
                        self.load_courses()
                    last_token_check = time.time()

                self.check_and_attend()
                time.sleep(self.interval)

        except KeyboardInterrupt:
            log.info("\n")
            log.info("🛑 Monitor dihentikan.")
            log.info(f"   Total cek    : {self.stats['total_checks']}")
            log.info(f"   Total presensi: {self.stats['total_presensi']}")
            log.info(f"   Total errors  : {self.stats['errors']}")
            log.info("=" * 60)


# ══════════════════════════════════════════════════════════════
# Main Entry Point
# ══════════════════════════════════════════════════════════════


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ███████╗████████╗██╗  ██╗ ██████╗ ██╗                    ║
║     ██╔════╝╚══██╔══╝██║  ██║██╔═══██╗██║                    ║
║     █████╗     ██║   ███████║██║   ██║██║                    ║
║     ██╔══╝     ██║   ██╔══██║██║   ██║██║                    ║
║     ███████╗   ██║   ██║  ██║╚██████╔╝███████╗               ║
║     ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝               ║
║                                                              ║
║         Auto Attendance Tool - PENS                          ║
║         Untuk keperluan eksperimen saja!                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")


def main():
    print_banner()

    config = load_config()

    email = config.get("email") or input("Email: ").strip()
    password = config.get("password") or input("Password: ").strip()

    if not email or not password:
        log.error("❌ Email dan password harus diisi!")
        return

    client = ETHOLClient(email=email, password=password)

    if not client.login():
        log.error("❌ Login gagal. Pastikan email dan password benar.")
        return

    monitor = AutoAttendanceMonitor(
        client=client,
        tahun=config.get("tahun", 2026),
        semester=config.get("semester", 1),
        interval=config.get("check_interval_seconds", 30),
    )

    monitor.run()


if __name__ == "__main__":
    main()
