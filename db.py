import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from timeutils import now_wib

import os
DB_PATH = os.path.join(os.environ.get("DB_DIR", "."), "tasks.db")


@contextmanager
def get_conn():
    """
    Context manager yang MENJAMIN koneksi selalu ditutup,
    baik saat sukses maupun saat ada error di tengah jalan.
    Ini yang mencegah bug 'database is locked'.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # supaya baris hasil SELECT bisa diakses kayak dict
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            due_at TEXT,
            priority TEXT DEFAULT 'normal',
            category TEXT DEFAULT 'Umum',
            status TEXT DEFAULT 'pending',
            reminded INTEGER DEFAULT 0,
            pending_date TEXT,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_task(chat_id, description, due_at, priority, category="Umum", pending_date=None) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            "INSERT INTO tasks (chat_id, description, due_at, priority, category, pending_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, description, due_at, priority, category, pending_date, now_wib().isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def list_pending_tasks(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND status = 'pending' "
            "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC",
            (chat_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_done(task_id: int, chat_id: int) -> bool:
    with get_conn() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = 'done' WHERE id = ? AND chat_id = ?",
            (task_id, chat_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_task(task_id: int, chat_id: int) -> bool:
    with get_conn() as conn:
        cursor = conn.execute(
            "DELETE FROM tasks WHERE id = ? AND chat_id = ?", (task_id, chat_id)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_due_unreminded_tasks(now_iso: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE status = 'pending' AND reminded = 0 "
            "AND due_at IS NOT NULL AND due_at <= ?",
            (now_iso,)
        ).fetchall()
        return [dict(r) for r in rows]


def mark_reminded(task_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET reminded = 1 WHERE id = ?", (task_id,))
        conn.commit()

def update_task(task_id, chat_id, description=None, due_at=None, priority=None, category=None) -> bool:
    with get_conn() as conn:
        fields, values = [], []
        if description is not None:
            fields.append("description = ?"); values.append(description)
        if due_at is not None:
            fields.append("due_at = ?"); values.append(due_at)
            fields.append("reminded = 0")
        if priority is not None:
            fields.append("priority = ?"); values.append(priority)
        if category is not None:
            fields.append("category = ?"); values.append(category)
        if not fields:
            return False
        values.extend([task_id, chat_id])
        query = f"UPDATE tasks SET {', '.join(fields)} WHERE id = ? AND chat_id = ?"
        cursor = conn.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def list_today_tasks(chat_id: int):
    """Tugas hari ini + semua yang overdue (belum selesai)."""
    besok_str = (now_wib() + timedelta(days=1)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND status = 'pending' "
            "AND due_at IS NOT NULL AND due_at < ? ORDER BY due_at ASC",
            (chat_id, besok_str)  # semua yg due_at-nya sebelum besok jam 00:00 = hari ini + overdue
        ).fetchall()
        return [dict(r) for r in rows]

def get_categories(chat_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM tasks WHERE chat_id = ? ORDER BY category",
            (chat_id,)
        ).fetchall()
        return [r["category"] for r in rows]

def list_overdue_tasks(chat_id: int):
    now_iso = now_wib().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND status = 'pending' "
            "AND due_at IS NOT NULL AND due_at < ? ORDER BY due_at ASC",
            (chat_id, now_iso)
        ).fetchall()
        return [dict(r) for r in rows]

def get_task(task_id: int, chat_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ? AND chat_id = ?", (task_id, chat_id)
        ).fetchone()
        return dict(row) if row else None

def list_pending_tasks_by_category(chat_id: int, category: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND status = 'pending' AND category = ? "
            "ORDER BY CASE WHEN due_at IS NULL THEN 1 ELSE 0 END, due_at ASC",
            (chat_id, category)
        ).fetchall()
        return [dict(r) for r in rows]

def clear_pending_date(task_id: int, chat_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE tasks SET pending_date = NULL WHERE id = ? AND chat_id = ?", (task_id, chat_id))
        conn.commit()