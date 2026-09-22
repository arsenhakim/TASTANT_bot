import os
import json
import sqlite3
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from timeutils import now_wib

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

def _cari_hashtag_kategori(text: str) -> str | None:
    match = re.search(r"#(\w+)", text)
    if not match:
        return None
    raw = match.group(1).lower()
    kata = raw.replace("_", " ")
    return kata.title()

def extract_task(user_message: str, existing_categories: list[str] = None) -> dict:
    now = now_wib()
    existing_categories = existing_categories or []
    daftar_kategori_str = ", ".join(existing_categories) if existing_categories else "(belum ada)"

    prompt = f"""Kamu adalah asisten yang mengekstrak informasi tugas dari pesan santai berbahasa Indonesia.

Konteks waktu sekarang: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

Kategori yang SUDAH PERNAH dipakai user sebelumnya: {daftar_kategori_str}

Dari pesan berikut, ekstrak:
- description: deskripsi tugas yang ringkas (buang hashtag dari deskripsi kalau ada)
- due_at: format "YYYY-MM-DDTHH:MM:SS". WAJIB isi null jika JAM SPESIFIK (misal "jam 9", "jam 3 sore",
  "sebelum jam 15:00") TIDAK disebutkan sama sekali di pesan — walaupun ada kata hari/tanggal seperti
  "besok", "besok minggu", "lusa", dst. Contoh: "besok saya ketemuan sama klien" -> due_at: null (karena
  tidak ada jam yang disebut, meski ada kata "besok").
  Jika jam DISEBUTKAN, baru isi due_at sesuai tanggal & jam tersebut. Untuk pola "besok <nama hari>"
  (misal "besok minggu jam 3 sore"), "besok <nama hari>" artinya HARI ITU YANG AKAN DATANG BERIKUTNYA
  (bukan otomatis +1 hari) — cari kemunculan nama hari itu yang paling dekat ke depan dari waktu sekarang.
  Contoh: hari ini Senin 21 September 2026, "besok minggu jam 3 sore" -> Minggu 27 September 2026, 15:00.
- inferred_date: format "YYYY-MM-DD", null jika benar-benar tidak ada petunjuk tanggal/hari apa pun di
  pesan. WAJIB diisi (walau due_at null karena jam tidak disebutkan) jika ada petunjuk tanggal/hari
  apa pun — gunakan LOGIC HARI YANG SAMA PERSIS seperti due_at (termasuk pola "besok <hari>"), cuma
  cukup isi tanggalnya saja tanpa perlu jam. Contoh: "besok saya ketemuan klien" (tanpa jam) ->
  due_at: null, inferred_date: tanggal besok (+1 hari dari sekarang). "besok minggu saya harus beli
  sesuatu" (tanpa jam) -> due_at: null, inferred_date: tanggal Minggu terdekat ke depan.
- priority: "low", "normal", atau "high"
- category: PRIORITASKAN mencocokkan ke salah satu kategori yang SUDAH PERNAH dipakai di atas kalau
  konteksnya jelas berkaitan. Kalau tidak ada yang cocok, isi "Umum". JANGAN membuat nama kategori baru
  sendiri kecuali benar-benar jelas dari konteks dan tidak ada opsi lama yang cocok sama sekali.

PENTING: Jika pesan berisi LEBIH DARI SATU tugas berbeda (dipisah koma, "dan", titik, atau baris baru),
pecah jadi beberapa tugas terpisah. Balas SELALU dalam bentuk JSON ARRAY — satu object per tugas dengan
field yang sama seperti di atas (description, due_at, priority, category) — walaupun pesan cuma berisi
SATU tugas (tetap bungkus jadi array berisi 1 object).

Balas HANYA JSON array, tanpa teks lain, tanpa markdown code fence.

Pesan: "{user_message}"
"""
    try:
        interaction = client.interactions.create(model="gemini-3.1-flash-lite", input=prompt)
    except Exception as e:
        print(f"[EXTRACT_TASK ERROR] {type(e).__name__}: {e}")
        raise RuntimeError("api_error") from e

    raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()

    try:
        hasil = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[EXTRACT_TASK JSON ERROR] Gagal parse. Raw response Gemini:\n---\n{raw}\n---")
        raise RuntimeError("json_error") from e

    hashtag_kategori = _cari_hashtag_kategori(user_message)
    if hashtag_kategori:
        for item in hasil:
            item["category"] = hashtag_kategori

    return hasil

def extract_edit(current_task: dict, instruksi: str, existing_categories: list[str] = None) -> dict:
    now = now_wib()
    existing_categories = existing_categories or []
    daftar_kategori_str = ", ".join(existing_categories) if existing_categories else "(belum ada)"

    prompt = f"""Kamu membantu merevisi sebuah tugas yang sudah ada berdasarkan instruksi perubahan dari user.

Konteks waktu sekarang: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

Kategori yang sudah pernah dipakai: {daftar_kategori_str}

Data tugas SAAT INI:
- description: {current_task['description']}
- due_at: {current_task['due_at']}
- priority: {current_task['priority']}
- category: {current_task.get('category', 'Umum')}
- pending_date (tanggal yang sempat disebut tapi belum resmi jadi due_at): {current_task.get('pending_date') or 'tidak ada'}

Instruksi perubahan: "{instruksi}"

Tentukan nilai BARU. Field yang tidak disinggung, kembalikan nilai LAMA apa adanya. Waktu relatif
(seperti "besok", "minggu depan") dihitung dari due_at SAAT INI, bukan dari waktu sekarang.

WAJIB isi due_at null HANYA jika instruksi secara eksplisit menghapus waktu (misal "hapus waktunya",
"jadi tanpa deadline") — jika instruksi tidak menyinggung waktu sama sekali, kembalikan due_at LAMA
apa adanya, JANGAN diubah jadi null.

Jika instruksi menyebut jam baru, sertakan tanggal & jam barunya. Untuk pola "besok <nama hari>"
(misal "besok minggu jam 3 sore"), "besok <nama hari>" artinya HARI ITU YANG AKAN DATANG BERIKUTNYA
(bukan otomatis +1 hari) — cari kemunculan nama hari itu yang paling dekat ke depan dari due_at SAAT INI.
Contoh: due_at saat ini Senin 21 September 2026, "besok minggu jam 3 sore" -> Minggu 27 September 2026, 15:00.

Balas HANYA JSON:
{{"description": "...", "due_at": "..." atau null, "priority": "low|normal|high", "category": "..."}}
"""
    try:
        interaction = client.interactions.create(model="gemini-3.1-flash-lite", input=prompt)
    except Exception as e:
        print(f"[EXTRACT_EDIT ERROR] {type(e).__name__}: {e}")
        raise RuntimeError("api_error") from e

    raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()

    try:
        hasil = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[EXTRACT_EDIT JSON ERROR] Gagal parse. Raw response Gemini:\n---\n{raw}\n---")
        raise RuntimeError("json_error") from e

    hashtag_kategori = _cari_hashtag_kategori(instruksi)
    if hashtag_kategori:
        hasil["category"] = hashtag_kategori

    return hasil