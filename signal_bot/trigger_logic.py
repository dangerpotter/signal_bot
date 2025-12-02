"""Logic for determining when bots should respond to messages."""

import random
import re
from typing import Optional, Union

from signal_bot.models import Bot


def should_bot_respond(
    bot_data: Union[Bot, dict],
    message_text: str,
    sender_name: str,
    is_direct_message: bool = False
) -> tuple[bool, str]:
    """
    Determine if a bot should respond to a message.

    Args:
        bot_data: Bot object or dict with bot configuration
        message_text: The message to check
        sender_name: Name of the sender
        is_direct_message: Whether this is a DM

    Returns:
        tuple of (should_respond: bool, reason: str)
    """
    # Support both Bot object and dict
    if isinstance(bot_data, dict):
        enabled = bot_data.get('enabled', True)
        respond_on_mention = bot_data.get('respond_on_mention', True)
        random_chance_percent = bot_data.get('random_chance_percent', 0)
        name = bot_data['name']
    else:
        enabled = bot_data.enabled
        respond_on_mention = bot_data.respond_on_mention
        random_chance_percent = bot_data.random_chance_percent
        name = bot_data.name

    if not enabled:
        return False, "bot_disabled"

    # Always respond to direct messages
    if is_direct_message:
        return True, "direct_message"

    # Check for mention
    if _is_mentioned(name, message_text):
        if respond_on_mention:
            return True, "mentioned"

    # Check for command trigger
    if _has_command_trigger(message_text, name):
        return True, "command_trigger"

    # Random chance
    if random_chance_percent > 0:
        roll = random.randint(1, 100)
        if roll <= random_chance_percent:
            return True, "random_chance"

    return False, "no_trigger"


def _is_mentioned(bot_name: str, message_text: str) -> bool:
    """Check if the bot is mentioned in the message."""
    text_lower = message_text.lower()
    bot_name_lower = bot_name.lower()

    # Direct name mention
    if bot_name_lower in text_lower:
        return True

    # @mention style
    if f"@{bot_name_lower}" in text_lower:
        return True

    # Common variations
    # e.g., "Claude" -> "claude", "claude-bot", "@claude"
    name_parts = bot_name_lower.split()
    for part in name_parts:
        if len(part) >= 3:  # Avoid matching short words
            if part in text_lower.split():
                return True

    return False


def _has_command_trigger(message_text: str, bot_name: str) -> bool:
    """Check if the message contains a command directed at this bot."""
    text_lower = message_text.lower()
    bot_name_lower = bot_name.lower()

    # !ask <bot_name> patterns
    ask_pattern = rf"!ask\s+{re.escape(bot_name_lower)}"
    if re.search(ask_pattern, text_lower):
        return True

    # hey <bot_name> patterns at start of message
    hey_pattern = rf"^(hey|hi|yo|ok)\s+{re.escape(bot_name_lower)}"
    if re.search(hey_pattern, text_lower):
        return True

    return False


def extract_mentioned_bots(message_text: str, all_bots: list[Bot]) -> list[Bot]:
    """Extract which bots are mentioned in a message."""
    mentioned = []

    for bot in all_bots:
        if _is_mentioned(bot.name, message_text):
            mentioned.append(bot)

    return mentioned


def get_response_delay(bot_data: Union[Bot, dict], reason: str) -> float:
    """
    Get delay before responding (in seconds).
    Helps make responses feel more natural and prevents flooding.

    Args:
        bot_data: Bot object or dict (unused currently, for future customization)
        reason: The trigger reason

    Returns:
        Delay in seconds
    """
    base_delay = 1.0

    if reason == "mentioned":
        # Respond fairly quickly to mentions
        return base_delay + random.uniform(0.5, 2.0)
    elif reason == "random_chance":
        # Random responses should feel more organic - longer delay
        return base_delay + random.uniform(2.0, 5.0)
    elif reason == "command_trigger":
        # Commands get quick response
        return base_delay + random.uniform(0.3, 1.0)
    else:
        return base_delay + random.uniform(1.0, 3.0)
