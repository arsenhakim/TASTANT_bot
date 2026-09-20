import pytz
from datetime import datetime

WIB = pytz.timezone("Asia/Jakarta")

def now_wib() -> datetime:
    """
    Waktu sekarang di WIB, sebagai naive datetime (tanpa info zona waktu
    ditempel) supaya tetap gampang dibandingkan & disimpan sebagai ISO
    string kayak sebelumnya. Tidak peduli server jalan di zona waktu apa,
    ini SELALU balikin jam yang benar untuk WIB.
    """
    return datetime.now(WIB).replace(tzinfo=None)