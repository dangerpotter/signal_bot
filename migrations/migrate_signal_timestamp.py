#!/usr/bin/env python3
"""
Migration script to add signal_timestamp column to message_logs table for deduplication.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')

def migrate():
    """Add signal_timestamp column to message_logs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(message_logs)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'signal_timestamp' in columns:
        print("Column 'signal_timestamp' already exists. No migration needed.")
        conn.close()
        return

    # Add the column
    print("Adding 'signal_timestamp' column to message_logs table...")
    cursor.execute("""
        ALTER TABLE message_logs
        ADD COLUMN signal_timestamp INTEGER
    """)

    conn.commit()
    print("Migration complete! signal_timestamp column added for message deduplication.")

    conn.close()

if __name__ == '__main__':
    migrate()
