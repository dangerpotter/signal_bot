#!/usr/bin/env python3
"""
Migration script to add Google Sheets integration columns to bots table
and create sheets_registry table.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def migrate():
    """Add Google Sheets columns and sheets_registry table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in bots table
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    # Add Google Sheets columns to bots table
    google_columns = [
        ('google_sheets_enabled', 'BOOLEAN DEFAULT 0'),
        ('google_client_id', 'VARCHAR(200)'),
        ('google_client_secret', 'TEXT'),
        ('google_refresh_token', 'TEXT'),
        ('google_token_expiry', 'DATETIME'),
        ('google_connected', 'BOOLEAN DEFAULT 0'),
    ]

    for col_name, col_type in google_columns:
        if col_name not in columns:
            print(f"Adding '{col_name}' column to bots table...")
            cursor.execute(f"ALTER TABLE bots ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column '{col_name}' already exists.")

    # Check if sheets_registry table exists
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='sheets_registry'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        print("Creating 'sheets_registry' table...")
        cursor.execute("""
            CREATE TABLE sheets_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id VARCHAR(50) NOT NULL,
                group_id VARCHAR(100) NOT NULL,
                spreadsheet_id VARCHAR(100) NOT NULL UNIQUE,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                FOREIGN KEY (bot_id) REFERENCES bots(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # Create index for efficient lookups
        cursor.execute("""
            CREATE INDEX idx_sheets_bot_group
            ON sheets_registry(bot_id, group_id)
        """)
        print("Created 'sheets_registry' table with index.")
    else:
        print("Table 'sheets_registry' already exists.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Google Sheets integration columns added to bots table.")
    print("sheets_registry table created for tracking spreadsheets.")


if __name__ == '__main__':
    migrate()
