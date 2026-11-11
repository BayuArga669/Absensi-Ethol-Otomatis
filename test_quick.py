"""Quick test - login and check all courses for active presensi"""
import sys, os, json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from absen_otomatis import ETHOLClient

config = json.load(open('config.json', encoding='utf-8'))
client = ETHOLClient(config['email'], config['password'])

if client.login():
    kuliah_list = client.get_kuliah_list(config['tahun'], config['semester'])
    print('\nMatakuliah (' + str(len(kuliah_list)) + '):')
    for kul in kuliah_list:
        mk = kul.get('matakuliah', {})
        nomor = kul['nomor']
        nama = mk.get('nama', 'N/A')
        active = client.get_active_presensi(nomor)
        status = 'AKTIF! key=' + str(active.get('key')) if active else 'tidak aktif'
        print('  [' + str(nomor) + '] ' + nama + ' -> ' + status)
    print('\nDone!')
else:
    print('Login gagal!')
