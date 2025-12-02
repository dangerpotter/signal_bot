"""Signal-specific configuration settings."""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "signal-data"
DB_PATH = BASE_DIR / "signal_bot.db"

# Default settings
DEFAULT_ROLLING_WINDOW = 25  # Messages to keep in context
DEFAULT_RANDOM_CHANCE = 15   # % chance to respond randomly
LONG_TERM_SAVE_CHANCE = 10   # % chance to save a memorable snippet
LONG_TERM_RECALL_CHANCE = 5  # % chance to reference old memory

# Model settings for auxiliary tasks (can use env vars to override)
# These are separate from the main bot response model
HUMOR_EVAL_MODEL = os.getenv("HUMOR_EVAL_MODEL", "anthropic/claude-3-5-haiku-20241022")
MEMORY_SCAN_MODEL = os.getenv("MEMORY_SCAN_MODEL", "anthropic/claude-sonnet-4-20250514")  # Fallback if bot has no model

# Signal API base URLs (for Docker containers)
SIGNAL_API_PORTS = {
    1: 8080,
    2: 8081,
    3: 8082,
}

def get_signal_api_url(bot_number: int = 1) -> str:
    """Get the Signal API URL for a specific bot container."""
    port = SIGNAL_API_PORTS.get(bot_number, 8080)
    return f"http://localhost:{port}"

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production")
