"""Flask application for Signal bot admin interface."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Flask
from signal_bot.models import db
from signal_bot.config_signal import DB_PATH, SECRET_KEY, FLASK_DEBUG


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__,
                template_folder="templates",
                static_folder="static")

    # Configuration
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialize database
    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()
        _seed_default_prompts()

    # Register routes
    from signal_bot.admin.routes import register_routes
    register_routes(app)

    return app


def _seed_default_prompts():
    """Seed default system prompts from config.py if not already present."""
    from signal_bot.models import SystemPromptTemplate

    # Check if prompts already exist
    if SystemPromptTemplate.query.first() is not None:
        return

    # Import prompts from main config
    try:
        from config import SYSTEM_PROMPT_PAIRS
    except ImportError:
        # Fallback default prompt
        SYSTEM_PROMPT_PAIRS = {
            "Default": {
                "system_prompt_ai1": "You are a helpful AI assistant participating in a Signal group chat. Be conversational, funny, and engaging. Keep responses concise (1-3 sentences usually). You can use !image \"prompt\" to generate images."
            }
        }

    # Create templates from existing prompts
    for style_name, prompts in SYSTEM_PROMPT_PAIRS.items():
        for key, prompt_text in prompts.items():
            if prompt_text:  # Skip empty prompts
                template_id = f"{style_name.lower().replace(' ', '_')}_{key}"
                template = SystemPromptTemplate(
                    id=template_id,
                    name=f"{style_name} - {key.replace('system_prompt_', '').upper()}",
                    prompt_text=prompt_text
                )
                db.session.add(template)

    db.session.commit()
