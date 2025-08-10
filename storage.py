# iseeyou/storage.py
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    return conn

def set_key(key, value):
    conn = get_conn()
    conn.execute(
        "REPLACE INTO kv (key, value) VALUES (?, ?)",
        (key, json.dumps(value))
    )
    conn.commit()
    conn.close()

def get_key(key, default=None):
    conn = get_conn()
    cur = conn.execute("SELECT value FROM kv WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return json.loads(row[0]) if row else default

def delete_key(key):
    conn = get_conn()
    conn.execute("DELETE FROM kv WHERE key=?", (key,))
    conn.commit()
    conn.close()
