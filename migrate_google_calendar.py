#!/usr/bin/env python3
"""
Migration script to add Google Calendar integration columns to bots table
and create calendar_registry table.

Run with: python migrate_google_calendar.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'signal_bot.db')


def migrate():
    """Add Google Calendar columns and calendar_registry table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    # Add Google Calendar enabled column to bots table
    if 'google_calendar_enabled' not in columns:
        print("Adding 'google_calendar_enabled' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN google_calendar_enabled BOOLEAN DEFAULT 0")
    else:
        print("Column 'google_calendar_enabled' already exists.")

    # Check if calendar_registry table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='calendar_registry'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        print("Creating 'calendar_registry' table...")
        cursor.execute("""
            CREATE TABLE calendar_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id VARCHAR(50) NOT NULL,
                group_id VARCHAR(100) NOT NULL,
                calendar_id VARCHAR(200) NOT NULL UNIQUE,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                timezone VARCHAR(100) DEFAULT 'UTC',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                share_link VARCHAR(500),
                is_public BOOLEAN DEFAULT 0,
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # Create index for efficient lookups
        cursor.execute("""
            CREATE INDEX idx_calendar_bot_group
            ON calendar_registry(bot_id, group_id)
        """)
        print("Created 'calendar_registry' table with index.")
    else:
        print("Table 'calendar_registry' already exists.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Google Calendar integration ready.")
    print("\nNOTE: Existing Google connections may need to be disconnected and")
    print("reconnected to grant Calendar API access (new OAuth scope).")


if __name__ == '__main__':
    migrate()
