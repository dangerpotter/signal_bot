#!/usr/bin/env python3
"""
Migration script to add chat log support.
- Adds chat_log_enabled and chat_log_retention columns to bots table
- Creates chat_logs table for permanent searchable message history

Run with: python migrate_chat_logs.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def migrate():
    """Add chat log columns and chat_logs table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    # Add chat_log_enabled column to bots table
    if 'chat_log_enabled' not in columns:
        print("Adding 'chat_log_enabled' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN chat_log_enabled BOOLEAN DEFAULT 0")
    else:
        print("Column 'chat_log_enabled' already exists.")

    # Add chat_log_retention column to bots table
    if 'chat_log_retention' not in columns:
        print("Adding 'chat_log_retention' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN chat_log_retention VARCHAR(20) DEFAULT 'forever'")
    else:
        print("Column 'chat_log_retention' already exists.")

    # Check if chat_logs table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='chat_logs'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        print("Creating 'chat_logs' table...")
        cursor.execute("""
            CREATE TABLE chat_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id VARCHAR(100) NOT NULL,
                sender_id VARCHAR(100),
                sender_name VARCHAR(100) NOT NULL,
                content TEXT NOT NULL,
                is_bot BOOLEAN DEFAULT 0,
                bot_id VARCHAR(50),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                signal_timestamp BIGINT UNIQUE,

                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # Create indexes for efficient lookups
        cursor.execute("""
            CREATE INDEX idx_chat_logs_group_time
            ON chat_logs(group_id, timestamp)
        """)
        cursor.execute("""
            CREATE INDEX idx_chat_logs_sender
            ON chat_logs(group_id, sender_name)
        """)
        cursor.execute("""
            CREATE INDEX idx_chat_logs_timestamp
            ON chat_logs(timestamp)
        """)
        print("Created 'chat_logs' table with indexes.")
    else:
        print("Table 'chat_logs' already exists.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Chat log feature ready.")
    print("\nYou can now:")
    print("  - Enable chat log search per-bot in the admin UI")
    print("  - Configure retention period (6h to forever)")
    print("  - Search chat history via bot tools or admin UI")


if __name__ == '__main__':
    migrate()
