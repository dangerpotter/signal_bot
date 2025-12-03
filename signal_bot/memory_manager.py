"""Memory management for Signal bot conversations."""

import random
from datetime import datetime
from typing import Optional

from signal_bot.models import db, MessageLog, MemorySnippet, GroupConnection
from signal_bot.config_signal import (
    DEFAULT_ROLLING_WINDOW,
    LONG_TERM_SAVE_CHANCE,
    LONG_TERM_RECALL_CHANCE
)


class MemoryManager:
    """Manages conversation context and long-term memories."""

    def __init__(self, group_id: str, rolling_window: int = DEFAULT_ROLLING_WINDOW):
        self.group_id = group_id
        self.rolling_window = rolling_window

    def add_message(
        self,
        sender_name: str,
        content: str,
        is_bot: bool = False,
        bot_id: Optional[str] = None,
        sender_id: Optional[str] = None,
        has_image: bool = False,
        signal_timestamp: Optional[int] = None
    ) -> Optional[MessageLog]:
        """Add a message to the rolling log.

        Args:
            signal_timestamp: Signal's unique message timestamp (milliseconds) for deduplication.
                            If provided and a message with this timestamp already exists,
                            the existing message is returned instead of creating a duplicate.
        """
        # Deduplication: skip if this exact message already exists (by Signal timestamp)
        if signal_timestamp:
            existing = MessageLog.query.filter_by(
                group_id=self.group_id,
                signal_timestamp=signal_timestamp
            ).first()
            if existing:
                return existing  # Already logged, skip duplicate

        message = MessageLog(
            group_id=self.group_id,
            sender_name=sender_name,
            sender_id=sender_id,
            content=content,
            is_bot=is_bot,
            bot_id=bot_id,
            has_image=has_image,
            timestamp=datetime.utcnow(),
            signal_timestamp=signal_timestamp
        )
        db.session.add(message)
        db.session.commit()

        # Prune old messages
        self._prune_old_messages()

        return message

    def get_context_messages(self, limit: Optional[int] = None) -> list[dict]:
        """
        Get recent messages for context.

        Returns list of dicts with 'role', 'content', 'name' keys
        suitable for passing to AI APIs.
        """
        limit = limit or self.rolling_window

        messages = MessageLog.query.filter_by(
            group_id=self.group_id
        ).order_by(
            MessageLog.timestamp.desc()
        ).limit(limit).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        context = []
        for msg in messages:
            context.append({
                "role": "assistant" if msg.is_bot else "user",
                "content": msg.content,
                "name": msg.sender_name,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                "sender_id": msg.sender_id,
                "signal_timestamp": msg.signal_timestamp
            })

        return context

    def get_formatted_context(self, limit: Optional[int] = None) -> str:
        """Get context as a formatted string for the AI."""
        messages = self.get_context_messages(limit)

        lines = []
        for msg in messages:
            lines.append(f"{msg['name']}: {msg['content']}")

        return "\n".join(lines)

    def maybe_save_memorable_moment(
        self,
        recent_exchange: str,
        context: Optional[str] = None
    ) -> Optional[MemorySnippet]:
        """
        Possibly save a memorable moment to long-term memory.

        Called after AI responses to potentially capture funny/interesting moments.
        """
        # Roll for chance to save
        if random.randint(1, 100) > LONG_TERM_SAVE_CHANCE:
            return None

        # Don't save if exchange is too short
        if len(recent_exchange) < 50:
            return None

        snippet = MemorySnippet(
            group_id=self.group_id,
            content=recent_exchange,
            context=context,
            timestamp=datetime.utcnow()
        )
        db.session.add(snippet)
        db.session.commit()

        return snippet

    def maybe_get_memory_callback(self) -> Optional[str]:
        """
        Maybe return an old memory to inject into context.

        Returns a formatted string like "Earlier in this chat, someone said..."
        """
        # Roll for chance to recall
        if random.randint(1, 100) > LONG_TERM_RECALL_CHANCE:
            return None

        # Get a random memory, preferring less-referenced ones
        memories = MemorySnippet.query.filter_by(
            group_id=self.group_id
        ).order_by(
            MemorySnippet.times_referenced.asc()
        ).limit(10).all()

        if not memories:
            return None

        # Pick a random one from the least-referenced
        memory = random.choice(memories)

        # Update reference count
        memory.times_referenced += 1
        db.session.commit()

        # Format the callback
        callback_intros = [
            "Remember when",
            "Earlier in this chat",
            "This reminds me of when",
            "Throwback to when",
            "Speaking of which, remember",
            "Wait this is giving me flashbacks to",
        ]

        intro = random.choice(callback_intros)
        return f"[{intro}: {memory.content}]"

    def _prune_old_messages(self):
        """Remove messages beyond the rolling window."""
        # Count messages for this group
        count = MessageLog.query.filter_by(group_id=self.group_id).count()

        if count > self.rolling_window * 2:  # Prune when we have 2x the window
            # Get IDs of messages to keep
            keep_messages = MessageLog.query.filter_by(
                group_id=self.group_id
            ).order_by(
                MessageLog.timestamp.desc()
            ).limit(self.rolling_window).all()

            keep_ids = {m.id for m in keep_messages}

            # Delete old messages
            MessageLog.query.filter(
                MessageLog.group_id == self.group_id,
                ~MessageLog.id.in_(keep_ids)
            ).delete(synchronize_session=False)

            db.session.commit()

    def clear_context(self):
        """Clear all messages for this group (but keep long-term memories)."""
        MessageLog.query.filter_by(group_id=self.group_id).delete()
        db.session.commit()

    def clear_all_memories(self):
        """Clear everything including long-term memories."""
        MessageLog.query.filter_by(group_id=self.group_id).delete()
        MemorySnippet.query.filter_by(group_id=self.group_id).delete()
        db.session.commit()


def get_memory_manager(group_id: str) -> MemoryManager:
    """Factory function to get a memory manager for a group."""
    return MemoryManager(group_id)
