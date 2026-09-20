from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_single_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Selesai", callback_data=f"done:{task_id}"),
        InlineKeyboardButton("⏰ +1 jam", callback_data=f"snooze1h:{task_id}"),
        InlineKeyboardButton("📅 Besok 9AM", callback_data=f"snoozetomorrow:{task_id}"),
    ]])


def build_grouped_message(tasks_map: dict):
    """tasks_map: {task_id: description}. Return (teks, keyboard)."""
    baris = [f"#{tid} — {desc}" for tid, desc in tasks_map.items()]
    pesan = f"⏰ {len(tasks_map)} tugas jatuh tempo:\n\n" + "\n".join(baris)

    rows = []
    for tid, desc in tasks_map.items():
        rows.append([
            InlineKeyboardButton(f"✅ #{tid}", callback_data=f"done:{tid}"),
            InlineKeyboardButton(f"⏰ #{tid} +1j", callback_data=f"snooze1h:{tid}"),
            InlineKeyboardButton(f"📅 #{tid} besok", callback_data=f"snoozetomorrow:{tid}"),
        ])
    return pesan, InlineKeyboardMarkup(rows)