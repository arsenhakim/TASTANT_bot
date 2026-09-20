# AI Task Assistant — Bot Telegram Pengingat Tugas

Bot Telegram pribadi yang mengubah pesan santai jadi tugas terstruktur (deskripsi, tanggal, jam, prioritas) menggunakan Google Gemini API, lalu mengingatkan otomatis saat tugas jatuh tempo — lengkap dengan snooze dan tombol aksi langsung dari chat.

Contoh: kirim *"Ingetin follow up laporan besok jam 10"*, bot otomatis menyimpannya sebagai tugas dengan due date besok jam 10:00, dan mengirim reminder otomatis pas waktunya — dengan tombol ✅ Selesai / ⏰ Tunda 1 jam / 📅 Tunda ke besok.

## Fitur

- **Natural language input** — cukup ketik santai, tidak perlu hafal command untuk mencatat tugas
- **Reminder otomatis + snooze** — background scheduler cek tiap menit, kirim reminder dengan tombol aksi
- **`/today`** — tugas hari ini + semua yang overdue (belum selesai)
- **`/overdue`** — khusus tugas yang sudah terlewat
- **`/edit`** — revisi tugas dengan bahasa natural (paham konteks tugas lama, termasuk perubahan relatif seperti "diundur bulan depan")
- **`/list`, `/done`, `/delete`** — kelola tugas dasar
- Riwayat tugas selesai disimpan permanen (tidak dihapus), berguna sebagai dokumentasi kerja
- Private — bot hanya merespons `chat_id` pemilik, tidak terbuka untuk publik
- - **Pilihan waktu fleksibel** — kalau pesan tidak menyebut jam spesifik, bot tawarkan tombol pilihan (08:00 / 12:00 / 15:00 / tanpa reminder), bukan menebak sendiri

## Struktur Project
TASTANT_bot/
├── bot.py # entrypoint + semua handler Telegram
├── db.py # database SQLite (CRUD tasks)
├── extractor.py # ekstraksi tugas dari teks via Gemini API
├── scheduler.py # background job pengecek & pengirim reminder
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

## Command yang Tersedia

## Command yang Tersedia

| Command | Fungsi |
|---|---|
| `/start` | Info cara pakai bot |
| `/today` | Tugas hari ini + overdue |
| `/list` | Semua tugas pending |
| `/overdue` | Khusus tugas yang terlewat |
| `/done <id>` | Tandai tugas selesai |
| `/edit <id> <perubahan>` | Revisi tugas dengan bahasa natural |
| `/delete <id>` | Hapus tugas |
| `/backup` | Kirim file database sebagai dokumen Telegram |
| `/reset_db CONFIRM` | Hapus semua data, mulai fresh (butuh konfirmasi eksplisit) |
| *(pesan bebas)* | Otomatis diekstrak jadi tugas baru |

## Cara Kerja Singkat

1. Pesan masuk → dikirim ke Gemini API dengan prompt yang menyertakan tanggal & jam saat ini sebagai konteks
2. Hasil ekstraksi (deskripsi, due_at, priority) disimpan ke SQLite
3. Scheduler berjalan di background tiap 1 menit, cek tugas yang jatuh tempo dan belum diingatkan
4. Kalau 1 tugas jatuh tempo → kirim reminder dengan tombol aksi individual
5. Kalau lebih dari 1 tugas numpuk (≤4) → tombol per tugas dalam satu pesan; lebih dari 4 → ringkasan + tombol "Selesai Semua"

## Known Limitations

- Free tier Gemini API punya rate limit (~20 request/menit) — sudah ditangani dengan retry otomatis 1x setelah jeda, tapi tetap bisa gagal kalau dipakai sangat intensif dalam waktu singkat
- Dirancang untuk single-user (dibatasi via `ALLOWED_CHAT_ID`), belum multi-tenant

## Ide Pengembangan Lanjutan

- Kategori/label tugas (kerja, pribadi, dll)
- Recurring task ("setiap Senin jam 9")
- Statistik ("bulan ini selesai 47 tugas") — datanya sudah tersedia karena riwayat tidak dihapus
- Voice note → transkripsi → tugas
- Morning briefing otomatis