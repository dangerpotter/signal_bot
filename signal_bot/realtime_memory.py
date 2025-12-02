"""
Real-time memory extraction for Signal bot.

Detects when users ask the bot to remember something and saves it immediately,
rather than waiting for the 6-hour background scan.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from flask import Flask

logger = logging.getLogger(__name__)

# Flask app reference for database context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app


# Trigger patterns by category - if any match, we attempt real-time extraction
REMEMBER_TRIGGERS = {
    # Explicit memory requests (highest priority)
    "explicit": [
        r"remember\s+(that\s+)?(i|my)\s+",           # "remember I prefer..."
        r"don\'?t\s+forget\s+(that\s+)?(i|my)\s+",   # "don't forget I..."
        r"keep\s+in\s+mind\s+(that\s+)?(i|my)?\s*",  # "keep in mind I work nights"
        r"note\s+that\s+i\s+",                        # "note that I live in Denver"
        r"fyi\s+i\s+",                                # "fyi I'll be traveling"
        r"please\s+remember\s+",                      # "please remember..."
        r"save\s+(this|that)\s+(to\s+)?memory",       # "save this to memory"
        r"add\s+(this|that)\s+to\s+(your\s+)?memory", # "add this to your memory"
    ],

    # Response preference indicators
    "response_prefs": [
        r"(give\s+me|i\s+(want|like|prefer))\s+(shorter|longer|brief|detailed|succinct|concise)",
        r"(stop|quit|don\'?t)\s+(being\s+so|with\s+the)\s+(verbose|wordy|lengthy)",
        r"(be\s+)?(more|less)\s+(words|text|explanation|verbose|brief|detailed)",
        r"be\s+(more\s+)?(brief|concise|succinct|direct|detailed|verbose)",
        r"i\s+prefer\s+(short|long|brief|detailed|succinct|concise)\s+(responses?|answers?|replies?)",
        r"respond\s+(to\s+me\s+)?(with|in)\s+(bullets?|lists?|paragraphs?)",
    ],

    # Location indicators
    "location": [
        r"i\s+(live|am|reside)\s+in\s+",              # "I live in Denver"
        r"i\'?m\s+(based|located)\s+(in|at)\s+",      # "I'm based in NYC"
        r"i\'?m\s+(going|traveling|heading)\s+to\s+", # "I'm going to Miami"
        r"i\'?ll\s+be\s+in\s+",                       # "I'll be in LA next week"
        r"(back\s+)?home\s+(is|in)\s+",               # "home is in Texas"
        r"i\s+moved\s+to\s+",                         # "I moved to Seattle"
        r"flying\s+(out\s+)?to\s+",                   # "flying to NYC tomorrow"
    ],

    # Interest indicators
    "interests": [
        r"i\s+(really\s+)?(love|enjoy|like|am\s+into)\s+",
        r"i\'?m\s+(really\s+)?(into|a\s+fan\s+of|obsessed\s+with)\s+",
        r"my\s+favorite\s+\w+\s+is\s+",
        r"i\'?m\s+(going\s+to|attending)\s+(the|a)\s+\w+\s+(concert|show|game|event)",
    ],

    # Life events
    "life_events": [
        r"(my|i\'?m\s+getting)\s+(wedding|married|engaged)",
        r"my\s+birthday\s+is\s+",
        r"i\'?m\s+(graduating|retiring|moving|having\s+a\s+baby)\s+",
        r"(getting|got)\s+(married|engaged|divorced)",
        r"my\s+anniversary\s+is\s+",
    ],

    # Work info
    "work_info": [
        r"i\s+work\s+(as|at|for)\s+",
        r"i\'?m\s+a\s+\w+\s+(at|for|engineer|developer|manager|designer|doctor|lawyer|teacher)",
        r"my\s+job\s+(is|involves)\s+",
        r"i\s+just\s+(started|got|accepted)\s+a\s+(job|position|role)\s+",
    ],
}

# Compile all patterns for efficiency
_compiled_triggers = {}
for category, patterns in REMEMBER_TRIGGERS.items():
    _compiled_triggers[category] = [re.compile(p, re.IGNORECASE) for p in patterns]


def check_for_memory_trigger(message_text: str) -> Optional[str]:
    """
    Check if a message contains any memory trigger patterns.

    Returns:
        The matched category (e.g., "explicit", "response_prefs", "location")
        or None if no trigger matched.
    """
    for category, patterns in _compiled_triggers.items():
        for pattern in patterns:
            if pattern.search(message_text):
                return category
    return None


MEMORY_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "skip": {
            "type": "boolean",
            "description": "Set to true if nothing worth remembering"
        },
        "slot_type": {
            "type": "string",
            "enum": ["response_prefs", "home_location", "travel_location",
                     "interests", "media_prefs", "life_events", "work_info", "social_notes"],
            "description": "The type of memory slot to save to"
        },
        "content": {
            "type": "string",
            "description": "Concise factual content to remember"
        },
        "valid_from": {
            "type": ["string", "null"],
            "description": "Start date in YYYY-MM-DD format, or null"
        },
        "valid_until": {
            "type": ["string", "null"],
            "description": "End date in YYYY-MM-DD format, or null"
        }
    },
    "required": ["skip"],
    "additionalProperties": False
}


async def extract_memory_from_message(
    message_text: str,
    sender_name: str,
    sender_id: str,
    group_id: str,
    detected_category: str,
    bot_model: Optional[str] = None
) -> Optional[dict]:
    """
    Extract memory from a single message using structured outputs.

    Args:
        message_text: The message content
        sender_name: Name of the sender
        sender_id: Signal UUID of sender
        group_id: Group ID
        detected_category: The category that triggered this extraction
        bot_model: Model to use (required)

    Returns:
        Dict with slot_type, content, valid_from, valid_until, or None if nothing to save
    """
    try:
        from shared_utils import call_openrouter_api_structured
        from config import AI_MODELS
    except ImportError as e:
        logger.error(f"Failed to import for memory extraction: {e}")
        return None

    # Map detected category to likely slot type (helps the AI)
    category_to_slot = {
        "explicit": None,  # Could be anything, AI decides
        "response_prefs": "response_prefs",
        "location": "home_location",  # or travel_location, AI decides
        "interests": "interests",
        "life_events": "life_events",
        "work_info": "work_info",
    }

    likely_slot = category_to_slot.get(detected_category)
    slot_hint = f"\nLikely slot type based on detected pattern: {likely_slot}" if likely_slot else ""

    system_prompt = """You extract memories from user messages for a chatbot's long-term memory.

