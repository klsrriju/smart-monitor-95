"""
database.py
------------
This file is responsible for ALL direct communication with the SQLite database.
No other file should talk to sqlite directly - they should call functions from here.

Why SQLite?
- It's just a single file on disk (attendance.db) - no server to install.
- Perfect for a first, simple, local version of the project.
- We can move to PostgreSQL/Supabase later without touching any other file,
  as long as we keep these same function names.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "attendance.db"


def get_connection():
    """
    Opens a connection to the SQLite database file.
    `row_factory = sqlite3.Row` lets us access columns by name (like a dictionary),
    e.g. row["employee_id"], instead of just by position, e.g. row[0].
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Creates all the tables we need, if they don't already exist.
    Safe to call every time the app starts - it won't wipe existing data.
    """
    conn = get_connection()
    cur = conn.cursor()

    # 1. Employees table - the "master list" of who works here
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    # 2. Attendance table - ONE row per employee per day.
    #    The UNIQUE(employee_id, date) constraint is what physically
    #    guarantees the database can never hold two rows for the same
    #    person on the same day, no matter how many times we call insert.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            date TEXT NOT NULL,
            entry_time TEXT,
            exit_time TEXT,
            status TEXT NOT NULL,
            UNIQUE(employee_id, date),
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # 3. Events table - EVERY single detection is logged here,
    #    even 500 duplicate ones for the same person. This is our audit trail
    #    and is how the "attendance/events" endpoint gets its data.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            event_type TEXT NOT NULL,      -- 'ENTRY' or 'EXIT'
            event_time TEXT NOT NULL,      -- just the time part, e.g. 09:04:21
            full_timestamp TEXT NOT NULL,  -- full ISO timestamp
            confidence REAL,
            track_id INTEGER
        )
    """)

    conn.commit()
    conn.close()


def seed_employees(employees: dict):
    """
    Inserts the sample employees into the database.
    `INSERT OR IGNORE` means: if the employee already exists, just skip it
    instead of throwing an error. Safe to run every time the app starts.
    """
    conn = get_connection()
    cur = conn.cursor()
    for emp_id, name in employees.items():
        cur.execute(
            "INSERT OR IGNORE INTO employees (employee_id, name) VALUES (?, ?)",
            (emp_id, name),
        )
    conn.commit()
    conn.close()


def reset_db():
    """
    Wipes all data (used by demo/testing so each run starts clean).
    Not used by the real API.
    """
    if DB_PATH.exists():
        DB_PATH.unlink()
