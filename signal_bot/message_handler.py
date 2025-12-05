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
from signal_bot.member_memory_scanner import (
    format_member_memories_for_context,
    set_flask_app as set_scanner_flask_app
)
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
    # Also set for member memory scanner module
    set_scanner_flask_app(app)


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
        send_callback: Callable,
        send_image_callback: Optional[Callable[[str], None]] = None,
        is_mentioned: bool = False,
        message_timestamp: Optional[int] = None,
        send_typing_callback: Optional[Callable] = None,
        stop_typing_callback: Optional[Callable] = None,
        incoming_images: Optional[list[dict]] = None,
        send_reaction_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Optional[str]:
        """
        Handle an incoming message and potentially generate a response.

        Args:
            group_id: Signal group ID
            sender_name: Name of the message sender
            sender_id: Signal UUID of sender
            message_text: The message content
            bot_data: Bot configuration as dict (id, name, model, system_prompt, etc.)
            send_callback: Function to send text response (text, quote_timestamp, quote_author, mentions, text_styles)
            send_image_callback: Function to call to send image
            is_mentioned: Whether the bot was @mentioned (Signal native mention)
            message_timestamp: Signal timestamp of the triggering message (for quotes/replies)
            send_typing_callback: Function to start typing indicator
            stop_typing_callback: Function to stop typing indicator
            incoming_images: List of base64-encoded images from the message
            send_reaction_callback: Function to send emoji reactions (sender_id, timestamp, emoji)

        Returns:
            The response text if one was generated, None otherwise
        """
        memory = self.get_memory_manager(group_id)

        # Log incoming message (with Signal timestamp for deduplication)
        memory.add_message(
            sender_name=sender_name,
            content=message_text or "[Image]",
            is_bot=False,
            sender_id=sender_id,
            has_image=bool(incoming_images),
            signal_timestamp=message_timestamp
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

        # Start typing indicator if enabled
        typing_enabled = bot_data.get('typing_enabled', True)
        if typing_enabled and send_typing_callback:
            send_typing_callback()

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
            memory_confirmation=memory_confirmation,
            send_image_callback=send_image_callback,
            incoming_images=incoming_images,
            send_reaction_callback=send_reaction_callback
        )

        # Stop typing indicator
        if typing_enabled and stop_typing_callback:
            stop_typing_callback()

        if response:
            # Parse for commands
            cleaned_response, commands = self._parse_commands(response)

            # Parse text for styling (markdown-like -> Signal styles)
            styled_text, text_styles = self._parse_text_styles(cleaned_response)

            # Strip bot name prefix if AI included it (e.g., "AI-Labo: Hello" -> "Hello")
            bot_name = bot_data.get('name', '')
            if bot_name and styled_text.startswith(f"{bot_name}: "):
                styled_text = styled_text[len(f"{bot_name}: "):]
            elif bot_name and styled_text.startswith(f"{bot_name}:"):
                styled_text = styled_text[len(f"{bot_name}:"):]

            # Determine if we should quote/reply to the original message
            # - Always quote if triggered by mention or direct command
            # - For random responses, use the random_chance_percent
            should_quote = False
            if message_timestamp and sender_id:
                if is_mentioned or reason in ("native_mention", "mention", "command"):
                    should_quote = True
                elif reason == "random":
                    import random
                    # Use half the random_chance_percent as quote probability for random responses
                    quote_chance = bot_data.get('random_chance_percent', 15) / 2
                    should_quote = random.random() * 100 < quote_chance

            # Send the text response with optional quote and styling
            if styled_text.strip():
                send_callback(
                    styled_text,
                    message_timestamp if should_quote else None,
                    sender_id if should_quote else None,
                    None,  # mentions - could be enhanced later
                    text_styles if text_styles else None
                )

                # Log bot's response
                memory.add_message(
                    sender_name=bot_data['name'],
                    content=styled_text,
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
            if styled_text:
                recent_exchange = f"{sender_name}: {message_text}\n{bot_data['name']}: {styled_text}"
                memory.maybe_save_memorable_moment(recent_exchange)

            return styled_text

        return None

    async def _generate_response(
        self,
        bot_data: dict,
        memory: MemoryManager,
        trigger_message: str,
        group_id: str,
        sender_name: str = "",
        sender_id: str = "",
        memory_confirmation: Optional[str] = None,
        send_image_callback: Optional[Callable[[str], None]] = None,
        incoming_images: Optional[list[dict]] = None,
        send_reaction_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Optional[str]:
        """Generate an AI response using the configured model."""
        try:
            # Import shared_utils for API calls
            from shared_utils import call_openrouter_api
            from config import AI_MODELS, OPENROUTER_TOOL_CALLING_ENABLED
            from tool_schemas import get_tools_for_context, model_supports_tools
            from tool_executor import SignalToolExecutor
        except ImportError as e:
            logger.error(f"Failed to import shared_utils: {e}")
            return None

        # Build context (use bot's context_window setting)
        context_window = bot_data.get('context_window', 25)
        context_messages = memory.get_context_messages(limit=context_window)

        # DEBUG: Log context before filtering
        logger.info(f"[DEBUG] Context retrieved: {len(context_messages)} messages, trigger: '{trigger_message[:50] if trigger_message else 'None'}...'")
        if context_messages:
            last_content = context_messages[-1].get('content', '')
            logger.info(f"[DEBUG] Last context msg: '{last_content[:50]}...'")
            logger.info(f"[DEBUG] Match check: last==trigger? {last_content == trigger_message}")

        # Exclude the current message from context - it was already logged to DB
        # but will be sent separately as the prompt (to avoid duplication)
        if context_messages and context_messages[-1].get('content') == trigger_message:
            logger.info(f"[DEBUG] Excluding last message from context (matches trigger)")
            context_messages = context_messages[:-1]

        # DEBUG: Log final context
        logger.info(f"[DEBUG] Final context: {len(context_messages)} messages")

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
            message_content=trigger_message,
            member_memory_model=bot_data.get('member_memory_model')
        )
        if member_memories:
            logger.info(f"Injecting member memories for {sender_name}:\n{member_memories[:500]}...")
            system_prompt += f"\n{member_memories}"

        # Inject memory confirmation instruction if a memory was just saved
        if memory_confirmation:
            system_prompt += f"\n\n{memory_confirmation}"

        # Get model ID
        model_id = AI_MODELS.get(bot_data['model'], bot_data['model'])

        # Check if reaction tool is enabled (needed for context formatting)
        reaction_enabled = bot_data.get('reaction_tool_enabled', False)

        # Format conversation for API with message indices for reaction tool
        formatted_messages = []
        reaction_metadata = []  # Stores metadata for messages that can be reacted to

        for idx, msg in enumerate(context_messages):
            role = msg["role"]
            # Format with index prefix when reaction tool is enabled
            if reaction_enabled:
                if role == "user" and msg.get("name"):
                    content = f"[{idx}] {msg['name']}: {msg['content']}"
                else:
                    content = f"[{idx}] {msg['content']}"
            else:
                # Original formatting without indices
                if role == "user" and msg.get("name"):
                    content = f"{msg['name']}: {msg['content']}"
                else:
                    content = msg["content"]
            formatted_messages.append({"role": role, "content": content})

            # Build reaction metadata for user messages with valid Signal metadata
            if role == "user" and msg.get("signal_timestamp") and msg.get("sender_id"):
                reaction_metadata.append({
                    "index": idx,
                    "sender_id": msg["sender_id"],
                    "signal_timestamp": msg["signal_timestamp"]
                })

        # DEBUG: Log ALL messages being sent to API
        logger.info(f"[DEBUG] ===== CONTEXT DUMP ({len(formatted_messages)} messages) =====")
        for i, msg in enumerate(formatted_messages):
            content_preview = msg['content'][:60].replace('\n', ' ') if msg.get('content') else 'None'
            logger.info(f"[DEBUG] [{i}] {msg['role']}: {content_preview}...")
        logger.info(f"[DEBUG] ===== PROMPT: {trigger_message[:60] if trigger_message else 'None'}... =====")

        try:
            # Determine if we should use native tool calling
            use_tools = None
            tool_executor = None

            # Check if any tools are enabled (image generation, weather, finance, time, wikipedia, reaction, or sheets)
            image_enabled = bot_data.get('image_generation_enabled', False)
            weather_enabled = bot_data.get('weather_enabled', False)
            finance_enabled = bot_data.get('finance_enabled', False)
            time_enabled = bot_data.get('time_enabled', False)
            wikipedia_enabled = bot_data.get('wikipedia_enabled', False)
            # Sheets requires both enabled AND connected to Google
            sheets_enabled = bot_data.get('google_sheets_enabled', False) and bot_data.get('google_connected', False)
            # Member memory tools
            member_memory_tools_enabled = bot_data.get('member_memory_tools_enabled', False)
            # reaction_enabled already set above for context formatting
            any_tools_enabled = image_enabled or weather_enabled or finance_enabled or time_enabled or wikipedia_enabled or reaction_enabled or sheets_enabled or member_memory_tools_enabled

            # Build prompt - include images if present
            if incoming_images:
                # Create structured content with text and images
                prompt_content = [{"type": "text", "text": trigger_message or "What do you see in this image?"}]
                for img in incoming_images:
                    prompt_content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["media_type"],
                            "data": img["data"]
                        }
                    })
                logger.info(f"Built structured prompt with {len(incoming_images)} image(s)")
            else:
                prompt_content = trigger_message

            # Two-phase meta-tool expansion loop
            expanded_categories = {}  # Track expanded categories: {"finance": "finance_quotes", "sheets": "sheets_core"}
            max_expansions = 3  # Allow finance + sheets + one retry

            for expansion_iteration in range(max_expansions + 1):
                if (OPENROUTER_TOOL_CALLING_ENABLED and
                    any_tools_enabled and
                    model_supports_tools(model_id)):

                    use_tools = get_tools_for_context(
                        context="signal",
                        image_enabled=image_enabled,
                        weather_enabled=weather_enabled,
                        finance_enabled=finance_enabled,
                        time_enabled=time_enabled,
                        wikipedia_enabled=wikipedia_enabled,
                        reaction_enabled=reaction_enabled,
                        sheets_enabled=sheets_enabled,
                        member_memory_enabled=member_memory_tools_enabled,
                        expanded_categories=expanded_categories
                    )
                    signal_executor = SignalToolExecutor(
                        bot_data=bot_data,
                        group_id=group_id,
                        send_image_callback=send_image_callback,
                        send_reaction_callback=send_reaction_callback,
                        reaction_metadata=reaction_metadata,
                        max_reactions=bot_data.get('max_reactions_per_response', 3)
                    )
                    # Set sender name for sheet attribution
                    signal_executor.sender_name = sender_name
                    tool_executor = signal_executor.execute
                    tools_list = [t['function']['name'] for t in use_tools]
                    logger.info(f"Tool calling enabled for {bot_data.get('name')} (expansion {expansion_iteration}): {tools_list}")
                else:
                    use_tools = None
                    tool_executor = None

                # Call the AI API
                response = call_openrouter_api(
                    prompt=prompt_content,
                    conversation_history=formatted_messages,
                    model=model_id,
                    system_prompt=system_prompt,
                    stream_callback=None,  # No streaming for Signal
                    web_search=bot_data.get('web_search_enabled', False),
                    tools=use_tools,
                    tool_executor=tool_executor
                )

                # Check if meta-tool expansion was requested
                if (signal_executor and
                    signal_executor.expansion_requested and
                    signal_executor.expanded_categories):
                    # Merge newly expanded categories
                    expanded_categories.update(signal_executor.expanded_categories)
                    logger.info(f"Meta-tool expansion triggered, expanded categories: {expanded_categories}")
                    # Continue loop with expanded tools
                    continue

                # No expansion needed, return response
                return response

            # Max iterations reached (shouldn't normally happen)
            logger.warning(f"Max tool expansion iterations ({max_expansions}) reached")
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

    def _parse_text_styles(self, text: str) -> tuple[str, list[dict]]:
        """
        Parse markdown-like syntax and convert to Signal text styles.

        Supports:
        - **bold** -> BOLD
        - *italic* or _italic_ -> ITALIC
        - `code` -> MONOSPACE
        - ~~strikethrough~~ -> STRIKETHROUGH
        - ||spoiler|| -> SPOILER

        Returns:
            Tuple of (cleaned_text, list of style dicts with start, length, style)
        """
        import re

        styles = []
        result = text

        # Process patterns in order of priority (longer markers first)
        patterns = [
            (r'\*\*(.+?)\*\*', 'BOLD', 2),          # **bold**
            (r'~~(.+?)~~', 'STRIKETHROUGH', 2),     # ~~strike~~
            (r'\|\|(.+?)\|\|', 'SPOILER', 2),       # ||spoiler||
            (r'`(.+?)`', 'MONOSPACE', 1),           # `code`
            (r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', 'ITALIC', 1),  # *italic* (not **)
            (r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', 'ITALIC', 1),        # _italic_ (not __)
        ]

        # Track processed ranges to avoid double-processing
        processed_ranges = []

        for pattern, style_name, marker_len in patterns:
            # Find all matches
            for match in re.finditer(pattern, result):
                full_match = match.group(0)
                inner_text = match.group(1)
                start = match.start()

                # Skip if this range overlaps with already processed
                end = start + len(full_match)
                overlaps = any(
                    not (end <= ps or start >= pe)
                    for ps, pe in processed_ranges
                )
                if overlaps:
                    continue

                processed_ranges.append((start, end))

        # Now do actual replacement and build styles
        # We need to do this carefully to track positions correctly
        styles = []
        offset = 0
        result_chars = list(text)

        # Sort patterns by their match positions in the original text
        all_matches = []
        for pattern, style_name, marker_len in patterns:
            for match in re.finditer(pattern, text):
                all_matches.append({
                    'start': match.start(),
                    'end': match.end(),
                    'inner': match.group(1),
                    'style': style_name,
                    'marker_len': marker_len
                })

        # Sort by start position and remove overlapping matches
        all_matches.sort(key=lambda x: x['start'])
        filtered_matches = []
        last_end = -1
        for m in all_matches:
            if m['start'] >= last_end:
                filtered_matches.append(m)
                last_end = m['end']

        # Build result string and styles
        result = ""
        last_pos = 0
        for m in filtered_matches:
            # Add text before this match
            result += text[last_pos:m['start']]
            # Add the inner text (without markers)
            style_start = len(result)
            result += m['inner']
            style_end = len(result)

            # Record the style
            # Signal uses UTF-16 code units, so we need to calculate correctly
            # For ASCII/BMP characters, len() works, but for emoji we need special handling
            utf16_start = len(result[:style_start].encode('utf-16-le')) // 2
            utf16_length = len(m['inner'].encode('utf-16-le')) // 2

            styles.append({
                'start': utf16_start,
                'length': utf16_length,
                'style': m['style']
            })

            last_pos = m['end']

        # Add remaining text
        result += text[last_pos:]

        return result, styles

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