Extract ONLY factual information worth remembering. Be concise.

Available slot types:
- response_prefs: How they prefer responses (length, style, format)
- home_location: Where they live permanently
- travel_location: Where they're traveling (include dates if mentioned)
- interests: Hobbies, interests, events they're attending
- media_prefs: Shows, movies, games, music they like
- life_events: Weddings, birthdays, graduations, major milestones
- work_info: Job, company, profession
- social_notes: Relationships within the group

If the message doesn't contain anything worth remembering, set skip=true.
Otherwise, provide slot_type and content."""

    user_prompt = f"""Message from {sender_name}: "{message_text}"
{slot_hint}

Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}

Extract the memory:"""

    try:
        # Use the bot's configured model
        model_id = AI_MODELS.get(bot_model, bot_model) if bot_model else None
        if not model_id:
            logger.error("No bot model provided for memory extraction")
            return None

        # Use structured outputs for guaranteed valid JSON
        result = call_openrouter_api_structured(
            prompt=user_prompt,
            model=model_id,
            system_prompt=system_prompt,
            json_schema=MEMORY_EXTRACTION_SCHEMA,
            schema_name="memory_extraction"
        )

        if not result:
            return None

        if result.get("skip"):
            logger.debug(f"No memory to extract from message by {sender_name}")
            return None

        # Validate slot type is present
        if not result.get("slot_type"):
            logger.warning(f"No slot_type in extraction result")
            return None

        logger.info(f"Extracted real-time memory for {sender_name}: {result.get('slot_type')} = {result.get('content', '')[:50]}...")
        return result

    except Exception as e:
        logger.error(f"Error in memory extraction: {e}")
        return None


def save_member_memory(
    group_id: str,
    member_id: str,
    member_name: str,
    slot_type: str,
    content: str,
    valid_from: Optional[datetime] = None,
    valid_until: Optional[datetime] = None
) -> bool:
    """
    Save or replace a member memory in the database.
    Latest request always wins (replaces existing).

    Returns:
        True if saved successfully, False otherwise
    """
    from signal_bot.models import db, GroupMemberMemory, ActivityLog

    try:
        with _flask_app.app_context():
            # Find existing memory for this slot
            existing = GroupMemberMemory.query.filter_by(
                group_id=group_id,
                member_name=member_name,
                slot_type=slot_type
            ).first()

            if existing:
                # Update existing
                old_content = existing.content
                existing.content = content
                existing.member_id = member_id
                existing.valid_from = valid_from
                existing.valid_until = valid_until
                existing.updated_at = datetime.utcnow()
                logger.info(f"Updated memory: {member_name}/{slot_type}: '{old_content[:30]}...' -> '{content[:30]}...'")
            else:
                # Create new
                new_memory = GroupMemberMemory(
                    group_id=group_id,
                    member_id=member_id,
                    member_name=member_name,
                    slot_type=slot_type,
                    content=content,
                    valid_from=valid_from,
                    valid_until=valid_until
                )
                db.session.add(new_memory)
                logger.info(f"Created memory: {member_name}/{slot_type} = '{content[:50]}...'")

            # Log activity
            log = ActivityLog(
                event_type="memory_realtime_save",
                group_id=group_id,
                description=f"Real-time save: {slot_type} for {member_name}: {content[:50]}..."
            )
            db.session.add(log)

            db.session.commit()
            return True

    except Exception as e:
        logger.error(f"Error saving member memory: {e}")
        try:
            with _flask_app.app_context():
                db.session.rollback()
        except:
            pass
        return False


def format_memory_confirmation_instruction(memory_result: dict, member_name: str) -> str:
    """
    Generate an instruction for the bot to confirm the memory save.

    Args:
        memory_result: The extracted memory dict
        member_name: Name of the user whose memory was saved

    Returns:
        An instruction string to append to the system prompt
    """
    slot_type = memory_result.get("slot_type", "")
    content = memory_result.get("content", "")

    # Customize confirmation based on slot type
    confirmations = {
        "response_prefs": f"IMPORTANT: {member_name} just told you their response preference. START your response by briefly acknowledging this (e.g., 'Got it, I'll keep it brief!' or 'Noted, more details coming your way!' or similar). Then continue with your normal response.",

        "home_location": f"Briefly acknowledge you've noted {member_name} is in/from {content}. Something casual like 'Oh nice, {content}!' or 'Cool, {content}!' then continue normally.",

        "travel_location": f"Briefly acknowledge {member_name}'s upcoming travel to {content}. Something like 'Have fun in {content}!' or 'Nice, {content} trip!' then continue.",

        "interests": f"Briefly and naturally acknowledge you've noted {member_name}'s interest. Don't be over-eager, just a casual acknowledgment then continue.",

        "life_events": f"Acknowledge {member_name}'s life event appropriately (congrats for happy events, etc). Keep it genuine but brief.",

        "work_info": f"Briefly acknowledge you've noted {member_name}'s work info if it fits naturally. Don't force it.",

        "media_prefs": f"If natural, briefly acknowledge the media preference. Don't force it if it doesn't fit.",

        "social_notes": f"Acknowledge naturally if it fits the conversation.",
    }

    return confirmations.get(slot_type, f"Briefly acknowledge you've noted: {content}")


async def check_and_save_realtime_memory(
    message_text: str,
    sender_name: str,
    sender_id: str,
    group_id: str,
    bot_data: dict
) -> Optional[dict]:
    """
    Main entry point: check for memory triggers, extract, and save.

    Args:
        message_text: The incoming message
        sender_name: Name of sender
        sender_id: Signal UUID of sender
        group_id: Group ID
        bot_data: Bot configuration dict

    Returns:
        Dict with 'saved': True and memory details if saved, None otherwise
    """
    from signal_bot.config_signal import REALTIME_MEMORY_ENABLED

    # Check if feature is enabled
    if not REALTIME_MEMORY_ENABLED:
        return None

    # Check for trigger patterns
    triggered_category = check_for_memory_trigger(message_text)
    if not triggered_category:
        return None

    logger.info(f"Memory trigger detected in message from {sender_name}: category={triggered_category}")

    # Extract memory using LLM
    memory_result = await extract_memory_from_message(
        message_text=message_text,
        sender_name=sender_name,
        sender_id=sender_id,
        group_id=group_id,
        detected_category=triggered_category,
        bot_model=bot_data.get('model')
    )

    if not memory_result:
        return None

    # Parse dates if provided
    valid_from = None
    valid_until = None
    if memory_result.get("valid_from"):
        try:
            valid_from = datetime.fromisoformat(memory_result["valid_from"])
        except ValueError:
            pass
    if memory_result.get("valid_until"):
        try:
            valid_until = datetime.fromisoformat(memory_result["valid_until"])
        except ValueError:
            pass

    # Save to database
    saved = save_member_memory(
        group_id=group_id,
        member_id=sender_id or sender_name,
        member_name=sender_name,
        slot_type=memory_result["slot_type"],
        content=memory_result["content"],
        valid_from=valid_from,
        valid_until=valid_until
    )

    if saved:
        return {
            "saved": True,
            "slot_type": memory_result["slot_type"],
            "content": memory_result["content"],
            "member_name": sender_name
        }

    return None
