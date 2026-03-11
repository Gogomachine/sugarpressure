import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "health.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('pressure', 'glucose')),
            systolic INTEGER,
            diastolic INTEGER,
            glucose REAL,
            recorded_at DATETIME NOT NULL DEFAULT (datetime('now')),
            created_at DATETIME NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def add_pressure(user_id: int, systolic: int, diastolic: int, recorded_at: datetime | None = None):
    conn = get_connection()
    ts = recorded_at or datetime.now()
    conn.execute(
        "INSERT INTO measurements (user_id, type, systolic, diastolic, recorded_at) VALUES (?, 'pressure', ?, ?, ?)",
        (user_id, systolic, diastolic, ts),
    )
    conn.commit()
    conn.close()


def add_glucose(user_id: int, glucose: float, recorded_at: datetime | None = None):
    conn = get_connection()
    ts = recorded_at or datetime.now()
    conn.execute(
        "INSERT INTO measurements (user_id, type, glucose, recorded_at) VALUES (?, 'glucose', ?, ?)",
        (user_id, glucose, ts),
    )
    conn.commit()
    conn.close()


def get_pressure_history(user_id: int, days: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT systolic, diastolic, recorded_at FROM measurements
           WHERE user_id = ? AND type = 'pressure'
             AND recorded_at >= datetime('now', ?)
           ORDER BY recorded_at""",
        (user_id, f"-{days} days"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_glucose_history(user_id: int, days: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT glucose, recorded_at FROM measurements
           WHERE user_id = ? AND type = 'glucose'
             AND recorded_at >= datetime('now', ?)
           ORDER BY recorded_at""",
        (user_id, f"-{days} days"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_history(user_id: int, days: int = 30) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        """SELECT type, systolic, diastolic, glucose, recorded_at FROM measurements
           WHERE user_id = ? AND recorded_at >= datetime('now', ?)
           ORDER BY recorded_at""",
        (user_id, f"-{days} days"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
