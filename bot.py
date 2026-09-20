import os
import json
import sqlite3
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
)
import db
from extractor import extract_edit, extract_task
from scheduler import start_scheduler
from telegram import BotCommand
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup


load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Aku Tastant asisten tugas harian kamu, Kirim tugas yang harus kamu kerjakan dengan bahasa santai, nanti aku rekap in 👍🙌 contoh:\n"
        "\"Ingetin follow up laporan besok jam 9\"\n\n"
        "Kalau tidak sebut jam, saya akan tawarkan pilihan waktu reminder.\n\n"
        "📋 Lihat tugas:\n"
        "/today - tugas hari ini + overdue\n"
        "/list - semua tugas pending\n"
        "/overdue - khusus yang terlewat\n\n"
        "✏️ Kelola tugas:\n"
        "/done <id> - tandai selesai\n"
        "/edit <id> <perubahan> - revisi tugas\n"
        "/delete <id> - hapus tugas\n\n"
        "🔧 Lainnya:\n"
        "/backup - kirim file database\n"
        "/reset_db - reset database (perlu konfirmasi)"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    pesan_user = update.message.text

    try:
        hasil = extract_task(pesan_user)
    except RuntimeError:
        await update.message.reply_text("⚠️ Lagi kena batas API, coba lagi sebentar.")
        return

    if not hasil.get("description") or not hasil["description"].strip():
        await update.message.reply_text(
            "Hmm, saya tidak menangkap tugas apa pun dari pesan itu. Coba jelaskan lebih detail."
        )
        return

    if hasil["due_at"]:
        # Ada waktu spesifik dari NLP, langsung simpan seperti biasa
        task_id = db.add_task(chat_id, hasil["description"], hasil["due_at"], hasil["priority"])
        waktu = datetime.fromisoformat(hasil["due_at"]).strftime("%a, %d %b %Y %H:%M")
        await update.message.reply_text(f"✅ Tersimpan #{task_id}: {hasil['description']}\n⏰ {waktu}")
        return

    # Tidak ada waktu spesifik -> simpan dulu tanpa due_at, lalu tawarkan pilihan
    task_id = db.add_task(chat_id, hasil["description"], None, hasil["priority"])

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌅 08:00", callback_data=f"settime:{task_id}:08:00"),
            InlineKeyboardButton("☀️ 12:00", callback_data=f"settime:{task_id}:12:00"),
            InlineKeyboardButton("🌇 15:00", callback_data=f"settime:{task_id}:15:00"),
        ],
        [InlineKeyboardButton("🔕 Tanpa reminder", callback_data=f"settime:{task_id}:none")],
    ])
    await update.message.reply_text(
        f"✅ Tersimpan #{task_id}: {hasil['description']}\n"
        f"Tidak ada waktu spesifik — mau diingatkan kapan?",
        reply_markup=keyboard
    )


async def list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    tasks = db.list_pending_tasks(chat_id)

    if not tasks:
        await update.message.reply_text("Tidak ada tugas pending. 🎉")
        return

    baris = []
    for t in tasks:
        waktu = "(tanpa waktu)" if not t["due_at"] else datetime.fromisoformat(t["due_at"]).strftime("%d %b %H:%M")
        baris.append(f"#{t['id']} — {t['description']} ({waktu})")

    await update.message.reply_text("📋 Tugas pending:\n\n" + "\n".join(baris))

async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Format: /done <id>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("fungsi /done itu pakai ID dan harus berupa angka bos. Cek dulu itu pakai /list untuk lihat ID yang benar.")
        return

    if db.mark_done(task_id, chat_id):
        await update.message.reply_text(f"✅ Task #{task_id} selesai.")
    else:
        await update.message.reply_text(f"Task #{task_id} tidak ditemukan.")


async def delete_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Format: /delete <id>")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("fungsi /delete itu pakai ID dan harus berupa angka bos. Cek dulu itu pakai /list untuk lihat ID yang benar.")
        return

    if db.delete_task(task_id, chat_id):
        await update.message.reply_text(f"🗑️ Task #{task_id} dihapus.")
    else:
        await update.message.reply_text(f"Task #{task_id} tidak ditemukan.")

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Info cara pakai bot"),
        BotCommand("list", "Lihat tugas yang belum selesai"),
        BotCommand("today", "Tugas hari ini + yang overdue"),
        BotCommand("overdue", "Khusus tugas yang terlewat"),
        BotCommand("done", "Tandai tugas selesai, contoh /done 3"),
        BotCommand("delete", "Hapus tugas, contoh /delete 3"),
        BotCommand("edit", "Revisi tugas, contoh /edit 3 majukan jam 2"),
        BotCommand("backup", "Kirim file backup database"),
        BotCommand("reset_db", "Buat Database Fresh Kembali"),
    ])
    start_scheduler(application)

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])
own_chat_filter = filters.Chat(chat_id=ALLOWED_CHAT_ID)

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])
own_chat_filter = filters.Chat(chat_id=ALLOWED_CHAT_ID)

