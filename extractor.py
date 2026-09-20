import os
import json
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def extract_task(user_message: str) -> dict:
    now = datetime.now()
    prompt = f"""Kamu adalah asisten yang mengekstrak informasi tugas dari pesan santai berbahasa Indonesia.

Konteks waktu sekarang: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

Dari pesan berikut, ekstrak:
- description: deskripsi tugas yang ringkas
- due_at: tanggal & jam dalam format "YYYY-MM-DDTHH:MM:SS". PENTING: isi null jika JAM SPESIFIK tidak disebutkan,
  walaupun tanggal/harinya disebutkan. Contoh: "besok aku harus makan steak" -> due_at: null (karena tidak ada jam
  yang disebut, meskipun ada kata "besok"). Contoh: "besok jam 7 makan steak" -> due_at diisi tanggal besok jam 07:00.
- priority: "low", "normal", atau "high"

Balas HANYA JSON, tanpa teks lain, tanpa markdown code fence.

Pesan: "{user_message}"
"""
    error_terakhir = None
    for percobaan in range(2):
        try:
            interaction = client.interactions.create(model="gemini-3.6-flash", input=prompt)
            raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            error_terakhir = e
            if percobaan == 0:
                print("Kena limit API, tunggu 10 detik lalu coba lagi otomatis...")
                time.sleep(10)  # jeda tetap, tidak bergantung format pesan error provider manapun

    raise RuntimeError(f"Gagal menghubungi API setelah retry: {error_terakhir}") from error_terakhir

def extract_edit(current_task: dict, instruksi: str) -> dict:
    now = datetime.now()
    prompt = f"""Kamu membantu merevisi sebuah tugas yang sudah ada berdasarkan instruksi perubahan dari user.

Konteks waktu sekarang: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

Data tugas SAAT INI (sebelum diubah):
- description: {current_task['description']}
- due_at: {current_task['due_at']}
- priority: {current_task['priority']}

Instruksi perubahan dari user: "{instruksi}"

Berdasarkan instruksi itu, tentukan nilai BARU untuk tugas ini. Jika instruksi menyebut
waktu relatif (misal "bulan depan", "minggu depan", "diundur 2 hari"), hitung dari
due_at SAAT INI di atas, bukan dari waktu sekarang. Jika sebuah field tidak disinggung
sama sekali di instruksi, kembalikan nilai LAMA-nya apa adanya (jangan null).

Balas HANYA JSON:
{{"description": "...", "due_at": "YYYY-MM-DDTHH:MM:SS" atau null jika memang tidak ada, "priority": "low|normal|high"}}
"""

    try:
        interaction = client.interactions.create(model="gemini-3.6-flash", input=prompt)
    except Exception as e:
        raise RuntimeError(f"Gagal menghubungi Gemini API: {e}") from e

    raw = interaction.output_text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)