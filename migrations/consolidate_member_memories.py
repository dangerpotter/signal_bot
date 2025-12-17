#!/usr/bin/env python3
"""
Migration script to consolidate duplicate member memories.

Problem: Memories can be stored with different member_id values (Signal UUIDs)
for the same member_name, creating duplicates per (group_id, member_name, slot_type).

Solution: For each (group_id, member_name, slot_type) with multiple entries:
- Keep the most recently updated entry
- Delete older duplicates
- Normalize member_id to the most common value for that member

Run with: python migrations/consolidate_member_memories.py
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signal_bot.db')


def consolidate():
    """Consolidate duplicate member memories by (group_id, member_name, slot_type)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Scanning for duplicate member memories...")
    print("=" * 60)

    # Find all duplicates: same (group_id, member_name, slot_type) with different IDs
    cursor.execute("""
        SELECT group_id, member_name, slot_type, COUNT(*) as cnt
        FROM group_member_memories
        GROUP BY group_id, member_name, slot_type
        HAVING COUNT(*) > 1
    """)

    duplicates = cursor.fetchall()

    if not duplicates:
        print("No duplicates found. Database is clean.")
        conn.close()
        return

    print(f"Found {len(duplicates)} duplicate groups to consolidate:\n")

    total_deleted = 0

    for group_id, member_name, slot_type, count in duplicates:
        print(f"  {member_name} / {slot_type}: {count} entries")

        # Get all entries for this combination, ordered by updated_at DESC
        cursor.execute("""
            SELECT id, member_id, content, updated_at, created_at
            FROM group_member_memories
            WHERE group_id = ? AND member_name = ? AND slot_type = ?
            ORDER BY
                CASE WHEN updated_at IS NOT NULL THEN updated_at ELSE created_at END DESC
        """, (group_id, member_name, slot_type))

        entries = cursor.fetchall()

        if len(entries) <= 1:
            continue

        # Keep the first (most recent) entry
        keep_id = entries[0][0]
        keep_content = entries[0][2][:50] + "..." if len(entries[0][2]) > 50 else entries[0][2]

        # Get the most common member_id for this member (prefer non-null)
        cursor.execute("""
            SELECT member_id, COUNT(*) as cnt
            FROM group_member_memories
            WHERE group_id = ? AND member_name = ?
            AND member_id IS NOT NULL AND member_id != ''
            GROUP BY member_id
            ORDER BY cnt DESC
            LIMIT 1
        """, (group_id, member_name))

        best_member_id_row = cursor.fetchone()
        best_member_id = best_member_id_row[0] if best_member_id_row else entries[0][1]

        # Update the kept entry to use the best member_id
        cursor.execute("""
            UPDATE group_member_memories
            SET member_id = ?
            WHERE id = ?
        """, (best_member_id, keep_id))

        # Delete the other entries
        delete_ids = [e[0] for e in entries[1:]]

        for entry in entries[1:]:
            old_content = entry[2][:30] + "..." if len(entry[2]) > 30 else entry[2]
            print(f"    - Deleting: \"{old_content}\"")

        cursor.execute(f"""
            DELETE FROM group_member_memories
            WHERE id IN ({','.join('?' * len(delete_ids))})
        """, delete_ids)

        deleted = len(delete_ids)
        total_deleted += deleted
        print(f"    ✓ Kept: \"{keep_content}\" (deleted {deleted} duplicate(s))")
        print()

    conn.commit()
    conn.close()

    print("=" * 60)
    print(f"Consolidation complete!")
    print(f"  - Duplicate groups processed: {len(duplicates)}")
    print(f"  - Total entries deleted: {total_deleted}")
    print()
    print("Note: Future duplicates will be prevented by updating")
    print("save_member_memory to check by member_name, not just member_id.")


def show_current_state():
    """Show current state of member memories for debugging."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("\nCurrent member memories:")
    print("=" * 60)

    cursor.execute("""
        SELECT group_id, member_name, slot_type, content, member_id, updated_at
        FROM group_member_memories
        ORDER BY member_name, slot_type
    """)

    for row in cursor.fetchall():
        group_id, member_name, slot_type, content, member_id, updated_at = row
        content_preview = content[:40] + "..." if len(content) > 40 else content
        print(f"  {member_name} | {slot_type}: {content_preview}")

    conn.close()


if __name__ == '__main__':
    import sys

    if '--show' in sys.argv:
        show_current_state()
    else:
        consolidate()
        print("\nRun with --show to see current state of memories.")
