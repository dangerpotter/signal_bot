"""One-time migration to add context_window column to bots table."""
import sqlite3

DB_PATH = "signal_bot.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(bots)")
    columns = [col[1] for col in cursor.fetchall()]

    if "context_window" in columns:
        print("Column 'context_window' already exists. No migration needed.")
    else:
        cursor.execute("ALTER TABLE bots ADD COLUMN context_window INTEGER DEFAULT 25")
        conn.commit()
        print("Successfully added 'context_window' column with default value 25.")

    conn.close()

if __name__ == "__main__":
    migrate()
