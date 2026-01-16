"""
Migration script to add Gemini API support columns to bots table.
Run this once: python migrate_gemini_support.py

Adds:
- api_provider: 'openrouter' (default) or 'gemini' for direct Gemini API
- gemini_api_key: Optional per-bot Gemini API key (overrides GEMINI_API_KEY env var)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signal_bot.db")


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("It will be created with the new schema on first run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    changes_made = False

    # Add api_provider column
    if "api_provider" not in columns:
        print("Adding 'api_provider' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN api_provider VARCHAR(20) DEFAULT 'openrouter'")
        changes_made = True
    else:
        print("Column 'api_provider' already exists.")

    # Add gemini_api_key column
    if "gemini_api_key" not in columns:
        print("Adding 'gemini_api_key' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN gemini_api_key TEXT")
        changes_made = True
    else:
        print("Column 'gemini_api_key' already exists.")

    if changes_made:
        conn.commit()
        print("Migration complete!")
    else:
        print("Nothing to do.")

    conn.close()


if __name__ == "__main__":
    migrate()
