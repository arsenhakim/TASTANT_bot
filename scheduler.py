from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import db


async def cek_reminder(app: Application):
    now_iso = datetime.now().isoformat()
    tasks_jatuh_tempo = db.get_due_unreminded_tasks(now_iso)

    if not tasks_jatuh_tempo:
        return

    chat_id = tasks_jatuh_tempo[0]["chat_id"]

    if len(tasks_jatuh_tempo) == 1:
        task = tasks_jatuh_tempo[0]
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Selesai", callback_data=f"done:{task['id']}"),
            InlineKeyboardButton("⏰ +1 jam", callback_data=f"snooze1h:{task['id']}"),
            InlineKeyboardButton("📅 Besok 9AM", callback_data=f"snoozetomorrow:{task['id']}"),
        ]])
        pesan = f"⏰ Reminder: {task['description']} (#{task['id']})"

    elif len(tasks_jatuh_tempo) <= 4:
        baris = [f"#{t['id']} — {t['description']}" for t in tasks_jatuh_tempo]
        pesan = f"⏰ {len(tasks_jatuh_tempo)} tugas jatuh tempo:\n\n" + "\n".join(baris)

        rows = []
        for t in tasks_jatuh_tempo:
            rows.append([
                InlineKeyboardButton(f"✅ #{t['id']}", callback_data=f"done:{t['id']}"),
                InlineKeyboardButton(f"⏰ #{t['id']} +1j", callback_data=f"snooze1h:{t['id']}"),
                InlineKeyboardButton(f"📅 #{t['id']} besok", callback_data=f"snoozetomorrow:{t['id']}"),
            ])
        keyboard = InlineKeyboardMarkup(rows)

    else:
        baris = [f"#{t['id']} — {t['description']}" for t in tasks_jatuh_tempo]
        ids_str = ",".join(str(t["id"]) for t in tasks_jatuh_tempo)
        pesan = f"⏰ {len(tasks_jatuh_tempo)} tugas jatuh tempo:\n\n" + "\n".join(baris)
        pesan += "\n\nKetik /today untuk pilih & selesaikan satu-satu."
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Selesai Semua", callback_data=f"doneall:{ids_str}"),
        ]])

    try:
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