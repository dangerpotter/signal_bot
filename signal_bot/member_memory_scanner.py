"""
Memory scanner for extracting and updating member memories from chat history.

Runs every 12 hours to analyze the last 100 messages and update:
- Location slots (home_location, travel_location)
- General memory slots (general_1 through general_5)
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from flask import Flask

logger = logging.getLogger(__name__)

# Flask app reference for database context
_flask_app: Optional[Flask] = None

# Valid slot types
LOCATION_SLOTS = ["home_location", "travel_location"]
SEMANTIC_SLOTS = ["interests", "media_prefs", "life_events", "work_info", "social_notes", "response_prefs"]
ALL_SLOTS = LOCATION_SLOTS + SEMANTIC_SLOTS

# Memory priority tiers for context inclusion
TIER_ALWAYS = ["response_prefs"]  # Always include for current speaker
TIER_CONTEXTUAL = ["interests", "media_prefs", "life_events", "work_info", "social_notes"]  # Include for speaker + mentioned
TIER_SITUATIONAL = ["home_location", "travel_location"]  # Only when location-relevant

# Keywords that make location contextually relevant
LOCATION_KEYWORDS = [
    "weather", "temperature", "forecast", "rain", "snow", "hot", "cold",
    "time", "timezone", "what time",
    "local", "nearby", "around here", "in your area",
    "visit", "travel", "trip", "vacation", "flying",
    "where are you", "where do you live", "where is",
    "distance", "how far", "drive", "flight",
    "restaurant", "food", "eat", "coffee", "bar",
    "event", "concert", "game", "show",
]

# Instruction to prevent over-mentioning location
LOCATION_INSTRUCTION = """[Context includes location info for reference. Do NOT proactively mention
someone's location unless they ask about weather, time, local recommendations, or it's directly relevant.
Mentioning location unprompted feels intrusive.]"""

# Scan interval (6 hours)
SCAN_INTERVAL_HOURS = 6
MESSAGES_TO_SCAN = 100


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app


class MemberMemoryScanner:
    """Scans chat history and updates member memories."""

    def __init__(self):
        self.running = False
        self._scanner_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the memory scanner background task."""
        if self.running:
            return

        self.running = True
        self._scanner_task = asyncio.create_task(
            self._scanner_loop(),
            name="member-memory-scanner"
        )
        logger.info("Member memory scanner started")

    async def stop(self):
        """Stop the memory scanner."""
        self.running = False
        if self._scanner_task:
            self._scanner_task.cancel()
            try:
                await self._scanner_task
            except asyncio.CancelledError:
                pass
        logger.info("Member memory scanner stopped")

    async def _scanner_loop(self):
        """Main scanner loop - runs every 12 hours."""
        # Wait a bit before first scan to let things initialize
        await asyncio.sleep(60)

        while self.running:
            try:
                await self._scan_all_groups()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory scanner: {e}")

            # Wait for next scan interval
            await asyncio.sleep(SCAN_INTERVAL_HOURS * 3600)

    async def _scan_all_groups(self):
        """Scan all active groups for memory updates."""
        from signal_bot.models import db, GroupConnection, Bot, BotGroupAssignment, MemoryScanState

        logger.info("Starting memory scan for all groups...")

        with _flask_app.app_context():
            # Get all active groups that have a bot with web search enabled
            groups = GroupConnection.query.filter_by(enabled=True).all()

            for group in groups:
                # Check if any bot in this group has web search (needed for context)
                assignments = BotGroupAssignment.query.filter_by(group_id=group.id).all()
                has_capable_bot = False
                bot_for_scan = None

                for assignment in assignments:
                    bot = Bot.query.get(assignment.bot_id)
                    if bot and bot.enabled:
                        has_capable_bot = True
                        bot_for_scan = bot
                        break

                if not has_capable_bot:
                    continue

                # Check if we need to scan (12 hours since last scan)
                scan_state = MemoryScanState.query.get(group.id)
                if scan_state and scan_state.last_scan_at:
                    time_since_scan = datetime.utcnow() - scan_state.last_scan_at
                    if time_since_scan < timedelta(hours=SCAN_INTERVAL_HOURS):
                        logger.debug(f"Skipping {group.name} - scanned {time_since_scan.total_seconds()/3600:.1f}h ago")
                        continue

                # Perform the scan
                await self._scan_group(group.id, group.name, bot_for_scan)

                # Update scan state
                if not scan_state:
                    scan_state = MemoryScanState(group_id=group.id)
                    db.session.add(scan_state)

                scan_state.last_scan_at = datetime.utcnow()
                db.session.commit()

        logger.info("Memory scan complete for all groups")

    async def _scan_group(self, group_id: str, group_name: str, bot: 'Bot'):
        """Scan a specific group and update member memories."""
        from signal_bot.models import db, MessageLog, GroupMemberMemory

        logger.info(f"Scanning group: {group_name}")

        with _flask_app.app_context():
            # Get last 100 messages
            messages = MessageLog.query.filter_by(group_id=group_id).order_by(
                MessageLog.timestamp.desc()
            ).limit(MESSAGES_TO_SCAN).all()

            if not messages:
                logger.debug(f"No messages to scan in {group_name}")
                return

            # Reverse to get chronological order
            messages = list(reversed(messages))

            # Get current memory state
            current_memories = GroupMemberMemory.query.filter_by(group_id=group_id).all()

            # Build context for AI analysis
            memory_updates = await self._analyze_messages_for_memories(
                messages, current_memories, group_name, bot
            )

            if memory_updates:
                self._apply_memory_updates(group_id, memory_updates)

    # JSON Schema for memory scan results
    MEMORY_SCAN_SCHEMA = {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["set", "update", "delete"],
                            "description": "The operation to perform"
                        },
                        "member_name": {
                            "type": "string",
                            "description": "Name of the group member"
                        },
                        "member_id": {
                            "type": ["string", "null"],
                            "description": "Signal UUID if known, null otherwise"
                        },
                        "slot_type": {
                            "type": "string",
                            "enum": ["interests", "media_prefs", "life_events", "work_info",
                                     "social_notes", "response_prefs", "home_location", "travel_location"],
                            "description": "The memory slot type"
                        },
                        "content": {
                            "type": "string",
                            "description": "The memory content"
                        },
                        "valid_from": {
                            "type": ["string", "null"],
                            "description": "Start date YYYY-MM-DD or null"
                        },
                        "valid_until": {
                            "type": ["string", "null"],
                            "description": "End date YYYY-MM-DD or null"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Brief explanation for the update"
                        }
                    },
                    "required": ["operation", "member_name", "slot_type"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["updates"],
        "additionalProperties": False
    }

    async def _analyze_messages_for_memories(
        self,
        messages: list,
        current_memories: list,
        group_name: str,
        bot: 'Bot'
    ) -> list[dict]:
        """Use AI to analyze messages and propose memory updates using structured outputs."""
        try:
            from shared_utils import call_openrouter_api_structured
            from config import AI_MODELS
        except ImportError as e:
            logger.error(f"Failed to import for memory scan: {e}")
            return []

        # Format messages for analysis
        message_text = "\n".join([
            f"[{msg.timestamp.strftime('%Y-%m-%d %H:%M')}] {msg.sender_name}: {msg.content}"
            for msg in messages
        ])

        # Format current memories
        memories_by_member = {}
        for mem in current_memories:
            if mem.member_name not in memories_by_member:
                memories_by_member[mem.member_name] = {}
            validity = ""
            if mem.valid_from or mem.valid_until:
                validity = f" (valid: {mem.valid_from} to {mem.valid_until})"
            memories_by_member[mem.member_name][mem.slot_type] = mem.content + validity

        current_memories_text = json.dumps(memories_by_member, indent=2) if memories_by_member else "No existing memories"

        # Build the analysis prompt
        system_prompt = """You are a memory manager for a group chat AI assistant. Analyze recent messages and extract important information about group members.

Each member can have up to 8 memory slots:

LOCATION SLOTS:
- home_location: Where they live permanently
- travel_location: Where they're traveling now (include dates if mentioned)

SEMANTIC SLOTS:
- interests: Hobbies, concerts, sports teams, music artists, activities they enjoy
- media_prefs: Shows, movies, podcasts, games, books they mention or recommend
- life_events: Wedding dates, birthdays, anniversaries, graduations, major milestones
- work_info: Job title, company, work schedule, professional background
- social_notes: Friend connections within the group, relationship dynamics
- response_prefs: How they prefer the bot to respond (length, style, tone)

EXAMPLES OF WHAT TO REMEMBER:
- "Scott is interested in the Jack Johnson concert Aug 2026" -> interests
- "Austin Tyler likes 90s cartoons like Freakazoid" -> media_prefs
- "Bryan prefers succinct, list-style responses" -> response_prefs
- "Joe works as a software engineer" -> work_info
- "Paul's wedding is March 15, 2025" -> life_events

EXAMPLES OF WHAT NOT TO REMEMBER:
- "lol", "nice", "same" - too trivial
- "I'm making coffee" - momentary states
- Bot/AI responses - only store info about humans

Your task:
1. Review messages and identify NEW info worth remembering
2. Identify OUTDATED info to remove (e.g., past travel)
3. Identify info that should be UPDATED

Return updates array. Empty array [] if no updates needed."""

        user_prompt = f"""Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}

Group: {group_name}

=== CURRENT MEMBER MEMORIES ===
{current_memories_text}

=== LAST {len(messages)} MESSAGES ===
{message_text}

Analyze and return memory updates:"""

        try:
            # Use bot's configured model (no fallback - bot must have a model)
            if not bot.model:
                logger.error(f"Bot {bot.name} has no model configured for memory scan")
                return []
            model_id = AI_MODELS.get(bot.model, bot.model)

            # Use structured outputs for guaranteed valid JSON
            result = call_openrouter_api_structured(
                prompt=user_prompt,
                model=model_id,
                system_prompt=system_prompt,
                json_schema=self.MEMORY_SCAN_SCHEMA,
                schema_name="memory_scan"
            )

            if not result:
                return []

            updates = result.get("updates", [])
            if updates:
                logger.info(f"Memory scanner found {len(updates)} updates for {group_name}")
            else:
                logger.debug(f"No memory updates found for {group_name}")

            return updates

        except Exception as e:
            logger.error(f"Error in memory analysis: {e}")
            return []

    def _apply_memory_updates(self, group_id: str, updates: list[dict]):
        """Apply memory updates to the database."""
        from signal_bot.models import db, GroupMemberMemory, ActivityLog

        with _flask_app.app_context():
            for update in updates:
                try:
                    operation = update.get("operation", "set")
                    member_name = update.get("member_name")
                    # Use member_name as fallback ID to avoid unique constraint collisions
                    # when multiple members have member_id='unknown'
                    member_id = update.get("member_id") or member_name or "unknown"
                    slot_type = update.get("slot_type")
                    content = update.get("content")
                    reason = update.get("reason", "")

                    if not member_name or not slot_type:
                        continue

                    if slot_type not in ALL_SLOTS:
                        logger.warning(f"Invalid slot type: {slot_type}")
                        continue

                    # Find existing memory for this slot
                    existing = GroupMemberMemory.query.filter_by(
                        group_id=group_id,
                        member_name=member_name,
                        slot_type=slot_type
                    ).first()

                    if operation == "delete":
                        if existing:
                            db.session.delete(existing)
                            logger.info(f"Deleted memory: {member_name}/{slot_type} - {reason}")

                            # Log activity
                            log = ActivityLog(
                                event_type="memory_deleted",
                                group_id=group_id,
                                description=f"Deleted {slot_type} for {member_name}: {reason}"
                            )
                            db.session.add(log)

                    elif operation in ("set", "update"):
                        if not content:
                            continue

                        # Parse dates if provided
                        valid_from = None
                        valid_until = None
                        if update.get("valid_from"):
                            try:
                                valid_from = datetime.fromisoformat(update["valid_from"])
                            except ValueError:
                                pass
                        if update.get("valid_until"):
                            try:
                                valid_until = datetime.fromisoformat(update["valid_until"])
                            except ValueError:
                                pass

                        if existing:
                            existing.content = content
                            existing.valid_from = valid_from
                            existing.valid_until = valid_until
                            existing.member_id = member_id
                            logger.info(f"Updated memory: {member_name}/{slot_type} = {content[:50]}...")
                        else:
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
                            logger.info(f"Created memory: {member_name}/{slot_type} = {content[:50]}...")

                        # Log activity
                        log = ActivityLog(
                            event_type="memory_updated",
                            group_id=group_id,
                            description=f"Set {slot_type} for {member_name}: {content[:50]}..."
                        )
                        db.session.add(log)

                    # Commit each update individually to avoid cascading failures
                    db.session.commit()

                except Exception as e:
                    logger.error(f"Error applying memory update: {e}")
                    db.session.rollback()  # Rollback failed transaction before continuing
                    continue

    async def force_scan_group(self, group_id: str):
        """Force an immediate scan of a specific group (for testing/admin)."""
        from signal_bot.models import GroupConnection, Bot, BotGroupAssignment

        with _flask_app.app_context():
            group = GroupConnection.query.get(group_id)
            if not group:
                logger.error(f"Group {group_id} not found")
                return

            # Find a capable bot
            assignments = BotGroupAssignment.query.filter_by(group_id=group_id).all()
            bot = None
            for assignment in assignments:
                b = Bot.query.get(assignment.bot_id)
                if b and b.enabled:
                    bot = b
                    break

            if not bot:
                logger.error(f"No enabled bot found for group {group_id}")
                return

            await self._scan_group(group_id, group.name, bot)


