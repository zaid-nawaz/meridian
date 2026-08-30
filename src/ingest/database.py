from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "meridian.sqlite3"

SCHEMA_PATH = DB_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """
    Return a connection to the Meridian SQLite database.
    """

    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database() -> None:
    """
    Create all Meridian database tables.
    """

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with get_connection() as connection:
        connection.executescript(schema)

        connection.commit()


def clear_database() -> None:
    """
    Delete the local database.

    Useful during development and testing.
    """

    if DB_PATH.exists():
        DB_PATH.unlink()