def main():
    db.init_db()
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start, filters=own_chat_filter))
    app.add_handler(CommandHandler("list", list_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("today", today_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("overdue", overdue_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("done", done_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("edit", edit_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("delete", delete_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("backup", backup_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("reset_db", reset_db_cmd, filters=own_chat_filter))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & own_chat_filter, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler)) 

    print("Bot jalan...")
    app.run_polling()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.message.chat_id != ALLOWED_CHAT_ID:
        await query.answer("Bot ini private.", show_alert=True)
        return
    await query.answer()

    parts = query.data.split(":")
    action = parts[0]
    chat_id = query.message.chat_id

    if action == "doneall":
        task_ids = [int(x) for x in parts[1].split(",")]
        for tid in task_ids:
            db.mark_done(tid, chat_id)
        await query.edit_message_text(f"✅ {len(task_ids)} tugas ditandai selesai sekaligus.")
        return

    if action == "settime":
        task_id = int(parts[1])
        jam = parts[2]

        if jam == "none":
            await query.edit_message_text(f"🔕 Task #{task_id} disimpan tanpa reminder.")
            return

        jam_int = int(jam)
        target = datetime.now().replace(hour=jam_int, minute=0, second=0, microsecond=0)
        if target < datetime.now():
            target += timedelta(days=1)

        db.update_task(task_id, chat_id, due_at=target.isoformat())
        await query.edit_message_text(f"⏰ Task #{task_id} dijadwalkan {target.strftime('%a %H:%M')}")
        return

    # Sisa action ("done", "snooze1h", "snoozetomorrow") semuanya formatnya "action:task_id"
    task_id = int(parts[1])

    if action == "done":
        db.mark_done(task_id, chat_id)
        await query.edit_message_text(f"✅ Task #{task_id} ditandai selesai.")
    elif action == "snooze1h":
        new_due = (datetime.now() + timedelta(hours=1)).isoformat()
        db.update_task(task_id, chat_id, due_at=new_due)
        await query.edit_message_text(f"⏰ Task #{task_id} ditunda 1 jam.")
    elif action == "snoozetomorrow":
        besok = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        db.update_task(task_id, chat_id, due_at=besok.isoformat())
        await query.edit_message_text(f"📅 Task #{task_id} ditunda ke besok jam 09:00.")
    


async def edit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if len(context.args) < 2:
        await update.message.reply_text("Format: /edit <id> <perubahan>")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID harus berupa angka.")
        return

    current_task = db.get_task(task_id, chat_id)
    if not current_task:
        await update.message.reply_text(f"Task #{task_id} tidak ditemukan.")
        return

    instruksi = " ".join(context.args[1:])
    try:
        hasil = extract_edit(current_task, instruksi)
    except RuntimeError:
        await update.message.reply_text("⚠️ Lagi kena batas API, coba lagi sebentar.")
        return

    db.update_task(
        task_id, chat_id,
        description=hasil.get("description"),
        due_at=hasil.get("due_at"),
        priority=hasil.get("priority"),
    )
    waktu = datetime.fromisoformat(hasil["due_at"]).strftime("%d %b %H:%M") if hasil.get("due_at") else "(tanpa waktu)"
    await update.message.reply_text(f"✏️ Task #{task_id} diperbarui:\n{hasil['description']} — {waktu}")


async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = db.list_today_tasks(update.effective_chat.id)
    if not tasks:
        await update.message.reply_text("Tidak ada tugas hari ini. 🎉")
        return

    hari_ini_str = datetime.now().strftime("%Y-%m-%d")
    baris = []
    for t in tasks:
        due_dt = datetime.fromisoformat(t["due_at"])
        flag = "🔴" if due_dt.strftime("%Y-%m-%d") < hari_ini_str else "🔵"
        baris.append(f"{flag} #{t['id']} — {t['description']} ({due_dt.strftime('%H:%M')})")

    await update.message.reply_text("📅 Tugas hari ini:\n\n" + "\n".join(baris))

async def overdue_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = db.list_overdue_tasks(update.effective_chat.id)
    if not tasks:
        await update.message.reply_text("Tidak ada tugas yang terlewat. 👍")
        return
    baris = [f"#{t['id']} — {t['description']} (lewat {datetime.fromisoformat(t['due_at']).strftime('%d %b %H:%M')})" for t in tasks]
    await update.message.reply_text("🔴 Tugas terlewat:\n\n" + "\n".join(baris))

async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kirim file database sebagai dokumen Telegram, semacam backup manual."""
    if not os.path.exists(db.DB_PATH):
        await update.message.reply_text("Belum ada database.")
        return
    await update.message.reply_document(
        document=open(db.DB_PATH, "rb"),
        filename="tasks_backup.db",
        caption=f"📦 Backup database — {datetime.now().strftime('%d %b %Y %H:%M')}"
    )


async def reset_db_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hapus SEMUA data, mulai dari kosong lagi. Minta konfirmasi dulu."""
    if not context.args or context.args[0] != "CONFIRM":
        await update.message.reply_text(
            "⚠️ Ini akan menghapus SEMUA data tugas (termasuk riwayat) secara permanen.\n"
            "Kalau yakin, ketik: /reset_db CONFIRM"
        )
        return

    os.remove(db.DB_PATH)
    db.init_db()
    await update.message.reply_text("🗑️ Database direset. Mulai dari kosong lagi.")

if __name__ == "__main__":
    main()