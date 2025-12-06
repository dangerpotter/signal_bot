#!/usr/bin/env python3
"""
One-time cleanup script to remove duplicate messages from message_logs table.

Duplicates are identified by:
- Same group_id
- Same sender_name
- Same content
- Timestamps within 5 seconds of each other

This script keeps the OLDEST message of each duplicate set.
"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')

def cleanup_duplicates():
    """Remove duplicate messages from message_logs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all messages ordered by timestamp
    cursor.execute("""
        SELECT id, group_id, sender_name, content, timestamp, is_bot
        FROM message_logs
        ORDER BY group_id, sender_name, content, timestamp
    """)
    messages = cursor.fetchall()

    print(f"Found {len(messages)} total messages in message_logs")

    # Track messages to delete (duplicates)
    ids_to_delete = []

    # Group messages by (group_id, sender_name, content)
    groups = {}
    for msg in messages:
        msg_id, group_id, sender_name, content, timestamp, is_bot = msg
        key = (group_id, sender_name, content)
        if key not in groups:
            groups[key] = []
        groups[key].append((msg_id, timestamp))

    # Find duplicates within each group (messages with same content within 5 seconds)
    for key, msg_list in groups.items():
        if len(msg_list) <= 1:
            continue

        # Sort by timestamp
        msg_list.sort(key=lambda x: x[1] if x[1] else '')

        # Compare consecutive messages - if within 5 seconds, mark as duplicate
        kept_id = msg_list[0][0]  # Keep the first (oldest)
        kept_time = msg_list[0][1]

        for msg_id, timestamp in msg_list[1:]:
            if not timestamp or not kept_time:
                # If no timestamp, use content-based dedup (assume duplicate)
                ids_to_delete.append(msg_id)
                continue

            # Parse timestamps
            try:
                t1 = datetime.fromisoformat(kept_time.replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                diff = abs((t2 - t1).total_seconds())

                if diff < 5:  # Within 5 seconds - duplicate
                    ids_to_delete.append(msg_id)
                else:
                    # New unique message, update keeper
                    kept_id = msg_id
                    kept_time = timestamp
            except (ValueError, TypeError):
                # If timestamp parsing fails, assume duplicate of recent message
                ids_to_delete.append(msg_id)

    print(f"Found {len(ids_to_delete)} duplicate messages to remove")

    if ids_to_delete:
        # Delete duplicates in batches
        batch_size = 100
        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i:i+batch_size]
            placeholders = ','.join('?' * len(batch))
            cursor.execute(f"DELETE FROM message_logs WHERE id IN ({placeholders})", batch)

        conn.commit()
        print(f"Deleted {len(ids_to_delete)} duplicate messages")
    else:
        print("No duplicates found - database is clean!")

    # Show remaining count
    cursor.execute("SELECT COUNT(*) FROM message_logs")
    remaining = cursor.fetchone()[0]
    print(f"Remaining messages: {remaining}")

    conn.close()

if __name__ == '__main__':
    print("Signal Bot Message Duplicate Cleanup")
    print("=" * 40)
    cleanup_duplicates()
