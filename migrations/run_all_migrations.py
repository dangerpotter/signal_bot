#!/usr/bin/env python3
"""
Run all database migrations in order.

This script runs from the project root directory to ensure migrations
can find signal_bot.db correctly.

Usage: python migrations/run_all_migrations.py
"""

import os
import sys

# Change to project root (parent of migrations/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

# Import migrations after path setup
from migrations import migrate_context_window
from migrations import migrate_idle_news
from migrations import migrate_weather_enabled
from migrations import migrate_finance_enabled
from migrations import migrate_time_enabled
from migrations import migrate_wikipedia_enabled
from migrations import migrate_signal_timestamp
from migrations import migrate_reaction_tool
from migrations import migrate_google_sheets
from migrations import migrate_member_memory_model
from migrations import migrate_member_memory_tools
from migrations import migrate_google_calendar
from migrations import migrate_triggers


MIGRATIONS = [
    ("context_window", migrate_context_window),
    ("idle_news", migrate_idle_news),
    ("weather_enabled", migrate_weather_enabled),
    ("finance_enabled", migrate_finance_enabled),
    ("time_enabled", migrate_time_enabled),
    ("wikipedia_enabled", migrate_wikipedia_enabled),
    ("signal_timestamp", migrate_signal_timestamp),
    ("reaction_tool", migrate_reaction_tool),
    ("google_sheets", migrate_google_sheets),
    ("member_memory_model", migrate_member_memory_model),
    ("member_memory_tools", migrate_member_memory_tools),
    ("google_calendar", migrate_google_calendar),
    ("triggers", migrate_triggers),
]


def run_all():
    """Run all migrations in order."""
    print("=" * 60)
    print("Running all database migrations...")
    print(f"Working directory: {os.getcwd()}")
    print("=" * 60)

    for name, module in MIGRATIONS:
        print(f"\n--- Running migration: {name} ---")
        try:
            module.migrate()
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            return False

    print("\n" + "=" * 60)
    print("All migrations completed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
