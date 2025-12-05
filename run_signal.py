#!/usr/bin/env python3
"""
Entry point for Signal Bot Admin UI and Bot Manager.

Usage:
    python run_signal.py              # Run admin UI only
    python run_signal.py --with-bots  # Run admin UI + start bots
    python run_signal.py --bots-only  # Run bots only (headless)
"""

import argparse
import asyncio
import logging
import threading
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

# Configure stdout for UTF-8 with error replacement (fixes Windows Unicode issues)
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('signal_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def run_admin_ui(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    """Run the Flask admin UI."""
    from signal_bot.admin.app import create_app

    app = create_app()
    logger.info(f"Starting admin UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


async def run_bot_manager():
    """Run the Signal bot manager."""
    from signal_bot.bot_manager import get_bot_manager

    manager = get_bot_manager()
    logger.info("Starting Signal Bot Manager...")

    try:
        await manager.start()

        # Keep running until cancelled
        while True:
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("Shutting down bot manager...")
        await manager.stop()
    except Exception as e:
        logger.error(f"Bot manager error: {e}")
        await manager.stop()
        raise


# Global Flask app for bot manager thread
_flask_app = None


def run_bots_in_thread():
    """Run bot manager in a separate thread."""
    from signal_bot.bot_manager import set_flask_app as set_bot_manager_app
    from signal_bot.message_handler import set_flask_app as set_message_handler_app
    from signal_bot.google_sheets_client import set_flask_app as set_sheets_app
    from signal_bot.google_calendar_client import set_flask_app as set_calendar_app

    # Set the Flask app for database context
    set_bot_manager_app(_flask_app)
    set_message_handler_app(_flask_app)
    set_sheets_app(_flask_app)
    set_calendar_app(_flask_app)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(run_bot_manager())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


def main():
    global _flask_app

    parser = argparse.ArgumentParser(description="Signal Bot Admin & Manager")
    parser.add_argument("--with-bots", action="store_true",
                        help="Start bots along with admin UI")
    parser.add_argument("--bots-only", action="store_true",
                        help="Run bots only (no admin UI)")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Admin UI host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5000,
                        help="Admin UI port (default: 5000)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable Flask debug mode")

    args = parser.parse_args()

    print("""
    ===============================================
    |  Signal Bot Admin                           |
    |  Liminal Backrooms - Signal Integration     |
    ===============================================
    """)

    try:
        if args.bots_only:
            # Run bots only
            logger.info("Running in bots-only mode")

            # Still need Flask app for database context
            from signal_bot.admin.app import create_app
            _flask_app = create_app()

            from signal_bot.bot_manager import set_flask_app as set_bot_manager_app
            from signal_bot.message_handler import set_flask_app as set_message_handler_app
            from signal_bot.google_sheets_client import set_flask_app as set_sheets_app
            from signal_bot.google_calendar_client import set_flask_app as set_calendar_app
            set_bot_manager_app(_flask_app)
            set_message_handler_app(_flask_app)
            set_sheets_app(_flask_app)
            set_calendar_app(_flask_app)

            asyncio.run(run_bot_manager())

        elif args.with_bots:
            # Run both admin UI and bots
            logger.info("Running admin UI with bot manager")

            # Create Flask app first so bot manager can use it
            from signal_bot.admin.app import create_app
            _flask_app = create_app()

            # Start bots in background thread
            bot_thread = threading.Thread(target=run_bots_in_thread, daemon=True)
            bot_thread.start()

            # Run admin UI in main thread (reuse the app we created)
            logger.info(f"Starting admin UI at http://{args.host}:{args.port}")
            _flask_app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)

        else:
            # Admin UI only
            logger.info("Running admin UI only (use --with-bots to start bots)")
            run_admin_ui(host=args.host, port=args.port, debug=args.debug)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
