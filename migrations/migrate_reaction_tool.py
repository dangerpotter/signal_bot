"""Migration for reaction tool feature.

Adds new columns:
- reaction_tool_enabled: Boolean toggle for the reaction tool
- max_reactions_per_response: Integer cap on reactions per response

Old columns (reaction_enabled, reaction_chance_percent, llm_reaction_enabled)
are left in place but will no longer be used.
"""
import sqlite3


def migrate():
    conn = sqlite3.connect('signal_bot.db')
    cursor = conn.cursor()

    # Add new columns
    columns = [
        ("reaction_tool_enabled", "BOOLEAN", "0"),
        ("max_reactions_per_response", "INTEGER", "3")
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
