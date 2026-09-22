from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db
from timeutils import now_wib
from reminder_ui import build_single_keyboard, build_grouped_message


async def cek_reminder(app: Application):
    now_iso = now_wib().isoformat()
    tasks_jatuh_tempo = db.get_due_unreminded_tasks(now_iso)
    print(f"[SCHEDULER CHECK] now={now_iso} | ditemukan {len(tasks_jatuh_tempo)} task jatuh tempo: {[(t['id'], t['due_at']) for t in tasks_jatuh_tempo]}")
    if not tasks_jatuh_tempo:
        return

    chat_id = tasks_jatuh_tempo[0]["chat_id"]

    try:
        if len(tasks_jatuh_tempo) == 1:
            task = tasks_jatuh_tempo[0]
            keyboard = build_single_keyboard(task["id"])
            pesan = f"⏰ Reminder: {task['description']} (#{task['id']})"
            await app.bot.send_message(chat_id=chat_id, text=pesan, reply_markup=keyboard)

        elif len(tasks_jatuh_tempo) <= 4:
            tasks_map = {t["id"]: t["description"] for t in tasks_jatuh_tempo}
            pesan, keyboard = build_grouped_message(tasks_map)
            sent = await app.bot.send_message(chat_id=chat_id, text=pesan, reply_markup=keyboard)
            app.bot_data[f"grp_{sent.message_id}"] = tasks_map  # simpan mapping buat di-edit parsial nanti

        else:
            baris = [f"#{t['id']} — {t['description']}" for t in tasks_jatuh_tempo]
            ids_str = ",".join(str(t["id"]) for t in tasks_jatuh_tempo)
            pesan = f"⏰ {len(tasks_jatuh_tempo)} tugas jatuh tempo:\n\n" + "\n".join(baris)
            pesan += "\n\nKetik /today untuk pilih & selesaikan satu-satu."
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Selesai Semua", callback_data=f"doneall:{ids_str}")]])
            await app.bot.send_message(chat_id=chat_id, text=pesan, reply_markup=keyboard)

        for t in tasks_jatuh_tempo:
            db.mark_reminded(t["id"])
    except Exception as e:
        print(f"Gagal kirim reminder: {e}")


def start_scheduler(app: Application):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        cek_reminder,
        "interval",
        minutes=1,
        args=[app],
        misfire_grace_time=30,  # toleransi telat sampai 30 detik, tetap dijalankan
    )
    scheduler.start()
    return scheduler