"""
Database for storing photon information. This is a system component - do not directly
import this module or operate on the database with direct SQL queries, unless you know
exactly what you are doing. Use the Lepton CLI instead. Arbitrary changes to the database
may cause the Lepton SDK metadata to be corrupted.
"""
import sqlite3

from ..config import DB_PATH

DB = sqlite3.connect(DB_PATH)
DB.cursor().execute(
    "CREATE TABLE IF NOT EXISTS photon (id TEXT, name TEXT, model TEXT, path TEXT,"
    " creation_time INT)"
)
DB.commit()
