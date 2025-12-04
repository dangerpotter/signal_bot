"""
Tool executor for bridging OpenRouter tool calls to existing command execution.

Maps structured tool_calls from the API to AgentCommand objects and executes them
using the existing command execution infrastructure.
"""

import json
import logging
from typing import Callable, Optional

from command_parser import AgentCommand

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Executes tool calls for the main GUI app.
    Bridges OpenRouter tool_calls to the ConversationManager's execute_agent_command method.
    """

    def __init__(self, execute_fn: Callable[[AgentCommand, str], tuple[bool, str]], ai_name: str):
        """
        Args:
            execute_fn: The execute_agent_command function from ConversationManager
            ai_name: The AI that is making the tool call (e.g., 'AI-1')
        """
        self.execute_fn = execute_fn
        self.ai_name = ai_name

    def execute(self, function_name: str, arguments: dict) -> dict:
        """
        Execute a tool call and return the result.

        Args:
            function_name: Name of the function to execute (e.g., 'generate_image')
            arguments: Dictionary of function arguments

        Returns:
            Dict with 'success' and 'message' keys
        """
        # Map OpenRouter function names to command_parser action names
        action_map = {
            "generate_image": "image",
            "generate_video": "video",
            "add_ai": "add_ai",
            "remove_ai": "remove_ai",
            "mute_self": "mute_self",
            "list_models": "list_models"
        }

        action = action_map.get(function_name)
        if not action:
            return {"success": False, "message": f"Unknown function: {function_name}"}

        # Map tool arguments to AgentCommand params format
        params = self._map_arguments(action, arguments)

        # Create AgentCommand
        command = AgentCommand(
            action=action,
            params=params,
            raw=f"tool_call:{function_name}"
        )

        # Execute using the provided function
        try:
            success, message = self.execute_fn(command, self.ai_name)
            return {"success": success, "message": message}
        except Exception as e:
            logger.error(f"Error executing tool {function_name}: {e}")
            return {"success": False, "message": f"Execution error: {str(e)}"}

    def _map_arguments(self, action: str, arguments: dict) -> dict:
        """Map tool call arguments to AgentCommand params format."""
        if action == "image":
            return {"prompt": arguments.get("prompt", "")}
        elif action == "video":
            return {"prompt": arguments.get("prompt", "")}
        elif action == "add_ai":
            return {
                "model": arguments.get("model", ""),
                "persona": arguments.get("persona")
            }
        elif action == "remove_ai":
            return {"target": arguments.get("target", "")}
        else:
            return {}


class SignalToolExecutor:
    """
    Executes tool calls for the Signal bot.
    Supports image generation, weather, time, wikipedia, finance, emoji reactions, and Google Sheets.
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

    def execute(self, function_name: str, arguments: dict) -> dict:
        """
        Execute a tool call for Signal bot.

        Args:
            function_name: Name of the function
            arguments: Dictionary of function arguments

        Returns:
            Dict with 'success' and 'message' keys
        """
        if function_name == "get_weather":
            return self._execute_weather(arguments)

        # Time tools
        if function_name == "get_datetime":
            return self._execute_get_datetime(arguments)
        if function_name == "get_unix_timestamp":
            return self._execute_get_unix_timestamp(arguments)

        # Wikipedia tools
        if function_name == "search_wikipedia":
            return self._execute_search_wikipedia(arguments)
        if function_name == "get_wikipedia_article":
            return self._execute_get_wikipedia_article(arguments)
        if function_name == "get_random_wikipedia_article":
            return self._execute_random_wikipedia_article(arguments)

        # Finance tools
        if function_name == "get_stock_quote":
            return self._execute_stock_quote(arguments)
        if function_name == "get_stock_news":
            return self._execute_stock_news(arguments)
        if function_name == "search_stocks":
            return self._execute_search_stocks(arguments)
        if function_name == "get_top_stocks":
            return self._execute_top_stocks(arguments)
        if function_name == "get_price_history":
            return self._execute_price_history(arguments)
        if function_name == "get_options":
            return self._execute_options(arguments)
        if function_name == "get_earnings":
            return self._execute_earnings(arguments)
        if function_name == "get_analyst_ratings":
            return self._execute_analyst_ratings(arguments)
        if function_name == "get_dividends":
            return self._execute_dividends(arguments)
        if function_name == "get_financials":
            return self._execute_financials(arguments)
        if function_name == "get_holders":
            return self._execute_holders(arguments)

        # Reaction tool
        if function_name == "react_to_message":
            return self._execute_react_to_message(arguments)

        # Google Sheets tools
        if function_name == "create_spreadsheet":
            return self._execute_create_spreadsheet(arguments)
        if function_name == "list_spreadsheets":
            return self._execute_list_spreadsheets(arguments)
        if function_name == "read_sheet":
            return self._execute_read_sheet(arguments)
        if function_name == "write_to_sheet":
            return self._execute_write_to_sheet(arguments)
        if function_name == "add_row_to_sheet":
            return self._execute_add_row_to_sheet(arguments)
        if function_name == "search_sheets":
            return self._execute_search_sheets(arguments)

        # Member memory tools
        if function_name == "save_member_memory":
            return self._execute_save_member_memory(arguments)
        if function_name == "get_member_memories":
            return self._execute_get_member_memories(arguments)
        if function_name == "list_group_members":
            return self._execute_list_group_members(arguments)

        if function_name != "generate_image":
            return {"success": False, "message": f"Unsupported function: {function_name}"}

        if not self.bot_data.get('image_generation_enabled'):
            return {"success": False, "message": "Image generation disabled for this bot"}

        prompt = arguments.get("prompt", "")
        if not prompt:
            return {"success": False, "message": "No prompt provided"}

        try:
            from shared_utils import generate_image_from_text

            result = generate_image_from_text(prompt)

            if result and result.get("success"):
                image_path = result.get("image_path")
                if image_path and self.send_image_callback:
                    self.send_image_callback(image_path)
                    return {
                        "success": True,
                        "message": f"Image generated: {prompt[:50]}...",
                        "image_path": image_path
                    }
                elif image_path:
                    return {
                        "success": True,
                        "message": f"Image generated at {image_path}",
                        "image_path": image_path
                    }

            return {"success": False, "message": result.get("error", "Image generation failed")}

        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

    def _execute_weather(self, arguments: dict) -> dict:
        """Execute the get_weather tool call."""
        if not self.bot_data.get('weather_enabled'):
            return {"success": False, "message": "Weather tool disabled for this bot"}

        location = arguments.get("location", "")
        days = arguments.get("days", 1)

        if not location:
            return {"success": False, "message": "Location is required"}

        try:
            from signal_bot.weather_client import get_weather_sync

            result = get_weather_sync(location, days)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            # Format the response for the AI to use
            return {
                "success": True,
                "weather_data": result,
                "message": f"Weather data retrieved for {result.get('location', {}).get('name', location)}"
            }

        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return {"success": False, "message": f"Error getting weather: {str(e)}"}

    # Time tool execution methods

    def _execute_get_datetime(self, arguments: dict) -> dict:
        """Execute the get_datetime tool call."""
        if not self.bot_data.get('time_enabled'):
            return {"success": False, "message": "Time tool disabled for this bot"}

        timezone = arguments.get("timezone", "UTC")

        try:
            from signal_bot.time_client import get_datetime_sync

            result = get_datetime_sync(timezone)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "time_data": result,
                "message": f"Current time in {result.get('timezone', timezone)}: {result.get('datetime', 'unknown')}"
            }

        except Exception as e:
            logger.error(f"Error getting datetime: {e}")
            return {"success": False, "message": f"Error getting datetime: {str(e)}"}

    def _execute_get_unix_timestamp(self, arguments: dict) -> dict:
        """Execute the get_unix_timestamp tool call."""
        if not self.bot_data.get('time_enabled'):
            return {"success": False, "message": "Time tool disabled for this bot"}

        try:
            from signal_bot.time_client import get_unix_timestamp_sync

            result = get_unix_timestamp_sync()

            return {
                "success": True,
                "time_data": result,
                "message": f"Current Unix timestamp: {result.get('unix_timestamp_int', 'unknown')}"
            }

        except Exception as e:
            logger.error(f"Error getting Unix timestamp: {e}")
            return {"success": False, "message": f"Error getting Unix timestamp: {str(e)}"}

    # Wikipedia tool execution methods

    def _execute_search_wikipedia(self, arguments: dict) -> dict:
        """Execute the search_wikipedia tool call."""
        if not self.bot_data.get('wikipedia_enabled'):
            return {"success": False, "message": "Wikipedia tool disabled for this bot"}

        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        if not query:
            return {"success": False, "message": "Search query is required"}

        try:
            from signal_bot.wikipedia_client import search_wikipedia_sync

            result = search_wikipedia_sync(query, limit)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} Wikipedia articles for '{query}'"
            }

        except Exception as e:
            logger.error(f"Error searching Wikipedia: {e}")
            return {"success": False, "message": f"Error searching Wikipedia: {str(e)}"}

    def _execute_get_wikipedia_article(self, arguments: dict) -> dict:
        """Execute the get_wikipedia_article tool call."""
        if not self.bot_data.get('wikipedia_enabled'):
            return {"success": False, "message": "Wikipedia tool disabled for this bot"}

        title = arguments.get("title", "")

        if not title:
            return {"success": False, "message": "Article title is required"}

        try:
            from signal_bot.wikipedia_client import get_wikipedia_summary_sync

            result = get_wikipedia_summary_sync(title)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved Wikipedia article: {result.get('title', title)}"
            }

        except Exception as e:
            logger.error(f"Error getting Wikipedia article: {e}")
            return {"success": False, "message": f"Error getting Wikipedia article: {str(e)}"}

    def _execute_random_wikipedia_article(self, arguments: dict) -> dict:
        """Execute the get_random_wikipedia_article tool call."""
        if not self.bot_data.get('wikipedia_enabled'):
            return {"success": False, "message": "Wikipedia tool disabled for this bot"}

        try:
            from signal_bot.wikipedia_client import get_random_article_sync

            result = get_random_article_sync()

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Random Wikipedia article: {result.get('title', 'Unknown')}"
            }

        except Exception as e:
            logger.error(f"Error getting random Wikipedia article: {e}")
            return {"success": False, "message": f"Error getting random Wikipedia article: {str(e)}"}

    # Finance tool execution methods

    def _execute_stock_quote(self, arguments: dict) -> dict:
        """Execute the get_stock_quote tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_ticker_info_sync

            result = get_ticker_info_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Stock quote retrieved for {result.get('symbol', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting stock quote: {e}")
            return {"success": False, "message": f"Error getting stock quote: {str(e)}"}

    def _execute_stock_news(self, arguments: dict) -> dict:
        """Execute the get_stock_news tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        count = arguments.get("count", 5)

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_ticker_news_sync

            result = get_ticker_news_sync(symbol, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {result.get('count', 0)} news articles for {symbol}"
            }

        except Exception as e:
            logger.error(f"Error getting stock news: {e}")
            return {"success": False, "message": f"Error getting stock news: {str(e)}"}

    def _execute_search_stocks(self, arguments: dict) -> dict:
        """Execute the search_stocks tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        query = arguments.get("query", "")
        count = arguments.get("count", 10)

        if not query:
            return {"success": False, "message": "Search query is required"}

        try:
            from signal_bot.finance_client import search_symbols_sync

            result = search_symbols_sync(query, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} results for '{query}'"
            }

        except Exception as e:
            logger.error(f"Error searching stocks: {e}")
            return {"success": False, "message": f"Error searching stocks: {str(e)}"}

    def _execute_top_stocks(self, arguments: dict) -> dict:
        """Execute the get_top_stocks tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        entity_type = arguments.get("entity_type", "companies")
        sector = arguments.get("sector", "technology")
        count = arguments.get("count", 10)

        try:
            from signal_bot.finance_client import get_top_entities_sync

            result = get_top_entities_sync(entity_type, sector, count)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved top {entity_type} in {sector} sector"
            }

        except Exception as e:
            logger.error(f"Error getting top stocks: {e}")
            return {"success": False, "message": f"Error getting top stocks: {str(e)}"}

    def _execute_price_history(self, arguments: dict) -> dict:
        """Execute the get_price_history tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "1mo")
        interval = arguments.get("interval", "1d")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_price_history_sync

            result = get_price_history_sync(symbol, period, interval)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {result.get('data_points', 0)} data points for {symbol}"
            }

        except Exception as e:
            logger.error(f"Error getting price history: {e}")
            return {"success": False, "message": f"Error getting price history: {str(e)}"}

    def _execute_options(self, arguments: dict) -> dict:
        """Execute the get_options tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        option_type = arguments.get("option_type", "both")
        date = arguments.get("date")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_option_chain_sync

            result = get_option_chain_sync(symbol, option_type, date)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved options chain for {symbol} expiring {result.get('expiration_date', 'N/A')}"
            }

        except Exception as e:
            logger.error(f"Error getting options: {e}")
            return {"success": False, "message": f"Error getting options: {str(e)}"}

    def _execute_earnings(self, arguments: dict) -> dict:
        """Execute the get_earnings tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "quarterly")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_earnings_sync

            result = get_earnings_sync(symbol, period)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {period} earnings data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting earnings: {e}")
            return {"success": False, "message": f"Error getting earnings: {str(e)}"}

    def _execute_analyst_ratings(self, arguments: dict) -> dict:
        """Execute the get_analyst_ratings tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_analyst_ratings_sync

            result = get_analyst_ratings_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved analyst ratings for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting analyst ratings: {e}")
            return {"success": False, "message": f"Error getting analyst ratings: {str(e)}"}

    def _execute_dividends(self, arguments: dict) -> dict:
        """Execute the get_dividends tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        include_history = arguments.get("include_history", False)

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_dividends_sync

            result = get_dividends_sync(symbol, include_history)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved dividend data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting dividends: {e}")
            return {"success": False, "message": f"Error getting dividends: {str(e)}"}

    def _execute_financials(self, arguments: dict) -> dict:
        """Execute the get_financials tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        period = arguments.get("period", "annual")

        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_financials_sync

            result = get_financials_sync(symbol, period)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved {period} financials for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting financials: {e}")
            return {"success": False, "message": f"Error getting financials: {str(e)}"}

    def _execute_holders(self, arguments: dict) -> dict:
        """Execute the get_holders tool call."""
        if not self.bot_data.get('finance_enabled'):
            return {"success": False, "message": "Finance tools disabled for this bot"}

        symbol = arguments.get("symbol", "")
        if not symbol:
            return {"success": False, "message": "Symbol is required"}

        try:
            from signal_bot.finance_client import get_holders_sync

            result = get_holders_sync(symbol)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Retrieved holder data for {result.get('name', symbol)}"
            }

        except Exception as e:
            logger.error(f"Error getting holders: {e}")
            return {"success": False, "message": f"Error getting holders: {str(e)}"}

    # Reaction tool execution method

    def _execute_react_to_message(self, arguments: dict) -> dict:
        """Execute the react_to_message tool call."""
        if not self.bot_data.get('reaction_tool_enabled'):
            return {"success": False, "message": "Reaction tool disabled for this bot"}

        if not self.send_reaction_callback:
            return {"success": False, "message": "Reaction callback not available"}

        # Check reaction cap
        if self.reactions_sent >= self.max_reactions:
            return {
                "success": False,
                "message": f"Maximum reactions ({self.max_reactions}) already sent for this response"
            }

        message_index = arguments.get("message_index")
        emoji = arguments.get("emoji", "")

        if message_index is None:
            return {"success": False, "message": "message_index is required"}

        if not emoji:
            return {"success": False, "message": "emoji is required"}

        # Basic validation - emoji shouldn't be too long
        if len(emoji) > 10:
            return {"success": False, "message": "Please provide a single emoji"}

        # Find the message in metadata
        target_msg = None
        for msg in self.reaction_metadata:
            if msg.get("index") == message_index:
                target_msg = msg
                break

        if not target_msg:
            return {
                "success": False,
                "message": f"Message [{message_index}] not found or cannot be reacted to (may be a bot message or missing metadata)"
            }

        # Send the reaction
        try:
            self.send_reaction_callback(
                target_msg["sender_id"],
                target_msg["signal_timestamp"],
                emoji
            )
            self.reactions_sent += 1
            logger.info(f"Sent reaction {emoji} to message [{message_index}]")
            return {
                "success": True,
                "message": f"Reacted with {emoji} to message [{message_index}]"
            }
        except Exception as e:
            logger.error(f"Error sending reaction: {e}")
            return {"success": False, "message": f"Failed to send reaction: {str(e)}"}

    # Google Sheets tool execution methods

    def _sheets_enabled(self) -> bool:
        """Check if Google Sheets is enabled and connected."""
        return (
            self.bot_data.get('google_sheets_enabled', False) and
            self.bot_data.get('google_connected', False)
        )

    def _execute_create_spreadsheet(self, arguments: dict) -> dict:
        """Execute the create_spreadsheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        title = arguments.get("title", "")
        description = arguments.get("description", "")

        if not title:
            return {"success": False, "message": "Title is required"}

        try:
            from signal_bot.google_sheets_client import create_spreadsheet_sync

            result = create_spreadsheet_sync(
                bot_data=self.bot_data,
                group_id=self.group_id,
                title=title,
                description=description,
                created_by=self.sender_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Created spreadsheet '{title}': {result.get('url', 'URL unavailable')}"
            }

        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}")
            return {"success": False, "message": f"Error creating spreadsheet: {str(e)}"}

    def _execute_list_spreadsheets(self, arguments: dict) -> dict:
        """Execute the list_spreadsheets tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        try:
            from signal_bot.google_sheets_client import list_spreadsheets_sync

            result = list_spreadsheets_sync(
                bot_data=self.bot_data,
                group_id=self.group_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} spreadsheet(s) for this group"
            }

        except Exception as e:
            logger.error(f"Error listing spreadsheets: {e}")
            return {"success": False, "message": f"Error listing spreadsheets: {str(e)}"}

    def _execute_read_sheet(self, arguments: dict) -> dict:
        """Execute the read_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "Sheet1!A1:Z100")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import read_sheet_sync

            result = read_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Read {result.get('row_count', 0)} rows from sheet"
            }

        except Exception as e:
            logger.error(f"Error reading sheet: {e}")
            return {"success": False, "message": f"Error reading sheet: {str(e)}"}

    def _execute_write_to_sheet(self, arguments: dict) -> dict:
        """Execute the write_to_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")
        values = arguments.get("values", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required"}
        if not values:
            return {"success": False, "message": "values are required"}

        try:
            from signal_bot.google_sheets_client import write_sheet_sync

            result = write_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                values=values
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Updated {result.get('updated_cells', 0)} cells"
            }

        except Exception as e:
            logger.error(f"Error writing to sheet: {e}")
            return {"success": False, "message": f"Error writing to sheet: {str(e)}"}

    def _execute_add_row_to_sheet(self, arguments: dict) -> dict:
        """Execute the add_row_to_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        values = arguments.get("values", [])
        include_metadata = arguments.get("include_metadata", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not values:
            return {"success": False, "message": "values are required"}

        try:
            from signal_bot.google_sheets_client import append_to_sheet_sync

            result = append_to_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                values=values,
                added_by=self.sender_name,
                include_metadata=include_metadata
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            row_added = result.get("row_added", [])
            return {
                "success": True,
                "data": result,
                "message": f"Added row: {', '.join(str(v) for v in row_added[:5])}{'...' if len(row_added) > 5 else ''}"
            }

        except Exception as e:
            logger.error(f"Error adding row to sheet: {e}")
            return {"success": False, "message": f"Error adding row to sheet: {str(e)}"}

    def _execute_search_sheets(self, arguments: dict) -> dict:
        """Execute the search_sheets tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        query = arguments.get("query", "")

        if not query:
            return {"success": False, "message": "Search query is required"}

        try:
            from signal_bot.google_sheets_client import search_sheets_sync

            result = search_sheets_sync(
                bot_data=self.bot_data,
                group_id=self.group_id,
                query=query
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} spreadsheet(s) matching '{query}'"
            }

        except Exception as e:
            logger.error(f"Error searching sheets: {e}")
            return {"success": False, "message": f"Error searching sheets: {str(e)}"}

    # Member memory tool execution methods

    def _execute_save_member_memory(self, arguments: dict) -> dict:
        """Execute the save_member_memory tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        member_name = arguments.get("member_name", "").strip()
        slot_type = arguments.get("slot_type", "")
        content = arguments.get("content", "").strip()

        if not member_name:
            return {"success": False, "message": "member_name is required"}
        if not slot_type:
            return {"success": False, "message": "slot_type is required"}
        if not content:
            return {"success": False, "message": "content is required"}

        # Validate slot_type
        valid_slots = ["home_location", "work_info", "interests", "media_prefs", "life_events", "response_prefs", "social_notes"]
        if slot_type not in valid_slots:
            return {"success": False, "message": f"Invalid slot_type. Must be one of: {', '.join(valid_slots)}"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog, db
            from datetime import datetime

            # Try to find member_id from message logs
            msg = MessageLog.query.filter_by(
                group_id=self.group_id,
                sender_name=member_name,
                is_bot=False
            ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                # Try case-insensitive search
                msg = MessageLog.query.filter(
                    MessageLog.group_id == self.group_id,
                    MessageLog.sender_name.ilike(member_name),
                    MessageLog.is_bot == False
                ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                return {
                    "success": False,
                    "message": f"No known member '{member_name}' found in this group's chat history"
                }

            member_id = msg.sender_id
            canonical_name = msg.sender_name  # Use the name as it appears in logs

            # Check if memory already exists for this slot
            existing = GroupMemberMemory.query.filter_by(
                group_id=self.group_id,
                member_id=member_id,
                slot_type=slot_type
            ).first()

            if existing:
                # Update existing
                existing.content = content
                existing.member_name = canonical_name
                existing.updated_at = datetime.utcnow()
                action = "Updated"
            else:
                # Create new
                new_memory = GroupMemberMemory(
                    group_id=self.group_id,
                    member_id=member_id,
                    member_name=canonical_name,
                    slot_type=slot_type,
                    content=content
                )
                db.session.add(new_memory)
                action = "Saved"

            db.session.commit()

            logger.info(f"Member memory {action.lower()}: {canonical_name} ({slot_type}): {content[:50]}...")

            return {
                "success": True,
                "data": {
                    "member_name": canonical_name,
                    "slot_type": slot_type,
                    "content": content,
                    "action": action.lower()
                },
                "message": f"{action} memory for {canonical_name}: {slot_type} = {content[:100]}"
            }

        except Exception as e:
            logger.error(f"Error saving member memory: {e}")
            return {"success": False, "message": f"Error saving memory: {str(e)}"}

    def _execute_get_member_memories(self, arguments: dict) -> dict:
        """Execute the get_member_memories tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        member_name = arguments.get("member_name", "").strip()

        if not member_name:
            return {"success": False, "message": "member_name is required"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog

            # Try to find member_id from message logs
            msg = MessageLog.query.filter_by(
                group_id=self.group_id,
                sender_name=member_name,
                is_bot=False
            ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                # Try case-insensitive search
                msg = MessageLog.query.filter(
                    MessageLog.group_id == self.group_id,
                    MessageLog.sender_name.ilike(member_name),
                    MessageLog.is_bot == False
                ).order_by(MessageLog.timestamp.desc()).first()

            if not msg:
                return {
                    "success": False,
                    "message": f"No known member '{member_name}' found in this group's chat history"
                }

            member_id = msg.sender_id
            canonical_name = msg.sender_name

            # Get all memories for this member
            memories = GroupMemberMemory.query.filter_by(
                group_id=self.group_id,
                member_id=member_id
            ).all()

            if not memories:
                return {
                    "success": True,
                    "data": {
                        "member_name": canonical_name,
                        "memories": {},
                        "count": 0
                    },
                    "message": f"No saved memories for {canonical_name}"
                }

            memory_dict = {}
            for mem in memories:
                memory_dict[mem.slot_type] = {
                    "content": mem.content,
                    "updated_at": mem.updated_at.isoformat() if mem.updated_at else None
                }

            return {
                "success": True,
                "data": {
                    "member_name": canonical_name,
                    "memories": memory_dict,
                    "count": len(memories)
                },
                "message": f"Found {len(memories)} memories for {canonical_name}"
            }

        except Exception as e:
            logger.error(f"Error getting member memories: {e}")
            return {"success": False, "message": f"Error getting memories: {str(e)}"}

    def _execute_list_group_members(self, arguments: dict) -> dict:
        """Execute the list_group_members tool call."""
        if not self.bot_data.get('member_memory_tools_enabled'):
            return {"success": False, "message": "Member memory tools disabled for this bot"}

        try:
            from signal_bot.models import GroupMemberMemory, MessageLog
            from sqlalchemy import func

            # Get distinct non-bot members from message logs
            members = MessageLog.query.filter_by(
                group_id=self.group_id,
                is_bot=False
            ).with_entities(
                MessageLog.sender_id,
                MessageLog.sender_name
            ).distinct().all()

            if not members:
                return {
                    "success": True,
                    "data": {"members": [], "count": 0},
                    "message": "No members found in chat history"
                }

            # Build member list with memory counts
            member_list = []
            for member_id, member_name in members:
                if not member_id:
                    continue

                # Count memories for this member
                memory_count = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_id=member_id
                ).count()

                # Get memory types stored
                memory_types = GroupMemberMemory.query.filter_by(
                    group_id=self.group_id,
                    member_id=member_id
                ).with_entities(GroupMemberMemory.slot_type).all()
                memory_types = [m[0] for m in memory_types]

                member_list.append({
                    "name": member_name,
                    "memory_count": memory_count,
                    "memory_types": memory_types
                })

            # Sort by memory count (most known members first)
            member_list.sort(key=lambda x: x["memory_count"], reverse=True)

            return {
                "success": True,
                "data": {
                    "members": member_list,
                    "count": len(member_list)
                },
                "message": f"Found {len(member_list)} group members"
            }

        except Exception as e:
            logger.error(f"Error listing group members: {e}")
            return {"success": False, "message": f"Error listing members: {str(e)}"}


def create_tool_executor_callback(executor: ToolExecutor) -> Callable[[str, dict], dict]:
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
    executor: ToolExecutor | SignalToolExecutor
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
