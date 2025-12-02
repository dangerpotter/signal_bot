"""Bot manager for orchestrating multiple Signal bots."""

import asyncio
import logging
import httpx
import random
import time
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
                'reaction_enabled': bot.reaction_enabled,
                'reaction_chance_percent': bot.reaction_chance_percent,
                'llm_reaction_enabled': bot.llm_reaction_enabled
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
        port: int = 8080
    ) -> bool:
        """Send a text message to a group."""
        import base64
        url = f"http://localhost:{port}/v2/send"

        # Convert internal_id format to API format (group.base64(internal_id))
        if not group_id.startswith("group."):
            api_group_id = "group." + base64.b64encode(group_id.encode()).decode()
        else:
            api_group_id = group_id

        payload = {
            "number": phone_number,
            "recipients": [api_group_id],
            "message": message
        }

        try:
            client = await self._get_http_client(port)
            response = await client.post(url, json=payload, timeout=30.0)

            if response.status_code in (200, 201):
                return True
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

        # Debug: log all incoming messages (safely encode for Windows console)
        source_name = envelope.get('sourceName', 'Unknown')
        logger.info(f"Received message envelope: {source_name} - dataMessage keys: {list(data_message.keys()) if data_message else 'None'}")

        if not data_message:
            return  # Not a data message

        # Get group info
        group_info = data_message.get("groupInfo", {})
        group_id = group_info.get("groupId")

        # Debug: log group info
        logger.info(f"Group info: {group_info}, group_id: {group_id}")

        if not group_id:
            return  # Not a group message (could add DM support later)

        # All database operations need app context - keep it open for the whole handler
        with _flask_app.app_context():
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
            message_text = data_message.get("message", "")
            message_timestamp = data_message.get("timestamp")  # For reactions

            if not message_text:
                return  # Empty message

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

            # Create send callbacks
            async def send_text(text: str):
                await self.send_message(bot_data['phone_number'], group_id, text, bot_data['signal_api_port'])

            async def send_image_cb(path: str):
                await self.send_image(bot_data['phone_number'], group_id, path, port=bot_data['signal_api_port'])

            # Handle the message (inside app context for DB operations)
            await self.message_handler.handle_incoming_message(
                group_id=group_id,
                sender_name=sender_name,
                sender_id=sender_id,
                message_text=message_text,
                bot_data=bot_data,
                is_mentioned=is_mentioned_native,  # Pass native mention flag
                send_callback=lambda t: asyncio.create_task(send_text(t)),
                send_image_callback=lambda p: asyncio.create_task(send_image_cb(p))
            )

            # Maybe react to the message with an emoji
            if message_timestamp and sender_id:
                await self._maybe_react_to_message(
                    bot_data, group_id, sender_id, message_timestamp, message_text
                )

    async def _idle_news_checker(self):
        """
        Background task that checks for idle groups and posts news commentary.

        Rules:
        - After 15 min of no activity, starts checking every 5 min
        - Each 5 min check has 10% chance to trigger
        - When triggered, searches for news and posts humorous commentary
        """
        IDLE_THRESHOLD = 15 * 60  # 15 minutes before idle mode starts
        CHECK_INTERVAL = 5 * 60   # Check every 5 minutes after idle
        TRIGGER_CHANCE = 0.10     # 10% chance to post

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

                        if bot and group and bot.enabled and group.enabled and bot.web_search_enabled:
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
                                    'web_search_enabled': bot.web_search_enabled
                                }
                            })

                for pair in group_bot_pairs:
                    group_id = pair['group_id']
                    bot_data = pair['bot']

                    # Get last activity time (default to now if never seen)
                    last_activity = self._group_last_activity.get(group_id, current_time)
                    idle_time = current_time - last_activity

                    # Check if we're in idle mode (15+ min of silence)
                    if idle_time < IDLE_THRESHOLD:
                        continue

                    # Check if enough time has passed since last idle check
                    last_check = self._group_last_idle_check.get(group_id, 0)
                    if current_time - last_check < CHECK_INTERVAL:
                        continue

                    # Update last check time
                    self._group_last_idle_check[group_id] = current_time

                    # Roll the dice - 10% chance
                    if random.random() > TRIGGER_CHANCE:
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

    # Animal emojis for random reactions
    ANIMAL_EMOJIS = [
        "🐶", "🐱", "🐼", "🦊", "🐸", "🐧", "🦆", "🐙", "🦋", "🐢",
        "🦝", "🐨", "🦥", "🐰", "🐻", "🦩", "🐝", "🦎", "🐳", "🐷"
    ]

    async def _maybe_react_to_message(
        self,
        bot_data: dict,
        group_id: str,
        sender_id: str,
        message_timestamp: int,
        message_text: str
    ):
        """Decide whether to react to a message and with what emoji."""
        if not bot_data.get('reaction_enabled', True):
            return

        # Option 1: Random animal emoji (configurable chance)
        chance = bot_data.get('reaction_chance_percent', 5)
        if random.random() * 100 < chance:
            emoji = random.choice(self.ANIMAL_EMOJIS)
            await self.send_reaction(
                bot_data['phone_number'],
                group_id,
                sender_id,
                message_timestamp,
                emoji,
                bot_data['signal_api_port']
            )
            self._log_activity(
                "reaction_sent",
                bot_data['id'],
                group_id,
                f"{bot_data['name']} reacted with {emoji} (random)"
            )
            return

        # Option 2: LLM-evaluated funny detection
        if bot_data.get('llm_reaction_enabled', False):
            is_funny, emoji = await self._evaluate_funny(message_text, bot_data)
            if is_funny:
                await self.send_reaction(
                    bot_data['phone_number'],
                    group_id,
                    sender_id,
                    message_timestamp,
                    emoji,
                    bot_data['signal_api_port']
                )
                self._log_activity(
                    "reaction_sent",
                    bot_data['id'],
                    group_id,
                    f"{bot_data['name']} reacted with {emoji} (funny detected)"
                )

    async def _evaluate_funny(self, message_text: str, bot_data: dict) -> tuple[bool, str]:
        """Use LLM to evaluate if a message is funny and suggest an emoji."""
        # Quick check - skip very short messages
        if len(message_text) < 10:
            return False, ""

        # Only evaluate ~30% of messages to save API calls
        if random.random() > 0.30:
            return False, ""

        try:
            from shared_utils import call_openrouter_api
            from config import AI_MODELS
            from signal_bot.config_signal import HUMOR_EVAL_MODEL
        except ImportError as e:
            logger.error(f"Failed to import for funny evaluation: {e}")
            return False, ""

        # Use configurable model for humor evaluation (default: Haiku for speed/cost)
        model_id = HUMOR_EVAL_MODEL

        prompt = f'''Is this message funny, clever, or reaction-worthy? Message: "{message_text}"

Respond with ONLY one of:
- NO
- YES 😂 (if genuinely funny/hilarious)
- YES 💀 (if dark humor or deadpan)
- YES 🔥 (if a sick burn or roast)
- YES ❤️ (if wholesome or sweet)
- YES 🤯 (if mind-blowing or surprising)

Be selective - most messages are NOT reaction-worthy.'''

        try:
            response = call_openrouter_api(
                prompt=prompt,
                conversation_history=[],
                model=model_id,
                system_prompt="You evaluate messages for humor. Be brief and selective.",
                stream_callback=None,
                web_search=False
            )

            if response and response.strip().upper().startswith("YES"):
                # Extract emoji from response
                parts = response.strip().split()
                emoji = parts[-1] if len(parts) > 1 else "😂"
                # Validate it's actually an emoji (simple check)
                if len(emoji) <= 4:
                    return True, emoji
                return True, "😂"
            return False, ""

        except Exception as e:
            logger.error(f"Funny evaluation failed: {e}")
            return False, ""

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
