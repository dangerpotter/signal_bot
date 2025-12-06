"""One-time migration to add member_memory_model column to bots table."""
import sqlite3

DB_PATH = "signal_bot.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    if "member_memory_model" in columns:
        print("Column 'member_memory_model' already exists. No migration needed.")
    else:
        cursor.execute("ALTER TABLE bots ADD COLUMN member_memory_model VARCHAR(100)")
        conn.commit()
        print("Successfully added 'member_memory_model' column.")

    conn.close()

if __name__ == "__main__":
    migrate()
