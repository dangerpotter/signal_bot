#!/usr/bin/env python3
"""
Migration: Add dnd_template_spreadsheet_id column to bots table.

This allows each bot to have a configured Google Sheets template for D&D campaigns.
"""

import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(bots)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'dnd_template_spreadsheet_id' in columns:
            print("Column 'dnd_template_spreadsheet_id' already exists, skipping.")
            return True

        # Add the new column
        cursor.execute("""
            ALTER TABLE bots
            ADD COLUMN dnd_template_spreadsheet_id VARCHAR(100)
        """)

        conn.commit()
        print("Successfully added 'dnd_template_spreadsheet_id' column to bots table.")
        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
