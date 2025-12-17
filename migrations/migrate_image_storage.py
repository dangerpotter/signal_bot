#!/usr/bin/env python3
"""
Migration script to add image storage columns for context image support.
- Adds image_data and image_media_type columns to message_logs table (fallback storage)
- Adds image_data and image_media_type columns to chat_logs table (primary storage)

Run with: python migrate_image_storage.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def migrate():
    """Add image storage columns to message_logs and chat_logs tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns in message_logs table
    cursor.execute("PRAGMA table_info(message_logs)")
    message_logs_columns = [col[1] for col in cursor.fetchall()]

    # Add image_data column to message_logs table
    if 'image_data' not in message_logs_columns:
        print("Adding 'image_data' column to message_logs table...")
        cursor.execute("ALTER TABLE message_logs ADD COLUMN image_data TEXT")
    else:
        print("Column 'image_data' already exists in message_logs.")

    # Add image_media_type column to message_logs table
    if 'image_media_type' not in message_logs_columns:
        print("Adding 'image_media_type' column to message_logs table...")
        cursor.execute("ALTER TABLE message_logs ADD COLUMN image_media_type VARCHAR(50)")
    else:
        print("Column 'image_media_type' already exists in message_logs.")

    # Check existing columns in chat_logs table
    cursor.execute("PRAGMA table_info(chat_logs)")
    chat_logs_columns = [col[1] for col in cursor.fetchall()]

    # Add image_data column to chat_logs table
    if 'image_data' not in chat_logs_columns:
        print("Adding 'image_data' column to chat_logs table...")
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN image_data TEXT")
    else:
        print("Column 'image_data' already exists in chat_logs.")

    # Add image_media_type column to chat_logs table
    if 'image_media_type' not in chat_logs_columns:
        print("Adding 'image_media_type' column to chat_logs table...")
        cursor.execute("ALTER TABLE chat_logs ADD COLUMN image_media_type VARCHAR(50)")
    else:
        print("Column 'image_media_type' already exists in chat_logs.")

    conn.commit()
    conn.close()
    print("\nMigration complete!")
    print("Image storage for context window now available.")
    print("\nHow it works:")
    print("  - If chat_log_enabled=True: images stored in chat_logs (follows retention policy)")
    print("  - If chat_log_enabled=False: images stored in message_logs (follows context window)")
    print("  - Bot can now see images from previous messages in context window")


if __name__ == '__main__':
    migrate()
