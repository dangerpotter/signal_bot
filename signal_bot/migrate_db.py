"""Database migration script to add new columns."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'signal_bot.db')


def migrate():
    """Add missing columns to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add typing_enabled if missing
    if 'typing_enabled' not in existing_columns:
        print("Adding typing_enabled column...")
        cursor.execute("ALTER TABLE bots ADD COLUMN typing_enabled BOOLEAN DEFAULT 1")

    # Add read_receipts_enabled if missing
    if 'read_receipts_enabled' not in existing_columns:
        print("Adding read_receipts_enabled column...")
        cursor.execute("ALTER TABLE bots ADD COLUMN read_receipts_enabled BOOLEAN DEFAULT 0")

    conn.commit()
    conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    migrate()
