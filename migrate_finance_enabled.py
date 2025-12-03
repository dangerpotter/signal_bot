#!/usr/bin/env python3
"""
Migration script to add finance_enabled column to bots table.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'signal_bot.db')

def migrate():
    """Add finance_enabled column to bots table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'finance_enabled' in columns:
        print("Column 'finance_enabled' already exists. No migration needed.")
        conn.close()
        return

    # Add the column
    print("Adding 'finance_enabled' column to bots table...")
    cursor.execute("""
        ALTER TABLE bots
        ADD COLUMN finance_enabled BOOLEAN DEFAULT 0
    """)

    conn.commit()
    print("Migration complete! finance_enabled column added (default: disabled)")

    conn.close()

if __name__ == '__main__':
    migrate()
