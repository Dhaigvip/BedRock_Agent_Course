"""
Long-term memory — persists curated user facts across sessions.

Short-term memory (SqliteSaver checkpointer) stores the full raw message
history for a single conversation thread. It is wiped when a new session
starts with a fresh thread_id.

Long-term memory stores *distilled* facts about a user that are worth
keeping forever: preferences, budget, home city, past destinations.
These facts are:
  1. Injected into the system prompt at the start of every session
  2. Extracted from the conversation at session end by a quick LLM call

Storage: a single SQLite table user_facts(user_id TEXT PRIMARY KEY, facts TEXT)
"""

import sqlite3
from pathlib import Path
from bedrock import call_bedrock, MODELS
from prompts import build_memory_prompt

DB_PATH = Path(__file__).parent / "memory.db"


# ── Schema ────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_facts (
            user_id TEXT PRIMARY KEY,
            facts   TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.commit()
    return conn


# ── Public API ────────────────────────────────────────────────────────────────

def load_facts(user_id: str) -> str:
    """
    Return the stored facts string for a user, or '' if none yet.
    Called at session start to inject facts into the system prompt.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT facts FROM user_facts WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row[0] if row else ""


def save_facts(user_id: str, messages: list[dict]) -> str:
    """
    Ask Nova Micro to extract useful facts from the conversation,
    merge with existing facts, and persist to SQLite.

    Called at session end (when the user types 'quit').
    Returns the updated facts string.
    """
    existing = load_facts(user_id)

    # Build a compact conversation summary for the LLM to read
    turns = []
    for m in messages:
        role = m.get("role", "")
        if role not in {"user", "assistant"}:
            continue
        text = " ".join(
            b["text"] for b in m.get("content", []) if "text" in b
        )
        if text:
            turns.append(f"{role.upper()}: {text[:300]}")

    conversation_text = "\n".join(turns[-20:])  # last 20 turns is enough

    response = call_bedrock(
        messages=[build_memory_prompt(existing, conversation_text)],
        model_id=MODELS["simple"],  # Nova Micro is fine for this extraction task
    )
    updated_facts = response["content"][0]["text"].strip()

    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO user_facts(user_id, facts) VALUES(?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET facts=excluded.facts",
            (user_id, updated_facts),
        )
        conn.commit()

    print(f"[memory] facts saved for user '{user_id}'")
    return updated_facts
