"""
Migration: Add image_models table and bots.image_model column

Creates:
- image_models table for managing available image generation models
- image_model column on bots table for per-bot model selection

Run: python migrations/migrate_image_models.py
"""

import sqlite3
import os

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signal_bot.db")


def run_migration():
    """Run the image models migration."""
    print(f"Connecting to SQLite database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Starting image models migration...")

    # 1. Create image_models table
    print("Creating image_models table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS image_models (
            id VARCHAR(255) PRIMARY KEY,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            enabled BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    print("  - image_models table created (or already exists)")

    # 2. Add image_model column to bots table
    print("Adding image_model column to bots table...")
    cursor.execute("PRAGMA table_info(bots);")
    columns = [col[1] for col in cursor.fetchall()]

    if "image_model" not in columns:
        cursor.execute("""
            ALTER TABLE bots ADD COLUMN image_model VARCHAR(255);
        """)
        print("  - image_model column added to bots table")
    else:
        print("  - image_model column already exists")

    # 3. Seed default image model
    print("Seeding default image model...")
    cursor.execute("""
        INSERT OR IGNORE INTO image_models (id, display_name, description, enabled)
        VALUES (?, ?, ?, ?);
    """, (
        "google/gemini-3-pro-image-preview",
        "Gemini 3 Pro (Nano Banana)",
        "Google's Gemini 3 Pro image generation model",
        True
    ))
    print("  - Default model seeded: google/gemini-3-pro-image-preview")

    conn.commit()
    cursor.close()
    conn.close()

    print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()
