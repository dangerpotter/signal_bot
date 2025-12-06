"""
Base classes and utilities for tool executors.

Contains shared state management and utility functions.
"""

import json
import logging
from typing import Callable, Optional, Union

from tool_schemas import ALL_META_CATEGORIES, FINANCE_CATEGORIES, SHEETS_CATEGORIES

logger = logging.getLogger(__name__)


class SignalToolExecutorBase:
    """
    Base class for Signal bot tool execution.
    Contains shared state and utility methods.
    """

    def __init__(
        self,
        bot_data: dict,
        group_id: str,
        send_image_callback: Optional[Callable[[str], None]] = None,
        send_reaction_callback: Optional[Callable[[str, int, str], None]] = None,
        reaction_metadata: Optional[list[dict]] = None,
        max_reactions: int = 3
    ):
        """
        Args:
            bot_data: Bot configuration dict
            group_id: The Signal group ID
            send_image_callback: Optional callback to send the generated image
            send_reaction_callback: Optional callback to send emoji reactions (sender_id, timestamp, emoji)
            reaction_metadata: List of dicts with message index, sender_id, and signal_timestamp
            max_reactions: Maximum reactions allowed per response
        """
        self.bot_data = bot_data
        self.group_id = group_id
        self.send_image_callback = send_image_callback
        self.send_reaction_callback = send_reaction_callback
        self.reaction_metadata = reaction_metadata or []
        self.max_reactions = max_reactions
        self.reactions_sent = 0  # Track reactions sent in this response
        self.sender_name = None  # Set by message handler for sheet attribution

        # Two-phase meta-tool expansion state
        self.expansion_requested = False
        self.expanded_categories = {}  # {"finance": "finance_quotes", "sheets": "sheets_core"}
        self.last_meta_intent = None  # Track intent from the most recent meta-tool call

    def _sheets_enabled(self) -> bool:
        """Check if Google Sheets is enabled for this bot."""
        return bool(self.bot_data.get('google_sheets_enabled') and self.bot_data.get('google_connected'))

    def _calendar_enabled(self) -> bool:
        """Check if Google Calendar is enabled for this bot."""
        return bool(self.bot_data.get('google_calendar_enabled') and self.bot_data.get('google_connected'))

    def _handle_meta_tool(self, function_name: str, arguments: dict) -> Optional[dict]:
        """
        Handle two-phase meta-tool expansion.

        Returns:
            Expansion signal dict if this is a meta-tool, None otherwise.
        """
        if function_name not in ALL_META_CATEGORIES:
            return None

        self.expansion_requested = True
        # Track which group this meta-tool belongs to (use sets to accumulate multiple categories)
        if function_name in FINANCE_CATEGORIES:
            if "finance" not in self.expanded_categories:
                self.expanded_categories["finance"] = set()
            self.expanded_categories["finance"].add(function_name)
        elif function_name in SHEETS_CATEGORIES:
            if "sheets" not in self.expanded_categories:
                self.expanded_categories["sheets"] = set()
            self.expanded_categories["sheets"].add(function_name)

        intent = arguments.get("intent", "")
        self.last_meta_intent = intent  # Store for context in retry
        available_tools = ALL_META_CATEGORIES[function_name]["sub_tools"]
        logger.info(f"Meta-tool expansion requested: {function_name} (intent: {intent})")

        return {
            "success": True,
            "expansion_needed": True,
            "category": function_name,
            "intent": intent,
            "available_tools": available_tools,
            "message": f"Expanding {function_name}. Available tools: {', '.join(available_tools)}"
        }


def create_tool_executor_callback(executor) -> Callable[[str, dict], dict]:
    """
    Create a callback function for use with call_openrouter_api.

    Args:
        executor: The ToolExecutor instance

    Returns:
        A callback function that takes (function_name, arguments) and returns a result dict
    """
    return executor.execute


def process_tool_calls(
    tool_calls: list,
    executor
) -> list[dict]:
    """
    Process multiple tool calls and return their results.

    Args:
        tool_calls: List of tool_call objects from the API response
        executor: The executor to use

    Returns:
        List of tool result dicts with 'tool_call_id', 'role', and 'content'
    """
    results = []

    for tool_call in tool_calls:
        try:
            function_name = tool_call.get('function', {}).get('name', '')
            arguments_str = tool_call.get('function', {}).get('arguments', '{}')
            tool_call_id = tool_call.get('id', '')

            # Parse arguments
            try:
                # Handle empty string case
                if isinstance(arguments_str, str) and arguments_str.strip() == '':
                    arguments = {}
                else:
                    arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            except json.JSONDecodeError:
                arguments = {}

            # Execute the tool
            result = executor.execute(function_name, arguments)

            # Format for API
            results.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result)
            })

        except Exception as e:
            logger.error(f"Error processing tool call: {e}")
            results.append({
                "role": "tool",
                "tool_call_id": tool_call.get('id', ''),
                "content": json.dumps({"success": False, "message": f"Processing error: {str(e)}"})
            })

    return results
