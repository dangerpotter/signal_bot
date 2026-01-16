"""
Migration script to add Gemini image generation settings to bots table.
Run this once: python migrate_gemini_image.py

Adds:
- image_api_provider: 'openrouter' (default) or 'gemini' for direct Gemini API
- gemini_image_model: Model to use for Gemini direct image generation
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

    # Check existing columns
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    changes_made = False

    # Add image_api_provider column
    if "image_api_provider" not in columns:
        print("Adding 'image_api_provider' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN image_api_provider VARCHAR(20) DEFAULT 'openrouter'")
        changes_made = True
    else:
        print("Column 'image_api_provider' already exists.")

    # Add gemini_image_model column
    if "gemini_image_model" not in columns:
        print("Adding 'gemini_image_model' column to bots table...")
        cursor.execute("ALTER TABLE bots ADD COLUMN gemini_image_model VARCHAR(50)")
        changes_made = True
    else:
        print("Column 'gemini_image_model' already exists.")

    if changes_made:
        conn.commit()
        print("Migration complete!")
    else:
        print("Nothing to do.")

    conn.close()


if __name__ == "__main__":
    migrate()
