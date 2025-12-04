#!/usr/bin/env python3
"""
Migration script to add idle news settings columns to the bots table.

Run this once to update an existing database:
    python migrate_idle_news.py
"""

import sqlite3
import os

DB_PATH = "signal_bot.db"


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. No migration needed - columns will be created on first run.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check which columns already exist
    cursor.execute("PRAGMA table_info(bots)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    new_columns = [
        ("idle_news_enabled", "BOOLEAN DEFAULT 0"),
        ("idle_threshold_minutes", "INTEGER DEFAULT 15"),
        ("idle_check_interval_minutes", "INTEGER DEFAULT 5"),
        ("idle_trigger_chance_percent", "INTEGER DEFAULT 10"),
    ]

    added = 0
    for col_name, col_def in new_columns:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE bots ADD COLUMN {col_name} {col_def}")
                print(f"Added column: {col_name}")
                added += 1
            except sqlite3.OperationalError as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column already exists: {col_name}")

    conn.commit()
    conn.close()

    if added > 0:
        print(f"\nMigration complete! Added {added} column(s).")
    else:
        print("\nNo migration needed - all columns already exist.")


if __name__ == "__main__":
    migrate()
