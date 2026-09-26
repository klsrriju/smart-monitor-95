import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parent
db_path=ROOT/"data"/"monitoring.db"
schema=ROOT/"schema_sqlite.sql"
conn=sqlite3.connect(db_path)
conn.executescript(schema.read_text())
conn.commit()
conn.close()
print("Database initialized:", db_path)
