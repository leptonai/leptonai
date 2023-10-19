"""
Database for storing photon information. This is a system component - do not directly
import this module or operate on the database with direct SQL queries, unless you know
exactly what you are doing. Use the Lepton CLI instead. Arbitrary changes to the database
may cause the metadata to be corrupted.
"""

import sqlite3

from ..config import DB_PATH
from ..util import create_cached_dir_if_needed

_lepton_internal_db = None


def DB() -> sqlite3.Connection:
    """
    Returns a sqlite3 connection to the database.
    """
    global _lepton_internal_db
    if not _lepton_internal_db:
        create_cached_dir_if_needed()
        _lepton_internal_db = sqlite3.connect(DB_PATH)
        _lepton_internal_db.cursor().execute(
            "CREATE TABLE IF NOT EXISTS photon (id TEXT, name TEXT, model TEXT, path"
            " TEXT, creation_time INT)"
        )
        _lepton_internal_db.commit()
    return _lepton_internal_db
