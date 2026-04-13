"""
JARVIS Contact Manager
Name → email lookup with fuzzy matching.
Stored in the same SQLite memory database as conversations and facts.
"""

import os
import sqlite3

from loguru import logger

MEMORY_DB = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")


def _get_db() -> sqlite3.Connection:
    """Get database connection and ensure contacts table exists."""
    db = sqlite3.connect(MEMORY_DB)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE,
            email TEXT NOT NULL,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(name COLLATE NOCASE)
        )
    """)
    db.commit()
    return db


def add_contact(name: str, email: str) -> str:
    """Add or update a contact. If name exists, updates the email."""
    db = _get_db()
    try:
        # Use INSERT OR REPLACE to handle updates
        db.execute(
            "INSERT OR REPLACE INTO contacts (name, email) VALUES (?, ?)",
            (name.strip(), email.strip().lower()),
        )
        db.commit()
        logger.info(f"📇 Contact saved: {name} → {email}")
        return f"Saved contact: {name} ({email})"
    except Exception as e:
        logger.error(f"Contact save failed: {e}")
        return f"Failed to save contact: {e}"
    finally:
        db.close()


def find_contact(name: str) -> dict | None:
    """Find a contact by name (case-insensitive, supports partial match).
    Returns {'name': ..., 'email': ...} or None."""
    db = _get_db()

    # 1) Exact match
    row = db.execute(
        "SELECT name, email FROM contacts WHERE name = ? COLLATE NOCASE",
        (name.strip(),),
    ).fetchone()

    if row:
        db.close()
        return {"name": row["name"], "email": row["email"]}

    # 2) Partial match — name contains the search term
    row = db.execute(
        "SELECT name, email FROM contacts WHERE name LIKE ? COLLATE NOCASE ORDER BY length(name) ASC",
        (f"%{name.strip()}%",),
    ).fetchone()

    if row:
        db.close()
        return {"name": row["name"], "email": row["email"]}

    db.close()
    return None


def list_contacts() -> list[dict]:
    """List all saved contacts."""
    db = _get_db()
    rows = db.execute("SELECT name, email FROM contacts ORDER BY name").fetchall()
    db.close()
    return [{"name": r["name"], "email": r["email"]} for r in rows]


def remove_contact(name: str) -> str:
    """Remove a contact by name."""
    db = _get_db()
    cursor = db.execute(
        "DELETE FROM contacts WHERE name = ? COLLATE NOCASE",
        (name.strip(),),
    )
    db.commit()
    db.close()

    if cursor.rowcount > 0:
        logger.info(f"📇 Contact removed: {name}")
        return f"Removed contact: {name}"
    return f"Contact not found: {name}"
