"""
JARVIS Neural Memory System
Persistent memory across sessions: conversation history, user facts, preferences.
Uses SQLite for storage and Gemini for summarization.
"""

import datetime
import json
import os
import sqlite3

from loguru import logger

MEMORY_DB = os.path.join(os.path.dirname(__file__), "jarvis_memory.db")


def _get_db() -> sqlite3.Connection:
    """Get database connection and ensure tables exist."""
    db = sqlite3.connect(MEMORY_DB)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            summary TEXT,
            turn_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            created_at TEXT NOT NULL,
            importance INTEGER DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)
    return db


def start_conversation() -> int:
    """Start a new conversation session. Returns conversation ID."""
    db = _get_db()
    now = datetime.datetime.now().isoformat()
    cursor = db.execute("INSERT INTO conversations (started_at) VALUES (?)", (now,))
    conv_id = cursor.lastrowid
    db.commit()
    db.close()
    logger.info(f"🧠 Memory: Started conversation #{conv_id}")
    return conv_id


def save_message(conv_id: int, role: str, content: str):
    """Save a message to conversation history."""
    if not content or not content.strip():
        return
    db = _get_db()
    now = datetime.datetime.now().isoformat()
    db.execute(
        "INSERT INTO messages (conversation_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (conv_id, role, content[:5000], now),
    )
    db.execute(
        "UPDATE conversations SET turn_count = turn_count + 1 WHERE id = ?",
        (conv_id,),
    )
    db.commit()
    db.close()


def end_conversation(conv_id: int, summary: str = None):
    """End a conversation and optionally save a summary."""
    db = _get_db()
    now = datetime.datetime.now().isoformat()
    db.execute(
        "UPDATE conversations SET ended_at = ?, summary = ? WHERE id = ?",
        (now, summary, conv_id),
    )
    db.commit()
    db.close()
    logger.info(f"🧠 Memory: Ended conversation #{conv_id}")


def save_fact(category: str, content: str, source: str = "conversation", importance: int = 5):
    """Save an important fact about the user or world."""
    db = _get_db()
    now = datetime.datetime.now().isoformat()
    # Avoid exact duplicates
    existing = db.execute(
        "SELECT id FROM facts WHERE content = ? AND category = ?",
        (content, category),
    ).fetchone()
    if not existing:
        db.execute(
            "INSERT INTO facts (category, content, source, created_at, importance) VALUES (?, ?, ?, ?, ?)",
            (category, content, source, now, importance),
        )
        db.commit()
        logger.info(f"🧠 Memory: Saved fact [{category}]: {content[:80]}")
    db.close()


def save_preference(key: str, value: str):
    """Save a user preference."""
    db = _get_db()
    now = datetime.datetime.now().isoformat()
    db.execute(
        "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
        (key, value, now),
    )
    db.commit()
    db.close()
    logger.info(f"🧠 Memory: Saved preference {key}={value}")


def get_recent_conversations(limit: int = 5) -> list[dict]:
    """Get recent conversation summaries."""
    db = _get_db()
    rows = db.execute(
        "SELECT id, started_at, summary, turn_count FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_facts(category: str = None, limit: int = 20) -> list[dict]:
    """Get stored facts, optionally filtered by category."""
    db = _get_db()
    if category:
        rows = db.execute(
            "SELECT category, content, importance FROM facts WHERE category = ? ORDER BY importance DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT category, content, importance FROM facts ORDER BY importance DESC LIMIT ?",
            (limit,),
        ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def get_preferences() -> dict:
    """Get all user preferences as a dict."""
    db = _get_db()
    rows = db.execute("SELECT key, value FROM preferences").fetchall()
    db.close()
    return {r["key"]: r["value"] for r in rows}


def get_conversation_messages(conv_id: int, limit: int = 50) -> list[dict]:
    """Get messages from a specific conversation."""
    db = _get_db()
    rows = db.execute(
        "SELECT role, content, timestamp FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conv_id, limit),
    ).fetchall()
    db.close()
    return [dict(r) for r in reversed(rows)]


def build_memory_context() -> str:
    """Build a memory context string to inject into the system prompt."""
    parts = []

    # User facts
    facts = get_facts(limit=15)
    if facts:
        user_facts = [f for f in facts if f["category"] == "user"]
        other_facts = [f for f in facts if f["category"] != "user"]
        if user_facts:
            parts.append("WHAT I KNOW ABOUT YOU:\n" + "\n".join(f"- {f['content']}" for f in user_facts))
        if other_facts:
            parts.append("THINGS I REMEMBER:\n" + "\n".join(f"- [{f['category']}] {f['content']}" for f in other_facts))

    # Preferences
    prefs = get_preferences()
    if prefs:
        parts.append("YOUR PREFERENCES:\n" + "\n".join(f"- {k}: {v}" for k, v in prefs.items()))

    # Recent conversation summaries
    convos = get_recent_conversations(limit=3)
    summaries = [c for c in convos if c.get("summary")]
    if summaries:
        parts.append("RECENT CONVERSATIONS:\n" + "\n".join(
            f"- {c['started_at'][:10]}: {c['summary']}" for c in summaries
        ))

    if not parts:
        return ""

    return "\n\n".join(parts)


async def summarize_conversation(conv_id: int) -> str:
    """Use Gemini to summarize a conversation and extract facts."""
    messages = get_conversation_messages(conv_id, limit=30)
    if not messages or len(messages) < 2:
        return ""

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

    api_key = os.getenv("GOOGLE_CREDENTIALS", "")
    if not api_key:
        # Fallback: just save first/last message as summary
        summary = f"Conversation with {len(messages)} turns"
        end_conversation(conv_id, summary)
        return summary

    from google import genai

    client = genai.Client(api_key=api_key)

    prompt = f"""Analyze this conversation and return a JSON object:
{{
  "summary": "1-2 sentence summary of what was discussed",
  "user_facts": ["list of facts learned about the user (name, preferences, habits, etc.)"],
  "important_info": ["list of other important information worth remembering"]
}}

Conversation:
{transcript[:3000]}

Return ONLY the JSON object, no markdown."""

    try:
        import asyncio
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
        )

        text = response.text.strip()
        if text.startswith("```"):
            import re
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        data = json.loads(text)
        summary = data.get("summary", "")

        # Save the summary
        end_conversation(conv_id, summary)

        # Save extracted facts
        for fact in data.get("user_facts", []):
            if fact.strip():
                save_fact("user", fact.strip(), source=f"conversation #{conv_id}", importance=8)

        for info in data.get("important_info", []):
            if info.strip():
                save_fact("knowledge", info.strip(), source=f"conversation #{conv_id}", importance=5)

        logger.info(f"🧠 Memory: Summarized conversation #{conv_id}: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Memory summarization failed: {e}")
        fallback = f"Conversation with {len(messages)} turns"
        end_conversation(conv_id, fallback)
        return fallback


def get_memory_stats() -> dict:
    """Get memory statistics."""
    db = _get_db()
    convos = db.execute("SELECT COUNT(*) as c FROM conversations").fetchone()["c"]
    msgs = db.execute("SELECT COUNT(*) as c FROM messages").fetchone()["c"]
    facts_count = db.execute("SELECT COUNT(*) as c FROM facts").fetchone()["c"]
    prefs_count = db.execute("SELECT COUNT(*) as c FROM preferences").fetchone()["c"]
    db.close()
    return {
        "conversations": convos,
        "messages": msgs,
        "facts": facts_count,
        "preferences": prefs_count,
    }
