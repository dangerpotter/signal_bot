"""Bot manager for orchestrating multiple Signal bots."""

import asyncio
import logging
import httpx
import random
import time
import uuid
from typing import Optional, Callable
from dataclasses import dataclass
from flask import Flask

from signal_bot.models import db, Bot, GroupConnection, BotGroupAssignment, ActivityLog
from signal_bot.config_signal import get_signal_api_url
from signal_bot.message_handler import get_message_handler
from signal_bot.member_memory_scanner import get_memory_scanner, set_flask_app as set_scanner_app

logger = logging.getLogger(__name__)

# Flask app reference for context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app
    # Also set for memory scanner
    set_scanner_app(app)


@dataclass
class BotStatus:
    """Status information for a bot."""
    bot_id: str
    name: str
    connected: bool
    phone_number: Optional[str]
    groups: list[str]
    error: Optional[str] = None


class SignalBotManager:
    """
    Manages multiple Signal bot instances.

    Each bot has its own phone number and signal-cli-rest-api container.
    """

    def __init__(self):
        self.running = False
        self._tasks: dict[str, asyncio.Task] = {}
        self._http_clients: dict[int, httpx.AsyncClient] = {}
        self.message_handler = get_message_handler()

        # Idle news feature - track last activity per group
        self._group_last_activity: dict[str, float] = {}  # group_id -> timestamp
        self._group_last_idle_check: dict[str, float] = {}  # group_id -> timestamp
        self._idle_checker_task: Optional[asyncio.Task] = None
        self._startup_time: float = time.time()  # Track when manager started for idle calculation

        # Member memory scanner
        self.memory_scanner = get_memory_scanner()

    async def start(self):
        """Start the bot manager and all enabled bots."""
        if self.running:
            logger.warning("Bot manager already running")
            return

        self.running = True
        logger.info("Starting Signal Bot Manager")

        # Get all enabled bots (need app context for DB)
        with _flask_app.app_context():
            bots = Bot.query.filter_by(enabled=True).all()
            bot_ids = [bot.id for bot in bots]

        for bot_id in bot_ids:
            await self.start_bot(bot_id)

        # Start the idle news checker
        self._idle_checker_task = asyncio.create_task(
            self._idle_news_checker(),
            name="idle-news-checker"
        )

        # Start the member memory scanner (runs every 12 hours)
        await self.memory_scanner.start()

        logger.info(f"Started {len(bot_ids)} bots + idle news checker + memory scanner")

    async def stop(self):
        """Stop all bots and the manager."""
        self.running = False
        logger.info("Stopping Signal Bot Manager")

        # Stop memory scanner
        await self.memory_scanner.stop()

        # Cancel idle checker
        if self._idle_checker_task:
            self._idle_checker_task.cancel()
            try:
                await self._idle_checker_task
            except asyncio.CancelledError:
                pass

        # Cancel all bot tasks
        for bot_id, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        # Close HTTP clients
        for client in self._http_clients.values():
            await client.aclose()
        self._http_clients.clear()

        logger.info("Bot manager stopped")

    async def start_bot(self, bot_id: str) -> bool:
        """Start a specific bot."""
        with _flask_app.app_context():
            bot = Bot.query.get(bot_id)
            if not bot:
                logger.error(f"Bot {bot_id} not found")
                return False

            if not bot.phone_number:
                logger.error(f"Bot {bot.name} has no phone number configured")
                return False

            if bot_id in self._tasks:
                logger.warning(f"Bot {bot.name} already running")
                return True

            # Copy bot data for use outside context
            bot_data = {
                'id': bot.id,
                'name': bot.name,
                'phone_number': bot.phone_number,
                'signal_api_port': bot.signal_api_port,
                'model': bot.model,
                'system_prompt': bot.system_prompt,
                'enabled': bot.enabled,
                'respond_on_mention': bot.respond_on_mention,
                'random_chance_percent': bot.random_chance_percent,
                'image_generation_enabled': bot.image_generation_enabled,
                'web_search_enabled': bot.web_search_enabled,
                'weather_enabled': getattr(bot, 'weather_enabled', False),
                'finance_enabled': getattr(bot, 'finance_enabled', False),
                'time_enabled': getattr(bot, 'time_enabled', False),
                'wikipedia_enabled': getattr(bot, 'wikipedia_enabled', False),
                'reaction_tool_enabled': getattr(bot, 'reaction_tool_enabled', False),
                'max_reactions_per_response': getattr(bot, 'max_reactions_per_response', 3),
                'typing_enabled': getattr(bot, 'typing_enabled', True),
                'read_receipts_enabled': getattr(bot, 'read_receipts_enabled', False),
                # Google Sheets integration
                'google_sheets_enabled': getattr(bot, 'google_sheets_enabled', False),
                'google_client_id': getattr(bot, 'google_client_id', None),
                'google_client_secret': getattr(bot, 'google_client_secret', None),
                'google_refresh_token': getattr(bot, 'google_refresh_token', None),
                'google_token_expiry': getattr(bot, 'google_token_expiry', None),
                'google_connected': getattr(bot, 'google_connected', False),
                # Google Calendar integration (shares OAuth with Sheets)
                'google_calendar_enabled': getattr(bot, 'google_calendar_enabled', False),
                # Member memory tools
                'member_memory_tools_enabled': getattr(bot, 'member_memory_tools_enabled', False),
                'member_memory_model': getattr(bot, 'member_memory_model', None),
                'context_window': getattr(bot, 'context_window', 25),
            }

        # Create task to listen for messages
        task = asyncio.create_task(
            self._bot_listener(bot_data),
            name=f"bot-{bot_id}"
        )
        self._tasks[bot_id] = task

        self._log_activity("bot_started", bot_id, None, f"Bot '{bot_data['name']}' started")
        logger.info(f"Bot {bot_data['name']} started")
        return True

    async def stop_bot(self, bot_id: str) -> bool:
        """Stop a specific bot."""
        if bot_id not in self._tasks:
            return False

        task = self._tasks.pop(bot_id)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        with _flask_app.app_context():
            bot = Bot.query.get(bot_id)
            if bot:
                self._log_activity("bot_stopped", bot_id, None, f"Bot '{bot.name}' stopped")
                logger.info(f"Bot {bot.name} stopped")

        return True

    async def restart_bot(self, bot_id: str) -> bool:
        """Restart a specific bot."""
        await self.stop_bot(bot_id)
        return await self.start_bot(bot_id)

    def get_bot_status(self, bot_id: str) -> Optional[BotStatus]:
        """Get status for a specific bot."""
        with _flask_app.app_context():
            bot = Bot.query.get(bot_id)
            if not bot:
                return None

            # Get assigned groups
            assignments = BotGroupAssignment.query.filter_by(bot_id=bot_id).all()
            groups = [a.group_id for a in assignments]

            return BotStatus(
                bot_id=bot.id,
                name=bot.name,
                connected=bot_id in self._tasks,
                phone_number=bot.phone_number,
                groups=groups
            )

    def get_all_statuses(self) -> list[BotStatus]:
        """Get status for all bots."""
        with _flask_app.app_context():
            bots = Bot.query.all()
            bot_ids = [bot.id for bot in bots]
        return [self.get_bot_status(bid) for bid in bot_ids if self.get_bot_status(bid)]

    async def check_signal_api_health(self, port: int = 8080) -> bool:
        """Check if a Signal API container is healthy."""
        url = f"http://localhost:{port}/v1/about"

        try:
            client = await self._get_http_client(port)
            response = await client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed for port {port}: {e}")
            return False

    async def get_groups_for_phone(self, phone_number: str, port: int = 8080) -> list[dict]:
        """Get list of groups for a phone number."""
        url = f"http://localhost:{port}/v1/groups/{phone_number}"

        try:
            client = await self._get_http_client(port)
            response = await client.get(url, timeout=10.0)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get groups: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error getting groups: {e}")
            return []

    async def send_message(
        self,
        phone_number: str,
        group_id: str,
        message: str,
        port: int = 8080,
        quote_timestamp: Optional[int] = None,
        quote_author: Optional[str] = None,
        mentions: Optional[list[dict]] = None,
        text_styles: Optional[list[dict]] = None
    ) -> bool:
        """
        Send a text message to a group.

        Args:
            phone_number: Bot's phone number
            group_id: Target group ID
            message: Message text
            port: Signal API port
            quote_timestamp: Timestamp of message to quote/reply to
            quote_author: Author UUID of message to quote
            mentions: List of mentions [{start, length, uuid}]
            text_styles: List of styles [{start, length, style}] where style is BOLD, ITALIC, etc.
        """
        url = f"http://localhost:{port}/v2/send"

        payload = {
            "number": phone_number,
            "recipients": [self._format_group_id(group_id)],
            "message": message
        }

        # Add quote/reply if provided
        if quote_timestamp and quote_author:
            payload["quote"] = {
                "timestamp": quote_timestamp,
                "author": quote_author
            }

        # Add mentions if provided
        if mentions:
            payload["mentions"] = mentions

        # Add text styles if provided
        if text_styles:
            payload["text_style"] = text_styles

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=30.0)

            if response.status_code in (200, 201):
                return True
            elif response.status_code == 400:
                # Check for partial delivery (unregistered user in group)
                error_text = response.text
                if "Unregistered user" in error_text:
                    logger.warning(f"Partial send - some recipients unregistered: {error_text}")
                    return True  # Message likely delivered to other members
                else:
                    logger.error(f"Send message failed: {response.status_code} - {error_text}")
                    return False
            else:
                logger.error(f"Send message failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def send_image(
        self,
        phone_number: str,
        group_id: str,
        image_path: str,
        caption: Optional[str] = None,
        port: int = 8080
    ) -> bool:
        """Send an image to a group."""
        import base64
        url = f"http://localhost:{port}/v2/send"

        # Convert internal_id format to API format (group.base64(internal_id))
        if not group_id.startswith("group."):
            api_group_id = "group." + base64.b64encode(group_id.encode()).decode()
        else:
            api_group_id = group_id

        # Read image as base64
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
        except Exception as e:
            logger.error(f"Failed to read image: {e}")
            return False

        payload = {
            "number": phone_number,
            "recipients": [api_group_id],
            "message": caption or "",
            "base64_attachments": [image_data]
        }

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=60.0)

            if response.status_code in (200, 201):
                return True
            else:
                logger.error(f"Send image failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            return False

    async def get_attachment_data(
        self,
        attachment_id: str,
        group_id: str,
        account: str,
        port: int = 8080
    ) -> Optional[str]:
        """Fetch attachment data from Signal API as base64 string.

        Tries JSON-RPC first (for json-rpc mode), falls back to REST (for normal mode).
        Returns base64-encoded attachment data.
        """
        import base64 as b64
        client = await self._get_http_client(port)

        # Try JSON-RPC first (works in json-rpc mode)
        rpc_url = f"http://localhost:{port}/api/v1/rpc"
        payload = {
            "jsonrpc": "2.0",
            "method": "getAttachment",
            "params": {
                "account": account,
                "id": attachment_id,
                "group-id": group_id
            },
            "id": 1
        }
        logger.info(f"[DEBUG] Trying JSON-RPC getAttachment: id={attachment_id}, group={group_id[:20]}...")
        try:
            response = await client.post(rpc_url, json=payload, timeout=30.0)
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    logger.info(f"Successfully fetched attachment via JSON-RPC: {len(result['result'])} chars")
                    return result["result"]  # Base64 string
                elif "error" in result:
                    logger.warning(f"JSON-RPC error: {result['error']}")
            else:
                logger.info(f"[DEBUG] JSON-RPC returned {response.status_code}, trying REST fallback...")
        except Exception as e:
            logger.info(f"[DEBUG] JSON-RPC failed ({e}), trying REST fallback...")

        # Fallback: Try REST endpoint with attachment_id as filename (for normal mode)
        rest_url = f"http://localhost:{port}/v1/attachments/{attachment_id}"
        logger.info(f"[DEBUG] Trying REST: {rest_url}")
        try:
            response = await client.get(rest_url, timeout=30.0)
            logger.info(f"[DEBUG] REST response: {response.status_code}, content-type: {response.headers.get('content-type')}, size: {len(response.content)}")
            if response.status_code == 200:
                encoded = b64.b64encode(response.content).decode('utf-8')
                logger.info(f"Successfully fetched attachment via REST: {len(encoded)} chars")
                return encoded
            else:
                logger.error(f"REST fallback failed: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"REST fallback error: {e}")

        return None

    async def send_reaction(
        self,
        phone_number: str,
        group_id: str,
        target_author: str,
        target_timestamp: int,
        emoji: str,
        port: int = 8080
    ) -> bool:
        """Send an emoji reaction to a message."""
        import base64
        url = f"http://localhost:{port}/v1/reactions/{phone_number}"

        # Convert internal_id format to API format if needed
        if not group_id.startswith("group."):
            api_group_id = "group." + base64.b64encode(group_id.encode()).decode()
        else:
            api_group_id = group_id

        payload = {
            "recipient": api_group_id,
            "reaction": emoji,
            "target_author": target_author,
            "timestamp": target_timestamp
        }

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=10.0)

            if response.status_code in (200, 201, 204):
                logger.info(f"Sent reaction {emoji} to message from {target_author[:8]}...")
                return True
            else:
                logger.error(f"Send reaction failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending reaction: {e}")
            return False

    async def _get_http_client(self, port: int) -> httpx.AsyncClient:
        """Get or create HTTP client for a port."""
        if port not in self._http_clients:
            self._http_clients[port] = httpx.AsyncClient()
        return self._http_clients[port]

    def _format_group_id(self, group_id: str) -> str:
        """Convert internal group ID to API format (group.base64(internal_id))."""
        import base64
        if not group_id.startswith("group."):
            return "group." + base64.b64encode(group_id.encode()).decode()
        return group_id

    async def send_typing(
        self,
        phone_number: str,
        group_id: str,
        port: int = 8080,
        stop: bool = False
    ) -> bool:
        """Send a typing indicator to a group."""
        url = f"http://localhost:{port}/v1/typing/{phone_number}"

        payload = {
            "recipient": self._format_group_id(group_id),
        }
        if stop:
            payload["stop"] = True

        try:
            client = await self._get_http_client(port)
            response = await client.put(url, json=payload, timeout=5.0)

            if response.status_code in (200, 201, 204):
                logger.debug(f"Typing {'stopped' if stop else 'started'} for {phone_number}")
                return True
            elif response.status_code == 404:
                # Endpoint not available in this REST API version - silently skip
                logger.debug("Typing indicator endpoint not available")
                return False
            else:
                logger.debug(f"Send typing failed: {response.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Error sending typing: {e}")
            return False

    async def send_read_receipt(
        self,
        phone_number: str,
        sender_id: str,
        timestamps: list[int],
        port: int = 8080
    ) -> bool:
        """Send a read receipt for messages."""
        url = f"http://localhost:{port}/v1/receipt/{phone_number}"

        payload = {
            "recipient": sender_id,
            "timestamps": timestamps,
            "type": "read"
        }

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=5.0)

            if response.status_code in (200, 201, 204):
                logger.debug(f"Read receipt sent for {len(timestamps)} messages")
                return True
            elif response.status_code == 404:
                # Endpoint not available in this REST API version - silently skip
                logger.debug("Read receipt endpoint not available")
                return False
            else:
                logger.debug(f"Send read receipt failed: {response.status_code}")
                return False
        except Exception as e:
            logger.debug(f"Error sending read receipt: {e}")
            return False

    async def join_group_by_link(
        self,
        phone_number: str,
        invite_url: str,
        port: int = 8080
    ) -> Optional[dict]:
        """Join a group via an invitation link.

        Since the bbernhard REST API doesn't expose joinGroup, we need to:
        1. Stop the container (releases the config lock)
        2. Run signal-cli joinGroup directly on the host-mounted volume
        3. Restart the container

        This requires the signal-cli data to be mounted at a known host path.
        """
        import subprocess
        import time
        import os

        # Get the project root directory (where docker-compose.signal.yml is)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Map port to container name and data path (absolute)
        container_map = {
            8080: ("signal-bot-1", os.path.join(project_root, "signal-data", "bot1")),
            8081: ("signal-bot-2", os.path.join(project_root, "signal-data", "bot2")),
            8082: ("signal-bot-3", os.path.join(project_root, "signal-data", "bot3"))
        }

        if port not in container_map:
            logger.error(f"Unknown port {port} for join_group_by_link")
            return None

        container_name, data_path = container_map[port]

        try:
            logger.info(f"Joining group via invite link (container: {container_name})")

            # Step 1: Stop the container to release the config lock
            logger.info(f"Stopping {container_name}...")
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True, text=True, timeout=30
            )
            if stop_result.returncode != 0:
                logger.error(f"Failed to stop container: {stop_result.stderr}")
                return None

            # Step 2: Run signal-cli joinGroup using a temporary container
            # This uses the same image but overrides entrypoint to run signal-cli directly
            logger.info(f"Running joinGroup command...")
            join_cmd = [
                "docker", "run", "--rm",
                "--entrypoint", "",
                "-v", f"{data_path}:/home/.local/share/signal-cli",
                "bbernhard/signal-cli-rest-api:latest",
                "signal-cli", "--config", "/home/.local/share/signal-cli",
                "-a", phone_number,
                "joinGroup", "--uri", invite_url
            ]

            logger.info(f"Command: {' '.join(join_cmd)}")
            join_result = subprocess.run(
                join_cmd,
                capture_output=True, text=True, timeout=120  # Increased timeout
            )
            logger.info(f"Join result: rc={join_result.returncode}, stdout={join_result.stdout}, stderr={join_result.stderr}")

            # Step 3: Restart the original container
            logger.info(f"Restarting {container_name}...")
            start_result = subprocess.run(
                ["docker", "start", container_name],
                capture_output=True, text=True, timeout=30
            )

            # Wait for container to be healthy
            time.sleep(3)

            if join_result.returncode == 0:
                logger.info(f"Successfully joined group: {join_result.stdout}")
                # Return a dict with group info if available
                return {"status": "joined", "output": join_result.stdout.strip()}
            else:
                error_msg = join_result.stderr or join_result.stdout or "Unknown error"
                logger.error(f"Join group failed: {error_msg}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Join group timed out")
            # Try to restart container on timeout
            subprocess.run(["docker", "start", container_name], capture_output=True, timeout=30)
            return None
        except Exception as e:
            logger.error(f"Error joining group: {e}")
            # Try to restart container on error
            try:
                subprocess.run(["docker", "start", container_name], capture_output=True, timeout=30)
            except Exception:
                pass
            return None

    async def edit_message(
        self,
        phone_number: str,
        group_id: str,
        original_timestamp: int,
        new_text: str,
        port: int = 8080
    ) -> bool:
        """Edit a previously sent message."""
        url = f"http://localhost:{port}/v2/send"

        payload = {
            "number": phone_number,
            "recipients": [self._format_group_id(group_id)],
            "message": new_text,
            "edit_timestamp": original_timestamp
        }

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=30.0)

            if response.status_code in (200, 201):
                logger.info(f"Message edited successfully")
                return True
            else:
                logger.error(f"Edit message failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return False

    async def delete_message(
        self,
        phone_number: str,
        group_id: str,
        timestamp: int,
        port: int = 8080
    ) -> bool:
        """Delete a previously sent message."""
        url = f"http://localhost:{port}/v1/messages/{phone_number}"

        payload = {
            "recipient": self._format_group_id(group_id),
            "timestamp": timestamp
        }

        try:
            client = await self._get_http_client(port)
            response = await client.delete(url, json=payload, timeout=10.0)

            if response.status_code in (200, 201, 204):
                logger.info(f"Message deleted successfully")
                return True
            else:
                logger.error(f"Delete message failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

    async def _bot_listener(self, bot_data: dict):
        """
        Main listener loop for a bot.

        Uses Signal CLI REST API's receive endpoint to poll for messages.
        """
        port = bot_data['signal_api_port']
        phone = bot_data['phone_number']

        logger.info(f"Starting listener for {bot_data['name']} on port {port}")

        while self.running:
            try:
                # Poll for new messages
                messages = await self._receive_messages(phone, port)

                for msg in messages:
                    await self._process_message(bot_data, msg)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in bot listener {bot_data['name']}: {e}")

            # Short delay between polls
            await asyncio.sleep(1)

    async def _receive_messages(self, phone: str, port: int) -> list[dict]:
        """Receive new messages from Signal API."""
        url = f"http://localhost:{port}/v1/receive/{phone}"

        try:
            client = await self._get_http_client(port)
            response = await client.get(url, timeout=30.0)

            if response.status_code == 200:
                return response.json()
            else:
                return []
        except Exception as e:
            logger.debug(f"Receive error: {e}")
            return []

    async def _process_message(self, bot_data: dict, message: dict):
        """Process an incoming Signal message."""
        # Extract message details
        envelope = message.get("envelope", {})
        data_message = envelope.get("dataMessage", {})

        # Extract source name for logging
        source_name = envelope.get('sourceName', 'Unknown')

        if not data_message:
            # Non-data envelopes (receipts, typing indicators) - log at debug level to reduce noise
            logger.debug(f"Received non-data envelope from: {source_name}")
            return

        # Log actual messages at info level
        logger.info(f"Received message envelope: {source_name} - dataMessage keys: {list(data_message.keys())}")

        # Get group info
        group_info = data_message.get("groupInfo", {})
        group_id = group_info.get("groupId")

        # Debug: log group info
        logger.info(f"Group info: {group_info}, group_id: {group_id}")

        if not group_id:
            return  # Not a group message (could add DM support later)

        # All database operations need app context - keep it open for the whole handler
        with _flask_app.app_context():
            # Refresh bot settings from database to pick up any changes made in admin UI
            bot = Bot.query.get(bot_data['id'])
            if bot:
                bot_data['model'] = bot.model
                bot_data['system_prompt'] = bot.system_prompt
                bot_data['enabled'] = bot.enabled
                bot_data['respond_on_mention'] = bot.respond_on_mention
                bot_data['random_chance_percent'] = bot.random_chance_percent
                bot_data['image_generation_enabled'] = bot.image_generation_enabled
                bot_data['web_search_enabled'] = bot.web_search_enabled
                bot_data['weather_enabled'] = getattr(bot, 'weather_enabled', False)
                bot_data['finance_enabled'] = getattr(bot, 'finance_enabled', False)
                bot_data['time_enabled'] = getattr(bot, 'time_enabled', False)
                bot_data['wikipedia_enabled'] = getattr(bot, 'wikipedia_enabled', False)
                bot_data['reaction_tool_enabled'] = getattr(bot, 'reaction_tool_enabled', False)
                bot_data['max_reactions_per_response'] = getattr(bot, 'max_reactions_per_response', 3)
                bot_data['typing_enabled'] = getattr(bot, 'typing_enabled', True)
                bot_data['read_receipts_enabled'] = getattr(bot, 'read_receipts_enabled', False)

            assignment = BotGroupAssignment.query.filter_by(
                bot_id=bot_data['id'],
                group_id=group_id
            ).first()

            if not assignment:
                logger.info(f"Bot {bot_data['name']} not assigned to group {group_id}")
                return  # Bot not in this group

            # Check if group is enabled
            group = GroupConnection.query.get(group_id)
            if not group:
                logger.info(f"Group {group_id} not found in database")
                return
            if not group.enabled:
                logger.info(f"Group {group_id} is disabled")
                return
            group_name = group.name

            # Extract sender and message
            sender_id = envelope.get("sourceUuid", envelope.get("source", "Unknown"))
            sender_name = envelope.get("sourceName", "Unknown")
            message_text = data_message.get("message") or ""  # Handle None value from image-only messages
            message_timestamp = data_message.get("timestamp")  # For reactions

            # Extract image attachments
            attachments = data_message.get("attachments", [])
            image_attachments = []
            for att in attachments:
                # Debug: log full attachment structure
                logger.info(f"[DEBUG] Attachment object keys: {list(att.keys())}")
                logger.info(f"[DEBUG] Attachment object: {att}")
                content_type = att.get("contentType", "")
                if content_type.startswith("image/"):
                    attachment_id = att.get("id")
                    if attachment_id:
                        image_attachments.append({
                            "content_type": content_type,
                            "id": attachment_id,
                            "filename": att.get("filename"),
                            "size": att.get("size", 0)
                        })

            if image_attachments:
                logger.info(f"Found {len(image_attachments)} image attachment(s)")

            if not message_text and not image_attachments:
                return  # Empty message with no attachments

            # Don't respond to own messages
            if sender_id == bot_data['phone_number']:
                return

            # Track activity for idle news feature
            self._group_last_activity[group_id] = time.time()

            # Check for Signal native @mentions of the bot
            mentions = data_message.get("mentions", [])
            is_mentioned_native = False

            # Normalize bot's phone number for comparison
            bot_phone_normalized = bot_data['phone_number'].replace("+", "").replace("-", "").replace(" ", "")

            for mention in mentions:
                mentioned_uuid = mention.get("uuid", "")
                mentioned_number = mention.get("number", "")
                # Normalize mentioned number for comparison
                mentioned_normalized = mentioned_number.replace("+", "").replace("-", "").replace(" ", "") if mentioned_number else ""

                if mentioned_normalized and bot_phone_normalized == mentioned_normalized:
                    is_mentioned_native = True
                    break
                # Also check UUID match (future-proofing)
                if mentioned_uuid and mentioned_uuid == bot_data.get('signal_uuid'):
                    is_mentioned_native = True
                    break

            # FALLBACK: If Signal mentions array failed, check text for bot name
            if not is_mentioned_native:
                bot_name_lower = bot_data['name'].lower()
                text_lower = message_text.lower()
                if bot_name_lower in text_lower or f"@{bot_name_lower}" in text_lower:
                    is_mentioned_native = True

            # Log safely (encode special chars for Windows)
            safe_text = message_text[:50].encode('ascii', 'replace').decode('ascii')
            logger.info(f"[{group_name}] {sender_name}: {safe_text}... (mentions: {len(mentions)}, bot_mentioned: {is_mentioned_native})")

            # Send read receipt if enabled
            if bot_data.get('read_receipts_enabled', False) and message_timestamp and sender_id:
                asyncio.create_task(
                    self.send_read_receipt(
                        bot_data['phone_number'],
                        sender_id,
                        [message_timestamp],
                        bot_data['signal_api_port']
                    )
                )

            # Create send callbacks with quote support
            async def send_text(
                text: str,
                quote_timestamp: Optional[int] = None,
                quote_author: Optional[str] = None,
                mentions: Optional[list] = None,
                text_styles: Optional[list] = None
            ):
                await self.send_message(
                    bot_data['phone_number'],
                    group_id,
                    text,
                    bot_data['signal_api_port'],
                    quote_timestamp=quote_timestamp,
                    quote_author=quote_author,
                    mentions=mentions,
                    text_styles=text_styles
                )

            async def send_image_cb(path: str):
                await self.send_image(bot_data['phone_number'], group_id, path, port=bot_data['signal_api_port'])

            # Create typing callbacks
            async def send_typing_cb():
                await self.send_typing(bot_data['phone_number'], group_id, bot_data['signal_api_port'])

            async def stop_typing_cb():
                await self.send_typing(bot_data['phone_number'], group_id, bot_data['signal_api_port'], stop=True)

            # Process image attachments into base64
            incoming_images = []
            for att in image_attachments:
                try:
                    base64_data = await self.get_attachment_data(
                        attachment_id=att["id"],
                        group_id=group_id,
                        account=bot_data['phone_number'],
                        port=bot_data['signal_api_port']
                    )
                    if base64_data:
                        incoming_images.append({
                            "media_type": att["content_type"],
                            "data": base64_data
                        })
                        logger.info(f"Processed image attachment: {att['content_type']}, {len(base64_data)} chars")
                except Exception as e:
                    logger.error(f"Failed to process attachment {att['id']}: {e}")

            # Create reaction callback for tool-based reactions
            async def send_reaction_cb(target_sender_id: str, target_timestamp: int, emoji: str):
                """Send an emoji reaction to a specific message."""
                await self.send_reaction(
                    bot_data['phone_number'],
                    group_id,
                    target_sender_id,
                    target_timestamp,
                    emoji,
                    bot_data['signal_api_port']
                )
                self._log_activity(
                    "reaction_sent",
                    bot_data['id'],
                    group_id,
                    f"{bot_data['name']} reacted with {emoji}"
                )

            # Handle the message (inside app context for DB operations)
            await self.message_handler.handle_incoming_message(
                group_id=group_id,
                sender_name=sender_name,
                sender_id=sender_id,
                message_text=message_text,
                message_timestamp=message_timestamp,
                bot_data=bot_data,
                is_mentioned=is_mentioned_native,  # Pass native mention flag
                send_callback=lambda t, qt=None, qa=None, m=None, ts=None: asyncio.create_task(send_text(t, qt, qa, m, ts)),
                send_image_callback=lambda p: asyncio.create_task(send_image_cb(p)),
                send_typing_callback=lambda: asyncio.create_task(send_typing_cb()),
                stop_typing_callback=lambda: asyncio.create_task(stop_typing_cb()),
                incoming_images=incoming_images if incoming_images else None,
                send_reaction_callback=lambda sid, ts, em: asyncio.create_task(send_reaction_cb(sid, ts, em))
            )

    async def _idle_news_checker(self):
        """
        Background task that checks for idle groups and posts news commentary.

        Uses per-bot configurable settings:
        - idle_threshold_minutes: How long group must be quiet (default 15)
        - idle_check_interval_minutes: How often to check (default 5)
        - idle_trigger_chance_percent: Chance to post each check (default 10%)

        When triggered, searches for news and posts humorous commentary.
        Requires both web_search_enabled AND idle_news_enabled to be True.
        """
        logger.info("Idle news checker started")

        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = time.time()

                # Get all active group assignments
                with _flask_app.app_context():
                    assignments = BotGroupAssignment.query.all()
                    group_bot_pairs = []

                    for assignment in assignments:
                        bot = Bot.query.get(assignment.bot_id)
                        group = GroupConnection.query.get(assignment.group_id)

                        if bot and group and bot.enabled and group.enabled and bot.web_search_enabled and bot.idle_news_enabled:
                            group_bot_pairs.append({
                                'group_id': assignment.group_id,
                                'group_name': group.name,
                                'bot': {
                                    'id': bot.id,
                                    'name': bot.name,
                                    'phone_number': bot.phone_number,
                                    'signal_api_port': bot.signal_api_port,
                                    'model': bot.model,
                                    'system_prompt': bot.system_prompt,
                                    'web_search_enabled': bot.web_search_enabled,
                                    'idle_threshold_minutes': bot.idle_threshold_minutes or 15,
                                    'idle_check_interval_minutes': bot.idle_check_interval_minutes or 5,
                                    'idle_trigger_chance_percent': bot.idle_trigger_chance_percent or 10
                                }
                            })

                for pair in group_bot_pairs:
                    group_id = pair['group_id']
                    bot_data = pair['bot']

                    # Get per-bot settings
                    idle_threshold = bot_data['idle_threshold_minutes'] * 60  # Convert to seconds
                    check_interval = bot_data['idle_check_interval_minutes'] * 60  # Convert to seconds
                    trigger_chance = bot_data['idle_trigger_chance_percent'] / 100  # Convert to 0-1

                    # Get last activity time (default to startup time if never seen)
                    last_activity = self._group_last_activity.get(group_id, self._startup_time)
                    idle_time = current_time - last_activity

                    # Check if we're in idle mode
                    if idle_time < idle_threshold:
                        continue

                    # Check if enough time has passed since last idle check
                    last_check = self._group_last_idle_check.get(group_id, 0)
                    if current_time - last_check < check_interval:
                        continue

                    # Update last check time
                    self._group_last_idle_check[group_id] = current_time

                    # Roll the dice
                    if random.random() > trigger_chance:
                        logger.debug(f"Idle check for {pair['group_name']}: dice roll failed")
                        continue

                    # We're posting news!
                    logger.info(f"Idle news triggered for group {pair['group_name']} (idle for {idle_time/60:.1f} min)")

                    # Generate and send news commentary
                    await self._post_idle_news(group_id, bot_data, pair['group_name'])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in idle news checker: {e}")

        logger.info("Idle news checker stopped")

    async def _post_idle_news(self, group_id: str, bot_data: dict, group_name: str):
        """Generate and post news commentary to spark conversation."""
        try:
            from shared_utils import call_openrouter_api
            from config import AI_MODELS
        except ImportError as e:
            logger.error(f"Failed to import for idle news: {e}")
            return

        # Get model ID
        model_id = AI_MODELS.get(bot_data['model'], bot_data['model'])

        # Prompt that encourages searching for current news
        system_prompt = f"""You are {bot_data['name']}, casually dropping into a quiet group chat with something interesting.

Your task: Search for today's most interesting or weird news headlines, then share ONE in a humorous, conversation-starting way.

Guidelines:
- Be casual and funny, like you just stumbled across something wild
- Make it conversational - invite reactions or hot takes
- Keep it short (1-3 sentences max)
- Feel free to add your own humorous commentary or hot take
- Use lowercase if it fits the vibe
- Topics that work well: tech, science, weird news, pop culture, memes, crypto, AI

Examples of tone:
- "yo did anyone see that [news]?? absolutely unhinged behavior"
- "ok so apparently [news] and i have thoughts"
- "the simulation is glitching again, [news headline]"
- "can we talk about how [news]? like what even is happening"

Search for current news and pick something good!"""

        try:
            response = call_openrouter_api(
                prompt="What's the most interesting or weird news happening today? Find something good to share with the group.",
                conversation_history=[],
                model=model_id,
                system_prompt=system_prompt,
                stream_callback=None,
                web_search=True  # This is key - enables news search
            )

            if response and response.strip():
                # Send the message
                await self.send_message(
                    bot_data['phone_number'],
                    group_id,
                    response.strip(),
                    bot_data['signal_api_port']
                )

                # Update activity time (our own message counts as activity)
                self._group_last_activity[group_id] = time.time()

                # Log it
                self._log_activity(
                    "idle_news",
                    bot_data['id'],
                    group_id,
                    f"{bot_data['name']} posted idle news in {group_name}"
                )

                logger.info(f"Posted idle news to {group_name}")

        except Exception as e:
            logger.error(f"Failed to generate idle news: {e}")

    def _log_activity(self, event_type: str, bot_id: str, group_id: str, description: str):
        """Log an activity event."""
        try:
            with _flask_app.app_context():
                log = ActivityLog(
                    event_type=event_type,
                    bot_id=bot_id,
                    group_id=group_id,
                    description=description
                )
                db.session.add(log)
                db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")


# Global manager instance
_manager: Optional[SignalBotManager] = None


def get_bot_manager() -> SignalBotManager:
    """Get the global bot manager instance."""
    global _manager
    if _manager is None:
        _manager = SignalBotManager()
    return _manager
