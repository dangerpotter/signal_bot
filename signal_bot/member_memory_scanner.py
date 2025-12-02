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

    async def _analyze_messages_for_memories(
        self,
        messages: list,
        current_memories: list,
        group_name: str,
        bot: 'Bot'
    ) -> list[dict]:
        """Use AI to analyze messages and propose memory updates."""
        try:
            from shared_utils import call_openrouter_api
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
- "The Chair Company is a great show" (recommendation) -> media_prefs

EXAMPLES OF WHAT NOT TO REMEMBER:
- "lol", "nice", "same" - too trivial
- "I'm making coffee", "heading to lunch" - momentary states
- Bot/AI responses - only store info about humans

Your task:
1. Review messages and identify NEW info worth remembering
2. Identify OUTDATED info to remove (e.g., past travel)
3. Identify info that should be UPDATED

Rules:
- Capture entertainment preferences, upcoming events they're interested in
- Capture communication style preferences explicitly stated
- Capture anything they recommend to others
- Location info valuable for weather/time queries
- Today's date matters for evaluating if travel is current

Output as JSON array:
[
  {
    "operation": "set" | "update" | "delete",
    "member_name": "Name",
    "member_id": null,
    "slot_type": "interests" | "media_prefs" | "life_events" | "work_info" | "social_notes" | "response_prefs" | "home_location" | "travel_location",
    "content": "The memory content",
    "valid_from": "2024-01-15" or null,
    "valid_until": "2024-01-20" or null,
    "reason": "Brief explanation"
  }
]

Return empty array [] if no updates needed.
IMPORTANT: Return ONLY the JSON array, no other text."""

        user_prompt = f"""Today's date: {datetime.utcnow().strftime('%Y-%m-%d')}

Group: {group_name}

=== CURRENT MEMBER MEMORIES ===
{current_memories_text}

=== LAST {len(messages)} MESSAGES ===
{message_text}

Analyze these messages and return memory updates as JSON."""

        try:
            model_id = AI_MODELS.get(bot.model, bot.model)

            response = call_openrouter_api(
                prompt=user_prompt,
                conversation_history=[],
                model=model_id,
                system_prompt=system_prompt,
                stream_callback=None,
                web_search=False  # No need for web search here
            )

            if not response:
                return []

            # Parse the JSON response
            # Try to extract JSON from the response (handle markdown code blocks)
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                updates = json.loads(json_match.group())
                logger.info(f"Memory scanner found {len(updates)} updates for {group_name}")
                return updates
            else:
                logger.debug(f"No memory updates found for {group_name}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse memory updates JSON: {e}")
            return []
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
                    member_id = update.get("member_id") or "unknown"
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

                except Exception as e:
                    logger.error(f"Error applying memory update: {e}")
                    continue

            db.session.commit()

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


def format_member_memories_for_context(group_id: str) -> str:
    """
    Format all member memories for a group into a string for system prompt injection.

    Returns a formatted string like:
    === WHAT I KNOW ABOUT GROUP MEMBERS ===
    AT:
    - Lives in: Denver, CO
    - Currently traveling: Miami (Dec 15-22)
    - Wedding date: March 15, 2025

    Bob:
    - Lives in: Seattle
    """
    from signal_bot.models import GroupMemberMemory
    from datetime import datetime

    try:
        with _flask_app.app_context():
            memories = GroupMemberMemory.query.filter_by(group_id=group_id).all()

            if not memories:
                return ""

            # Group by member
            by_member = {}
            now = datetime.utcnow()

            for mem in memories:
                # Skip expired travel locations
                if mem.slot_type == "travel_location" and mem.valid_until:
                    if mem.valid_until < now:
                        continue

                if mem.member_name not in by_member:
                    by_member[mem.member_name] = []

                # Format the memory based on slot type
                if mem.slot_type == "home_location":
                    by_member[mem.member_name].append(f"- Lives in: {mem.content}")
                elif mem.slot_type == "travel_location":
                    date_str = ""
                    if mem.valid_from and mem.valid_until:
                        date_str = f" ({mem.valid_from.strftime('%b %d')}-{mem.valid_until.strftime('%b %d')})"
                    elif mem.valid_until:
                        date_str = f" (until {mem.valid_until.strftime('%b %d')})"
                    by_member[mem.member_name].append(f"- Currently traveling: {mem.content}{date_str}")
                elif mem.slot_type == "interests":
                    by_member[mem.member_name].append(f"- Interests: {mem.content}")
                elif mem.slot_type == "media_prefs":
                    by_member[mem.member_name].append(f"- Media preferences: {mem.content}")
                elif mem.slot_type == "life_events":
                    by_member[mem.member_name].append(f"- Life event: {mem.content}")
                elif mem.slot_type == "work_info":
                    by_member[mem.member_name].append(f"- Work: {mem.content}")
                elif mem.slot_type == "social_notes":
                    by_member[mem.member_name].append(f"- Social: {mem.content}")
                elif mem.slot_type == "response_prefs":
                    by_member[mem.member_name].append(f"- Prefers responses: {mem.content}")
                else:
                    by_member[mem.member_name].append(f"- {mem.content}")

            if not by_member:
                return ""

            # Build output
            lines = ["\n=== WHAT I KNOW ABOUT GROUP MEMBERS ==="]
            for member, mems in by_member.items():
                lines.append(f"\n{member}:")
                lines.extend(mems)

            return "\n".join(lines)

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
