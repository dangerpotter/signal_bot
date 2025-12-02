"""Message handling and AI response generation for Signal bot."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Callable

from flask import Flask

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from signal_bot.models import db, Bot, MessageLog, ActivityLog
from signal_bot.memory_manager import MemoryManager, get_memory_manager
from signal_bot.trigger_logic import should_bot_respond, get_response_delay
from signal_bot.member_memory_scanner import format_member_memories_for_context
from signal_bot.realtime_memory import (
    check_and_save_realtime_memory,
    format_memory_confirmation_instruction,
    set_flask_app as set_realtime_flask_app
)

logger = logging.getLogger(__name__)

# Flask app reference for context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app
    # Also set for realtime memory module
    set_realtime_flask_app(app)


class MessageHandler:
    """Handles incoming messages and generates AI responses."""

    def __init__(self):
        self.memory_managers: dict[str, MemoryManager] = {}

    def get_memory_manager(self, group_id: str) -> MemoryManager:
        """Get or create memory manager for a group."""
        if group_id not in self.memory_managers:
            self.memory_managers[group_id] = get_memory_manager(group_id)
        return self.memory_managers[group_id]

    async def handle_incoming_message(
        self,
        group_id: str,
        sender_name: str,
        sender_id: str,
        message_text: str,
        bot_data: dict,
        send_callback: Callable[[str], None],
        send_image_callback: Optional[Callable[[str], None]] = None,
        is_mentioned: bool = False
    ) -> Optional[str]:
        """
        Handle an incoming message and potentially generate a response.

        Args:
            group_id: Signal group ID
            sender_name: Name of the message sender
            sender_id: Signal UUID of sender
            message_text: The message content
            bot_data: Bot configuration as dict (id, name, model, system_prompt, etc.)
            send_callback: Function to call to send text response
            send_image_callback: Function to call to send image
            is_mentioned: Whether the bot was @mentioned (Signal native mention)

        Returns:
            The response text if one was generated, None otherwise
        """
        memory = self.get_memory_manager(group_id)

        # Log incoming message
        memory.add_message(
            sender_name=sender_name,
            content=message_text,
            is_bot=False,
            sender_id=sender_id
        )

        # Check for real-time memory save (e.g., "remember I prefer...")
        memory_result = await check_and_save_realtime_memory(
            message_text=message_text,
            sender_name=sender_name,
            sender_id=sender_id,
            group_id=group_id,
            bot_data=bot_data
        )

        memory_confirmation = None
        if memory_result and memory_result.get('saved'):
            memory_confirmation = format_memory_confirmation_instruction(
                memory_result,
                sender_name
            )

        # Check if bot should respond
        # If natively @mentioned in Signal, always respond
        if is_mentioned:
            should_respond = True
            reason = "native_mention"
        else:
            should_respond, reason = should_bot_respond(
                bot_data=bot_data,
                message_text=message_text,
                sender_name=sender_name
            )

        if not should_respond:
            logger.info(f"Bot {bot_data['name']} not responding: {reason}")
            return None

        logger.info(f"Bot {bot_data['name']} responding (reason: {reason})")

        # Add delay for natural feel
        delay = get_response_delay(bot_data, reason)
        await asyncio.sleep(delay)

        # Generate response
        response = await self._generate_response(
            bot_data=bot_data,
            memory=memory,
            trigger_message=message_text,
            group_id=group_id,
            sender_name=sender_name,
            sender_id=sender_id,
            memory_confirmation=memory_confirmation
        )

        if response:
            # Parse for commands
            cleaned_response, commands = self._parse_commands(response)

            # Send the text response
            if cleaned_response.strip():
                send_callback(cleaned_response)

                # Log bot's response
                memory.add_message(
                    sender_name=bot_data['name'],
                    content=cleaned_response,
                    is_bot=True,
                    bot_id=bot_data['id']
                )

                # Log activity
                self._log_activity(
                    "message_sent",
                    bot_data['id'],
                    group_id,
                    f"{bot_data['name']} replied in group"
                )

            # Handle commands (like !image)
            if commands and send_image_callback:
                await self._execute_commands(
                    commands, bot_data, group_id, send_image_callback
                )

            # Maybe save memorable moment
            if cleaned_response:
                recent_exchange = f"{sender_name}: {message_text}\n{bot_data['name']}: {cleaned_response}"
                memory.maybe_save_memorable_moment(recent_exchange)

            return cleaned_response

        return None

    async def _generate_response(
        self,
        bot_data: dict,
        memory: MemoryManager,
        trigger_message: str,
        group_id: str,
        sender_name: str = "",
        sender_id: str = "",
        memory_confirmation: Optional[str] = None
    ) -> Optional[str]:
        """Generate an AI response using the configured model."""
        try:
            # Import shared_utils for API calls
            from shared_utils import call_openrouter_api
            from config import AI_MODELS
        except ImportError as e:
            logger.error(f"Failed to import shared_utils: {e}")
            return None

        # Build context
        context_messages = memory.get_context_messages()

        # Maybe inject a memory callback
        memory_callback = memory.maybe_get_memory_callback()

        # Build system prompt
        system_prompt = bot_data.get('system_prompt') or self._get_default_system_prompt(bot_data['name'])

        if memory_callback:
            system_prompt += f"\n\n{memory_callback}"

        # Inject member memories (locations, personal info) - now prioritized by speaker
        member_memories = format_member_memories_for_context(
            group_id=group_id,
            current_speaker_name=sender_name,
            current_speaker_id=sender_id,
            message_content=trigger_message
        )
        if member_memories:
            system_prompt += f"\n{member_memories}"

        # Inject memory confirmation instruction if a memory was just saved
        if memory_confirmation:
            system_prompt += f"\n\n{memory_confirmation}"

        # Get model ID
        model_id = AI_MODELS.get(bot_data['model'], bot_data['model'])

        # Format conversation for API
        formatted_messages = []
        for msg in context_messages:
            role = msg["role"]
            content = f"{msg['name']}: {msg['content']}" if msg.get("name") else msg["content"]
            formatted_messages.append({"role": role, "content": content})

        try:
            # Call the AI API
            response = call_openrouter_api(
                prompt=trigger_message,
                conversation_history=formatted_messages,
                model=model_id,
                system_prompt=system_prompt,
                stream_callback=None,  # No streaming for Signal
                web_search=bot_data.get('web_search_enabled', False)
            )

            return response

        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None

    def _parse_commands(self, response: str) -> tuple[str, list[dict]]:
        """Parse commands from the response."""
        try:
            from command_parser import parse_commands
            return parse_commands(response)
        except ImportError:
            # Fallback: simple !image parsing
            import re
            commands = []
            cleaned = response

            # Find !image commands
            image_pattern = r'!image\s+"([^"]+)"'
            matches = re.findall(image_pattern, response)
            for match in matches:
                commands.append({"action": "image", "params": {"prompt": match}})
                cleaned = re.sub(rf'!image\s+"{re.escape(match)}"', '', cleaned)

            return cleaned.strip(), commands

    async def _execute_commands(
        self,
        commands: list,
        bot_data: dict,
        group_id: str,
        send_image_callback: Callable[[str], None]
    ):
        """Execute parsed commands."""
        for cmd in commands:
            # Support both dict and AgentCommand dataclass
            action = cmd.action if hasattr(cmd, 'action') else cmd.get("action")
            params = cmd.params if hasattr(cmd, 'params') else cmd.get("params", {})

            if action == "image" and bot_data.get('image_generation_enabled'):
                prompt = params.get("prompt") if isinstance(params, dict) else params
                await self._execute_image_command(
                    prompt,
                    bot_data,
                    group_id,
                    send_image_callback
                )

    async def _execute_image_command(
        self,
        prompt: str,
        bot_data: dict,
        group_id: str,
        send_image_callback: Callable[[str], None]
    ):
        """Generate and send an image."""
        try:
            from shared_utils import generate_image_from_text
        except ImportError:
            logger.error("Cannot import generate_image_from_text")
            return

        logger.info(f"Bot {bot_data['name']} generating image: {prompt[:50]}...")

        try:
            result = generate_image_from_text(prompt)

            if result and result.get("success"):
                image_path = result.get("image_path")
                if image_path:
                    send_image_callback(image_path)

                    self._log_activity(
                        "image_generated",
                        bot_data['id'],
                        group_id,
                        f"{bot_data['name']} generated image: {prompt[:30]}..."
                    )
            else:
                logger.error(f"Image generation failed: {result}")

        except Exception as e:
            logger.error(f"Image generation error: {e}")

    def _get_default_system_prompt(self, bot_name: str) -> str:
        """Get a default system prompt for a bot."""
        return f"""You are {bot_name}, an AI participating in a Signal group chat with humans and other AIs.

Guidelines:
- Keep responses concise (1-3 sentences usually, unless more detail is needed)
- Be conversational, witty, and engaging
- Match the energy of the chat - if it's casual, be casual
- You can use !image "detailed prompt" to generate images/memes
- Don't be overly formal or robotic
- Feel free to use lowercase, emoji, or casual language when it fits
- Reference previous messages when relevant
- Have opinions and personality - don't be bland"""

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


# Global handler instance
_handler: Optional[MessageHandler] = None


def get_message_handler() -> MessageHandler:
    """Get the global message handler instance."""
    global _handler
    if _handler is None:
        _handler = MessageHandler()
    return _handler