def detect_mentioned_members(message_content: str, group_id: str) -> list[str]:
    """
    Detect which group members are mentioned in the message.

    Returns list of member_names that appear to be mentioned.
    """
    from signal_bot.models import GroupMemberMemory

    try:
        with _flask_app.app_context():
            # Get all known member names from this group
            members = GroupMemberMemory.query.filter_by(group_id=group_id).with_entities(
                GroupMemberMemory.member_name
            ).distinct().all()

            member_names = [m.member_name for m in members]
            mentioned = []

            message_lower = message_content.lower()

            for name in member_names:
                name_lower = name.lower()
                # Check for name mention (with word boundaries to avoid false positives)
                if re.search(rf'\b{re.escape(name_lower)}\b', message_lower):
                    mentioned.append(name)
                # Also check for @mention style
                elif f"@{name_lower}" in message_lower:
                    if name not in mentioned:
                        mentioned.append(name)

            return mentioned
    except Exception as e:
        logger.error(f"Error detecting mentioned members: {e}")
        return []


def is_location_relevant(message_content: str, member_memories: list) -> tuple[bool, bool]:
    """
    Determine if location info is relevant to include.

    Args:
        message_content: The message text
        member_memories: List of GroupMemberMemory objects

    Returns:
        Tuple of (should_include_location, is_explicitly_asked)
        - should_include_location: Whether to include location in context
        - is_explicitly_asked: Whether location was explicitly asked about (no need for warning)
    """
    from signal_bot.config_signal import TRAVEL_PROXIMITY_DAYS

    message_lower = message_content.lower()

    # Check for keyword match
    keyword_match = any(kw in message_lower for kw in LOCATION_KEYWORDS)

    if keyword_match:
        return True, True  # Include location, was explicitly relevant

    # Check for upcoming travel (within configured days)
    now = datetime.utcnow()
    for mem in member_memories:
        if mem.slot_type == "travel_location" and mem.valid_from:
            days_until = (mem.valid_from - now).days
            if 0 <= days_until <= TRAVEL_PROXIMITY_DAYS:
                return True, False  # Include due to proximity, but add warning

    return False, False


