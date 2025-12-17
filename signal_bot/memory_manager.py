"""Memory management for Signal bot conversations."""

import logging
from datetime import datetime
from typing import Optional

from signal_bot.models import db, MessageLog
from signal_bot.config_signal import DEFAULT_ROLLING_WINDOW

logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages conversation context (rolling message window)."""

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
        signal_timestamp: Optional[int] = None,
        image_data: Optional[str] = None,
        image_media_type: Optional[str] = None
    ) -> Optional[MessageLog]:
        """Add a message to the rolling log.

        Args:
            signal_timestamp: Signal's unique message timestamp (milliseconds) for deduplication.
                            If provided and a message with this timestamp already exists,
                            the existing message is returned instead of creating a duplicate.
            image_data: Base64 encoded image data (used when chat_log is disabled as fallback)
            image_media_type: MIME type of the image, e.g., "image/jpeg"
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
            image_data=image_data,
            image_media_type=image_media_type,
            timestamp=datetime.utcnow(),
            signal_timestamp=signal_timestamp
        )
        db.session.add(message)
        db.session.commit()

        # Prune old messages
        self._prune_old_messages()

        return message

    def get_context_messages(self, limit: Optional[int] = None, include_images: bool = True, max_image_messages: int = 3) -> list[dict]:
        """
        Get recent messages for context.

        Returns list of dicts with 'role', 'content', 'name' keys
        suitable for passing to AI APIs.

        Args:
            limit: Maximum number of messages to return
            include_images: If True, include image data in structured content format
                           when available (from MessageLog or ChatLog)
            max_image_messages: Maximum number of recent messages to include images for.
                               Older messages with images will have text only (to reduce tokens).

        Note: Content can be either a string (text only) or a list (structured content
        with text and images) when include_images=True and image data is available.
        """
        from signal_bot.models import ChatLog  # Import here to avoid circular

        limit = limit or self.rolling_window

        messages = MessageLog.query.filter_by(
            group_id=self.group_id
        ).order_by(
            MessageLog.timestamp.desc()
        ).limit(limit).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        # First pass: identify which messages should include images (only last N with images)
        # Process from newest to oldest to find which indices should include images
        image_message_indices = set()
        if include_images:
            images_included = 0
            for i in range(len(messages) - 1, -1, -1):  # Iterate newest to oldest
                if messages[i].has_image and images_included < max_image_messages:
                    image_message_indices.add(i)
                    images_included += 1

        context = []
        for i, msg in enumerate(messages):
            content = msg.content
            image_found = False

            # Only include image if this message is in the allowed set
            should_include_image = i in image_message_indices

            # Check for image data if message has_image flag and images requested for this message
            if msg.has_image and should_include_image:
                # Lazy import to avoid circular dependency
                from signal_bot.bot_manager import compress_image_for_api

                # Priority 1: Check MessageLog directly (fallback storage when chat_log disabled)
                if msg.image_data and msg.image_media_type:
                    # Compress if needed to stay under API limits
                    compressed_data, final_media_type = compress_image_for_api(
                        msg.image_data, msg.image_media_type
                    )
                    content = [
                        {"type": "text", "text": msg.content},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": final_media_type,
                                "data": compressed_data
                            }
                        }
                    ]
                    image_found = True

                # Priority 2: Look up from ChatLog (primary storage when chat_log enabled)
                if not image_found and msg.signal_timestamp:
                    chat_log = ChatLog.query.filter_by(
                        signal_timestamp=msg.signal_timestamp
                    ).first()
                    if chat_log and chat_log.image_data and chat_log.image_media_type:
                        # Compress if needed to stay under API limits
                        compressed_data, final_media_type = compress_image_for_api(
                            chat_log.image_data, chat_log.image_media_type
                        )
                        content = [
                            {"type": "text", "text": msg.content},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": final_media_type,
                                    "data": compressed_data
                                }
                            }
                        ]
                # If neither has image data, content stays as text (graceful degradation)

            context.append({
                "role": "assistant" if msg.is_bot else "user",
                "content": content,
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
        """Clear all messages for this group."""
        MessageLog.query.filter_by(group_id=self.group_id).delete()
        db.session.commit()


def get_memory_manager(group_id: str) -> MemoryManager:
    """Factory function to get a memory manager for a group."""
    return MemoryManager(group_id)
