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


load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Halo! Kirim tugas dengan bahasa santai, contoh:\n"
        "\"Ingetin follow up laporan besok jam 9\"\n\n"
        "Perintah lain:\n"
        "/list - lihat tugas pending\n"
        "/done <id> - tandai selesai\n"
        "/delete <id> - hapus tugas"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    pesan_user = update.message.text

    try:
        hasil = extract_task(pesan_user)
    except RuntimeError:
        await update.message.reply_text(
            "⚠️ Lagi kena batas pemakaian gratis API sesaat. Coba kirim ulang dalam beberapa detik."
        )
        return

    if not hasil.get("description") or not hasil["description"].strip():
        await update.message.reply_text(
            "Hmm, saya tidak menangkap tugas apa pun dari pesan itu. "
            "Coba jelaskan lebih detail, misal: \"follow up laporan besok jam 10\"."
        )
        return
    task_id = db.add_task(
        chat_id=chat_id,
        description=hasil["description"],
        due_at=hasil["due_at"],
        priority=hasil["priority"],
    )

    if hasil["due_at"]:
        waktu = datetime.fromisoformat(hasil["due_at"]).strftime("%a, %d %b %Y %H:%M")
        balasan = f"✅ Tersimpan #{task_id}: {hasil['description']}\n⏰ {waktu}"
    else:
        balasan = f"✅ Tersimpan #{task_id}: {hasil['description']} (tanpa waktu spesifik)"

    await update.message.reply_text(balasan)


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
        BotCommand("list", "Lihat tugas yang belum selesai"),
        BotCommand("done", "Tandai tugas selesai, contoh /done 3"),
        BotCommand("delete", "Hapus tugas, contoh /delete 3"),
        BotCommand("start", "Info cara pakai bot"),
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
    app.add_handler(CommandHandler("delete", delete_cmd, filters=own_chat_filter))
    app.add_handler(CommandHandler("edit", edit_cmd, filters=own_chat_filter))
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

    action, data = query.data.split(":")
    chat_id = query.message.chat_id

    if action == "doneall":
        task_ids = [int(x) for x in data.split(",")]
        for tid in task_ids:
            db.mark_done(tid, chat_id)
        await query.edit_message_text(f"✅ {len(task_ids)} tugas ditandai selesai sekaligus.")
        return

    task_id = int(data)

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

if __name__ == "__main__":
    main()