def format_single_memory(mem) -> str:
    """Format a single memory entry."""
    slot_labels = {
        "response_prefs": "Prefers responses",
        "home_location": "Lives in",
        "travel_location": "Currently traveling",
        "interests": "Interests",
        "media_prefs": "Media preferences",
        "life_events": "Life event",
        "work_info": "Work",
        "social_notes": "Social",
    }

    label = slot_labels.get(mem.slot_type, mem.slot_type)

    # Add date info for travel
    if mem.slot_type == "travel_location":
        date_str = ""
        if mem.valid_from and mem.valid_until:
            date_str = f" ({mem.valid_from.strftime('%b %d')}-{mem.valid_until.strftime('%b %d')})"
        elif mem.valid_until:
            date_str = f" (until {mem.valid_until.strftime('%b %d')})"
        return f"- {label}: {mem.content}{date_str}"

    return f"- {label}: {mem.content}"


def format_member_memories_for_context(
    group_id: str,
    current_speaker_name: str = "",
    current_speaker_id: str = "",
    message_content: str = ""
) -> str:
    """
    Format member memories prioritized for the current conversation context.

    Args:
        group_id: The group's ID
        current_speaker_name: Name of person who sent the message
        current_speaker_id: Signal UUID of speaker (optional)
        message_content: The message text (for mentioned member detection)

    Returns:
        Formatted string with tiered memory inclusion:
        - Current speaker: Full context (response_prefs always, location when relevant)
        - Mentioned members: Full context
        - Others: Omitted
    """
    from signal_bot.models import GroupMemberMemory

    try:
        with _flask_app.app_context():
            memories = GroupMemberMemory.query.filter_by(group_id=group_id).all()

            if not memories:
                return ""

            now = datetime.utcnow()

            # Group by member, filtering expired travel
            by_member = {}
            for mem in memories:
                # Skip expired travel locations
                if mem.slot_type == "travel_location" and mem.valid_until:
                    if mem.valid_until < now:
                        continue

                if mem.member_name not in by_member:
                    by_member[mem.member_name] = []
                by_member[mem.member_name].append(mem)

            if not by_member:
                return ""

            # Detect mentioned members
            mentioned_members = detect_mentioned_members(message_content, group_id) if message_content else []

            # Check location relevance based on current speaker's memories
            speaker_memories = by_member.get(current_speaker_name, [])
            include_location, location_explicit = is_location_relevant(message_content, speaker_memories)

            output_lines = []

            # === CURRENT SPEAKER SECTION ===
            if current_speaker_name and current_speaker_name in by_member:
                output_lines.append(f"\n=== WHAT I KNOW ABOUT {current_speaker_name.upper()} (CURRENT SPEAKER) ===")

                for mem in by_member[current_speaker_name]:
                    # Tier 1: Always include response_prefs
                    if mem.slot_type in TIER_ALWAYS:
                        output_lines.append(format_single_memory(mem))

                    # Tier 2: Contextual - always include for speaker
                    elif mem.slot_type in TIER_CONTEXTUAL:
                        output_lines.append(format_single_memory(mem))

                    # Tier 3: Situational - location only when relevant
                    elif mem.slot_type in TIER_SITUATIONAL:
                        if include_location:
                            output_lines.append(format_single_memory(mem))

            # === MENTIONED MEMBERS SECTION ===
            for mentioned_name in mentioned_members:
                if mentioned_name == current_speaker_name:
                    continue  # Already covered
                if mentioned_name not in by_member:
                    continue

                output_lines.append(f"\n=== {mentioned_name.upper()} (MENTIONED IN MESSAGE) ===")

                for mem in by_member[mentioned_name]:
                    # Include all tiers for mentioned members
                    output_lines.append(format_single_memory(mem))

            # Add location instruction if location was included but not explicitly asked
            if include_location and not location_explicit:
                output_lines.append(f"\n{LOCATION_INSTRUCTION}")

            # Note about omitted members (if any)
            included_count = 1 if current_speaker_name in by_member else 0
            included_count += len([m for m in mentioned_members if m in by_member and m != current_speaker_name])
            omitted_count = len(by_member) - included_count

            if omitted_count > 0:
                output_lines.append(f"\n[{omitted_count} other group member(s) - context available if mentioned]")

            return "\n".join(output_lines) if output_lines else ""

    except Exception as e:
        logger.error(f"Error formatting member memories: {e}")
        return ""


# Global scanner instance
_scanner: Optional[MemberMemoryScanner] = None


def get_memory_scanner() -> MemberMemoryScanner:
    """Get the global memory scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = MemberMemoryScanner()
    return _scanner
