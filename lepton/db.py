import sqlite3

from .config import DB_PATH

DB = sqlite3.connect(DB_PATH)
DB.cursor().execute(
    "CREATE TABLE IF NOT EXISTS photon (name TEXT, model TEXT, path TEXT)"
)
DB.commit()
