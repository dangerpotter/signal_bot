"""Migration for image generation limit feature.

Adds new column:
- max_images_per_response: Integer cap on images per response (default 2)

This prevents bots from generating excessive images in a single response.
"""
import sqlite3


def migrate():
    conn = sqlite3.connect('signal_bot.db')
    cursor = conn.cursor()

    # Add new column
    columns = [
        ("max_images_per_response", "INTEGER", "2")
    ]

    for col_name, col_type, default in columns:
        try:
            cursor.execute(f"ALTER TABLE bots ADD COLUMN {col_name} {col_type} DEFAULT {default}")
            print(f"Added {col_name} column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"{col_name} column already exists")
            else:
                raise

    conn.commit()
    conn.close()
    print("Migration complete!")


if __name__ == "__main__":
    migrate()
