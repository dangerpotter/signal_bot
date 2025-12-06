"""
Migration script to add weather_enabled column to bots table.
Run this once: python migrate_weather_enabled.py
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

    # Check if column already exists
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    if "weather_enabled" in columns:
        print("Column 'weather_enabled' already exists. Nothing to do.")
        conn.close()
        return

    # Add the new column
    print("Adding 'weather_enabled' column to bots table...")
    cursor.execute("ALTER TABLE bots ADD COLUMN weather_enabled BOOLEAN DEFAULT 0")
    conn.commit()
    print("Migration complete!")

    conn.close()


if __name__ == "__main__":
    migrate()
