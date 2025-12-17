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

# Real-time memory settings
REALTIME_MEMORY_ENABLED = True  # Enable instant memory saves when user says "remember..."

# Location context settings
TRAVEL_PROXIMITY_DAYS = 7  # Include travel location if within N days of travel date

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

# WebSocket configuration for json-rpc mode
WEBSOCKET_ENABLED = True  # Master toggle for WebSocket support
WEBSOCKET_RECONNECT_DELAY = 1.0  # Initial reconnect delay in seconds
WEBSOCKET_MAX_RECONNECT_DELAY = 60.0  # Max reconnect delay (exponential backoff cap)
WEBSOCKET_PING_INTERVAL = 20.0  # Send ping every N seconds to keep connection alive
WEBSOCKET_PING_TIMEOUT = 10.0  # Consider connection dead if no pong in N seconds
