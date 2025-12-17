#!/usr/bin/env python3
"""
Migration script to drop the memory_snippets table.

This table was used for the old long-term memory feature which has been
replaced by the searchable chat log system.

Run with: python drop_memory_snippets.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def migrate():
    """Drop the memory_snippets table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if memory_snippets table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='memory_snippets'
    """)
    table_exists = cursor.fetchone() is not None

    if table_exists:
        print("Dropping 'memory_snippets' table...")
        cursor.execute("DROP TABLE memory_snippets")
        print("Table 'memory_snippets' dropped successfully.")
    else:
        print("Table 'memory_snippets' does not exist (already removed).")

    conn.commit()
    conn.close()
    print("\nMigration complete!")


if __name__ == '__main__':
    migrate()
