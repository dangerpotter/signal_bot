#!/usr/bin/env python3
"""
Migration script to add D&D Game Master support.
Adds dnd_enabled column to bots table and creates dnd_campaigns table.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def migrate():
    """Add D&D columns and dnd_campaigns table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    # Add D&D enabled column to bots table
    if 'dnd_enabled' not in columns:
        print("Adding 'dnd_enabled' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN dnd_enabled BOOLEAN DEFAULT 0")
    else:
        print("Column 'dnd_enabled' already exists.")

    # Check if dnd_campaigns table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='dnd_campaigns'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        print("Creating 'dnd_campaigns' table...")
        cursor.execute("""
            CREATE TABLE dnd_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id VARCHAR(50) NOT NULL,
                group_id VARCHAR(100) NOT NULL,
                spreadsheet_id VARCHAR(100) NOT NULL UNIQUE,
                campaign_name VARCHAR(255) NOT NULL,
                setting VARCHAR(255),
                tone VARCHAR(50),
                starting_level INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_played DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # Create indexes for efficient lookups
        cursor.execute("""
            CREATE INDEX idx_dnd_bot_group
            ON dnd_campaigns(bot_id, group_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_dnd_campaign_name
            ON dnd_campaigns(campaign_name)
        """)
        print("Created 'dnd_campaigns' table with indexes.")
    else:
        print("Table 'dnd_campaigns' already exists.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("D&D Game Master support has been added.")
    print("- dnd_enabled column added to bots table")
    print("- dnd_campaigns table created for tracking campaigns")


if __name__ == '__main__':
    migrate()
