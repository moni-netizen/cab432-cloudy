from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_DATA: dict[str, list[dict[str, Any]]] = {
    "users": [],
    "posts": [],
    "comments": [],
    "likes": [],
    "follows": [],
    "moments": [],
}

DB_PATH = Path(__file__).resolve().parents[2] / "db.json"

_database: dict[str, Any] | None = None


def initialise_database() -> dict[str, Any]:
    """Load the JSON database into memory and create missing defaults."""
    global _database

    if _database is not None:
        return _database

    if DB_PATH.exists():
        with DB_PATH.open("r", encoding="utf-8") as file_handle:
            loaded = json.load(file_handle)
    else:
        loaded = {}

    database = dict(DEFAULT_DATA)
    database.update(loaded or {})

    for key, value in DEFAULT_DATA.items():
        if key not in database or database[key] is None:
            database[key] = list(value)

    _database = database
    save_database()
    return _database


def get_database() -> dict[str, Any]:
    """Return database data for the requested context."""
    if _database is None:
        raise RuntimeError("Database not initialised. Call initialise_database() first.")
    return _database


def save_database() -> None:
    """Persist the current in-memory database state to disk."""
    if _database is None:
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DB_PATH.open("w", encoding="utf-8") as file_handle:
        json.dump(_database, file_handle, indent=2)
        file_handle.write("\n")
