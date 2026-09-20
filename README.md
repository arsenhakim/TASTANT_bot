# AI Task Assistant — Bot Telegram Pengingat Tugas

Bot Telegram pribadi yang mengubah pesan santai jadi tugas terstruktur (deskripsi, tanggal, jam, prioritas, kategori) menggunakan Google Gemini API, lalu mengingatkan otomatis saat tugas jatuh tempo — lengkap dengan snooze, tombol aksi langsung dari chat, dan pengelompokan per kategori/proyek.

Contoh: kirim *"Follow up vendor IT buat acara gathering #project_gathering"*, bot otomatis menyimpannya sebagai tugas kategori "Project Gathering", dan mengingatkan sesuai jam yang kamu pilih — dengan tombol ✅ Selesai / ⏰ Tunda 1 jam / 📅 Tunda ke besok.

## Fitur

- **Natural language input** — cukup ketik santai, tidak perlu hafal command untuk mencatat tugas
- **Pilihan waktu fleksibel** — kalau pesan tidak menyebut jam spesifik, bot tawarkan tombol pilihan (08:00 / 12:00 / 15:00 / tanpa reminder), bukan menebak sendiri
- **Kategorisasi hybrid** — AI otomatis nebak kategori dari konteks kalimat, tapi hashtag manual (`#kerja`, `#project_x`, dll) selalu jadi prioritas final. Kategori baru bisa tercipta bebas lewat hashtag, dan AI belajar mencocokkan ke kategori yang sudah pernah dipakai
- **Reminder otomatis + snooze** — background scheduler cek tiap menit, kirim reminder dengan tombol aksi
- **Update parsial pada reminder gabungan** — kalau 2-4 tugas jatuh tempo sekaligus, klik tombol salah satu tugas hanya menghapus tugas itu dari pesan, sisanya tetap bisa diproses tanpa perlu buka `/today` manual
- **Timezone-safe (WIB eksplisit)** — semua perhitungan waktu dipaksa pakai `Asia/Jakarta`, tidak bergantung zona waktu server tempat bot di-deploy
- **`/today`** — tugas hari ini + semua yang overdue (belum selesai), dikelompokkan per kategori
- **`/overdue`** — khusus tugas yang sudah terlewat, dikelompokkan per kategori
- **`/list`** — semua tugas pending per kategori; bisa difilter ke 1 kategori spesifik (`/list <kategori>`)
- **`/categories`** — lihat semua kategori yang sudah pernah dipakai
- **`/edit`** — revisi tugas dengan bahasa natural (paham konteks tugas lama, termasuk perubahan relatif seperti "diundur bulan depan", dan bisa ganti kategori)
- **`/backup`** — kirim file database langsung ke chat, bisa dibuka pakai DBeaver kapan saja
- **`/reset_db`** — reset database dari nol (dengan konfirmasi eksplisit, mencegah kehapus tidak sengaja)
- Riwayat tugas selesai disimpan permanen (tidak dihapus), berguna sebagai dokumentasi kerja
- Private — bot hanya merespons `chat_id` pemilik, tidak terbuka untuk publik

## Struktur Project

TASTANT_bot/
├── bot.py # entrypoint + semua handler Telegram
├── db.py # database SQLite (CRUD tasks + kategori)
├── extractor.py # ekstraksi tugas & kategori dari teks via Gemini API
├── scheduler.py # background job pengecek & pengirim reminder
├── reminder_ui.py # builder pesan & keyboard reminder (dipakai scheduler.py & bot.py)
├── timeutils.py # helper waktu WIB eksplisit, anti masalah timezone server
├── requirements.txt
├── .env.example
├── .gitignore
└── tasks.db # otomatis dibuat saat pertama kali run (di-ignore dari git)


## Setup

