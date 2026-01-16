"""
Migration script to add Gemini Interactions API columns to bots table.
Run this once: python migrate_interactions_api.py

Adds:
- thinking_level: 'minimal', 'low', 'medium', 'high' (default: 'high')
- enable_google_search: Enable built-in Google Search grounding
- enable_code_execution: Enable Gemini to run Python code
- enable_url_context: Enable Gemini to fetch and summarize URLs
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

    # Add thinking_level column
    if "thinking_level" not in columns:
        print("Adding 'thinking_level' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN thinking_level TEXT DEFAULT 'high'")
        changes_made = True
    else:
        print("Column 'thinking_level' already exists.")

    # Add enable_google_search column
    if "enable_google_search" not in columns:
        print("Adding 'enable_google_search' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN enable_google_search BOOLEAN DEFAULT 0")
        changes_made = True
    else:
        print("Column 'enable_google_search' already exists.")

    # Add enable_code_execution column
    if "enable_code_execution" not in columns:
        print("Adding 'enable_code_execution' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN enable_code_execution BOOLEAN DEFAULT 0")
        changes_made = True
    else:
        print("Column 'enable_code_execution' already exists.")

    # Add enable_url_context column
    if "enable_url_context" not in columns:
        print("Adding 'enable_url_context' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN enable_url_context BOOLEAN DEFAULT 0")
        changes_made = True
    else:
        print("Column 'enable_url_context' already exists.")

    if changes_made:
        conn.commit()
        print("Migration complete!")
    else:
        print("Nothing to do.")

    conn.close()


if __name__ == "__main__":
    migrate()
