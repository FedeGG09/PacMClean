from __future__ import annotations
import sqlite3
import json
from datetime import datetime
from pathlib import Path

ART_DIR = Path("artifacts")
DB_PATH = ART_DIR / "history.db"

def init_storage():
    ART_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            source_name TEXT,
            score INTEGER,
            rows INTEGER,
            cols INTEGER,
            payload TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            ts TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cleanings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            ts TEXT NOT NULL,
            cleaned_path TEXT NOT NULL,
            actions TEXT,
            derived TEXT
        )
        """)
        conn.commit()

def save_run(report: dict, source_name: str, input_rows: int, input_cols: int):
    init_storage()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO runs (ts, source_name, score, rows, cols, payload) VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.utcnow().isoformat(),
                source_name,
                int(report["summary"]["quality_score"]),
                int(input_rows),
                int(input_cols),
                json.dumps(report, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()
        return cur.lastrowid

def save_alert(run_id: int, message: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO alerts (run_id, ts, message) VALUES (?, ?, ?)",
            (run_id, datetime.utcnow().isoformat(), message),
        )
        conn.commit()

def save_cleaning(run_id: int, cleaned_path: str, actions=None, derived=None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO cleanings (run_id, ts, cleaned_path, actions, derived) VALUES (?, ?, ?, ?, ?)",
            (
                run_id,
                datetime.utcnow().isoformat(),
                cleaned_path,
                json.dumps(actions or [], ensure_ascii=False, default=str),
                json.dumps(derived or [], ensure_ascii=False, default=str),
            ),
        )
        conn.commit()

def get_history(limit=50):
    init_storage()
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, ts, source_name, score, rows, cols FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cur.fetchall()
    return [
        {"id": r[0], "ts": r[1], "source_name": r[2], "score": r[3], "rows": r[4], "cols": r[5]}
        for r in rows
    ]
