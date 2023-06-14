import sqlite3

from .config import DB_PATH

DB = sqlite3.connect(DB_PATH)
DB.cursor().execute(
    "CREATE TABLE IF NOT EXISTS photon (id TEXT, name TEXT, model TEXT, path TEXT,"
    " creation_time INT)"
)
DB.commit()
