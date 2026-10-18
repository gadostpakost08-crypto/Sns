# language: Python 3.11, file: db.py
import sqlite3
from config import DB_PATH

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            session TEXT NOT NULL,
            phone   TEXT NOT NULL,
            active  INTEGER DEFAULT 1
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            target  TEXT NOT NULL,
            status  TEXT DEFAULT 'pending',
            total   INTEGER DEFAULT 0,
            done    INTEGER DEFAULT 0
        )
    """)
    con.commit()
    con.close()

def get_active_accounts():
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT id, session, phone FROM accounts WHERE active=1"
    ).fetchall()
    con.close()
    return rows

def add_account(session_str: str, phone: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO accounts (session, phone) VALUES (?,?)",
        (session_str, phone)
    )
    con.commit()
    con.close()

def deactivate_account(account_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("UPDATE accounts SET active=0 WHERE id=?", (account_id,))
    con.commit()
    con.close()

def get_account_count():
    con = sqlite3.connect(DB_PATH)
    count = con.execute(
        "SELECT COUNT(*) FROM accounts WHERE active=1"
    ).fetchone()[0]
    con.close()
    return count