### 1. Buat Bot Telegram
1. Chat [@BotFather](https://t.me/BotFather) di Telegram
2. `/newbot`, ikuti instruksinya, simpan token yang diberikan

### 2. Cari tahu Chat ID kamu
Chat [@userinfobot](https://t.me/userinfobot), catat angka `Id` yang diberikan — ini yang membatasi bot supaya hanya kamu yang bisa pakai.

### 3. Dapatkan Gemini API Key (gratis)
Buat di [Google AI Studio](https://aistudio.google.com/apikey)

### 4. Install dependencies
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 5. Konfigurasi environment
```bash
copy .env.example .env
```
Isi `.env`:
TELEGRAM_BOT_TOKEN=token_dari_botfather
GEMINI_API_KEY=api_key_dari_google_ai_studio
ALLOWED_CHAT_ID=chat_id_kamu
TIMEZONE=Asia/Jakarta


### 6. Jalankan
```bash
python bot.py
```

Buka Telegram, kirim `/start` ke bot kamu.

## Deploy

Bot ini di-deploy di [JustRunMy.App](https://justrunmy.app) (tier gratis). Karena server hosting bisa berjalan di zona waktu berbeda (misal UTC), seluruh logic waktu di project ini sengaja dipaksa eksplisit ke WIB lewat `timeutils.py` — jangan gunakan `datetime.now()` polos di mana pun dalam project ini, selalu pakai `now_wib()`.

## Command yang Tersedia

| Command | Fungsi |
|---|---|
| `/start` | Info cara pakai bot |
| `/today` | Tugas hari ini + overdue, per kategori |
| `/list` | Semua tugas pending, per kategori |
| `/list <kategori>` | Filter tugas pending ke 1 kategori spesifik |
| `/overdue` | Khusus tugas yang terlewat, per kategori |
| `/categories` | Lihat semua kategori yang sudah pernah dipakai |
| `/done <id>` | Tandai tugas selesai |
| `/edit <id> <perubahan>` | Revisi tugas dengan bahasa natural (termasuk kategori) |
| `/delete <id>` | Hapus tugas |
| `/backup` | Kirim file database sebagai dokumen Telegram |
| `/reset_db CONFIRM` | Hapus semua data, mulai fresh (butuh konfirmasi eksplisit) |
| *(pesan bebas)* | Otomatis diekstrak jadi tugas baru |

## Cara Pakai Kategori

- **Kategori baru:** sertakan hashtag di pesan, contoh: `Survey lokasi tender #tpk_banjarmasin`. Gunakan underscore untuk multi-kata, konsisten setiap kali menyebut kategori yang sama.
- **Tanpa hashtag:** AI otomatis coba cocokkan ke kategori yang sudah pernah kamu pakai berdasarkan konteks kalimat. Kalau tidak yakin, masuk kategori "Umum".
- **Salah kategori:** perbaiki lewat `/edit <id> #kategori_yang_benar`, tidak perlu hapus-buat ulang.

## Cara Kerja Singkat

1. Pesan masuk → daftar kategori yang sudah ada dikirim sebagai konteks ke Gemini API, bersama tanggal & jam WIB saat ini (`now_wib()`)
2. Hasil ekstraksi (deskripsi, due_at, priority, category) diproses; hashtag eksplisit di pesan selalu override tebakan kategori dari AI
3. Kalau tidak ada waktu spesifik, bot tawarkan tombol pilihan jam sebelum tugas dianggap final
4. Disimpan ke SQLite
5. Scheduler berjalan di background tiap 1 menit (waktu WIB), cek tugas yang jatuh tempo dan belum diingatkan
6. Kalau 1 tugas jatuh tempo → kirim reminder dengan tombol aksi individual
7. Kalau 2-4 tugas numpuk → 1 pesan dengan tombol per tugas; klik salah satu hanya menghapus baris itu, sisanya tetap bisa diproses dari pesan yang sama
8. Kalau lebih dari 4 tugas numpuk → ringkasan + tombol "Selesai Semua", arahkan ke `/today` untuk detail

## Known Limitations

- Free tier Gemini API punya rate limit (~20 request/menit) — sudah ditangani dengan retry otomatis 1x setelah jeda, tapi tetap bisa gagal kalau dipakai sangat intensif dalam waktu singkat
- Dirancang untuk single-user (dibatasi via `ALLOWED_CHAT_ID`), belum multi-tenant
- Kategori yang typo (misal `#project_gathring` vs `#project_gathering`) akan tercatat sebagai 2 kategori terpisah — belum ada fitur rename/merge kategori, perbaikan manual lewat `/edit` satu-satu
- Tier gratis hosting (JustRunMy.App Starter) punya batas runtime yang mungkin butuh reset manual berkala — perlu dipantau

## Ide Pengembangan Lanjutan

- Rename/merge kategori yang typo atau duplikat
- Recurring task per kategori ("setiap Senin jam 9, kategori Kerja")
- Statistik per kategori ("bulan ini kategori Project selesai 12 dari 15 tugas") — datanya sudah tersedia karena riwayat tidak dihapus
- Voice note → transkripsi → tugas