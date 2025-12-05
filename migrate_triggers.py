#!/usr/bin/env python3
"""
Migration script to add scheduled triggers support.
- Adds triggers_enabled and max_triggers columns to bots table
- Creates scheduled_triggers table

Run with: python migrate_triggers.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'signal_bot.db')


def migrate():
    """Add trigger columns and scheduled_triggers table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    # Add triggers_enabled column to bots table
    if 'triggers_enabled' not in columns:
        print("Adding 'triggers_enabled' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN triggers_enabled BOOLEAN DEFAULT 1")
    else:
        print("Column 'triggers_enabled' already exists.")

    # Add max_triggers column to bots table
    if 'max_triggers' not in columns:
        print("Adding 'max_triggers' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN max_triggers INTEGER DEFAULT 10")
    else:
        print("Column 'max_triggers' already exists.")

    # Check if scheduled_triggers table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='scheduled_triggers'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        print("Creating 'scheduled_triggers' table...")
        cursor.execute("""
            CREATE TABLE scheduled_triggers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id VARCHAR(50) NOT NULL,
                group_id VARCHAR(100) NOT NULL,

                -- Trigger type and content
                trigger_type VARCHAR(20) NOT NULL,
                name VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,

                -- Timing configuration
                trigger_mode VARCHAR(20) NOT NULL,
                scheduled_time DATETIME,

                -- Recurring configuration
                recurrence_pattern VARCHAR(20),
                recurrence_interval INTEGER DEFAULT 1,
                recurrence_day_of_week INTEGER,
                recurrence_day_of_month INTEGER,
                recurrence_time TIME,
                end_date DATETIME,
                timezone VARCHAR(100) DEFAULT 'UTC',

                -- State tracking
                enabled BOOLEAN DEFAULT 1,
                next_fire_time DATETIME,
                last_fired_at DATETIME,
                fire_count INTEGER DEFAULT 0,

                -- Metadata
                created_by VARCHAR(100),
                created_via VARCHAR(20) DEFAULT 'admin',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # Create indexes for efficient lookups
        cursor.execute("""
            CREATE INDEX idx_triggers_bot_group
            ON scheduled_triggers(bot_id, group_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_triggers_next_fire
            ON scheduled_triggers(next_fire_time, enabled)
        """)
        print("Created 'scheduled_triggers' table with indexes.")
    else:
        print("Table 'scheduled_triggers' already exists.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Scheduled triggers feature ready.")
    print("\nYou can now:")
    print("  - Enable triggers per-bot in the admin UI")
    print("  - Create triggers via chat or admin UI")
    print("  - Manage triggers from the new 'Triggers' tab")


if __name__ == '__main__':
    migrate()
