import os
import json
import sqlite3
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai

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
    now = datetime.now()
    existing_categories = existing_categories or []
    daftar_kategori_str = ", ".join(existing_categories) if existing_categories else "(belum ada)"

    prompt = f"""Kamu adalah asisten yang mengekstrak informasi tugas dari pesan santai berbahasa Indonesia.

Konteks waktu sekarang: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

Kategori yang SUDAH PERNAH dipakai user sebelumnya: {daftar_kategori_str}

Dari pesan berikut, ekstrak:
- description: deskripsi tugas yang ringkas (buang hashtag dari deskripsi kalau ada)
- due_at: format "YYYY-MM-DDTHH:MM:SS", null jika jam spesifik tidak disebutkan
- priority: "low", "normal", atau "high"
- category: PRIORITASKAN mencocokkan ke salah satu kategori yang SUDAH PERNAH dipakai di atas kalau
  konteksnya jelas berkaitan. Kalau tidak ada yang cocok, isi "Umum". JANGAN membuat nama kategori baru
  sendiri kecuali benar-benar jelas dari konteks dan tidak ada opsi lama yang cocok sama sekali.

Balas HANYA JSON, tanpa teks lain.

Pesan: "{user_message}"
"""
    try:
        interaction = client.interactions.create(model="gemini-3.6-flash", input=prompt)
    except Exception as e:
        raise RuntimeError(f"Gagal menghubungi Gemini API: {e}") from e

    raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()
    hasil = json.loads(raw)

    hashtag_kategori = _cari_hashtag_kategori(user_message)
    if hashtag_kategori:
        hasil["category"] = hashtag_kategori

    return hasil

def extract_edit(current_task: dict, instruksi: str, existing_categories: list[str] = None) -> dict:
    now = datetime.now()
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

Instruksi perubahan: "{instruksi}"

Tentukan nilai BARU. Field yang tidak disinggung, kembalikan nilai LAMA apa adanya. Waktu relatif dihitung
dari due_at SAAT INI, bukan dari sekarang.

Balas HANYA JSON:
{{"description": "...", "due_at": "..." atau null, "priority": "low|normal|high", "category": "..."}}
"""
    try:
        interaction = client.interactions.create(model="gemini-3.6-flash", input=prompt)
    except Exception as e:
        raise RuntimeError(f"Gagal menghubungi Gemini API: {e}") from e

    raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()
    hasil = json.loads(raw)

    hashtag_kategori = _cari_hashtag_kategori(instruksi)
    if hashtag_kategori:
        hasil["category"] = hashtag_kategori

    return hasil