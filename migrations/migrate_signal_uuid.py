#!/usr/bin/env python3
"""
Migration: Add signal_uuid column to bots table.

This column stores the bot's Signal UUID for proper mention matching.
Signal mentions can include UUID only (no phone number), so we need
to match mentions by UUID as well as phone number.
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "signal_bot.db")


def migrate():
    """Add signal_uuid column to bots table if it doesn't exist."""
    print(f"Connecting to database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("Database does not exist yet - will be created on first run")
        return True

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(bots)")
        columns = [col[1] for col in cursor.fetchall()]

        if "signal_uuid" in columns:
            print("signal_uuid column already exists - skipping")
            return True

        # Add the column
        print("Adding signal_uuid column to bots table...")
        cursor.execute("""
            ALTER TABLE bots
            ADD COLUMN signal_uuid VARCHAR(64)
        """)

        conn.commit()
        print("Migration successful: signal_uuid column added")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
