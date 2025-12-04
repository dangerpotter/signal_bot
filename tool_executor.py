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
        if function_name == "format_columns":
            return self._execute_format_columns(arguments)
        if function_name == "clear_range":
            return self._execute_clear_range(arguments)
        if function_name == "delete_rows":
            return self._execute_delete_rows(arguments)
        if function_name == "delete_columns":
            return self._execute_delete_columns(arguments)
        if function_name == "insert_rows":
            return self._execute_insert_rows(arguments)
        if function_name == "insert_columns":
            return self._execute_insert_columns(arguments)
        if function_name == "add_sheet":
            return self._execute_add_sheet(arguments)
        if function_name == "delete_sheet":
            return self._execute_delete_sheet(arguments)
        if function_name == "rename_sheet":
            return self._execute_rename_sheet(arguments)
        if function_name == "freeze_rows":
            return self._execute_freeze_rows(arguments)
        if function_name == "freeze_columns":
            return self._execute_freeze_columns(arguments)
        if function_name == "sort_range":
            return self._execute_sort_range(arguments)
        if function_name == "auto_resize_columns":
            return self._execute_auto_resize_columns(arguments)
        if function_name == "merge_cells":
            return self._execute_merge_cells(arguments)
        if function_name == "unmerge_cells":
            return self._execute_unmerge_cells(arguments)
        if function_name == "conditional_format":
            return self._execute_conditional_format(arguments)
        if function_name == "data_validation":
            return self._execute_data_validation(arguments)
        if function_name == "alternating_colors":
            return self._execute_alternating_colors(arguments)
        if function_name == "add_note":
            return self._execute_add_note(arguments)
        if function_name == "set_borders":
            return self._execute_set_borders(arguments)
        if function_name == "set_alignment":
            return self._execute_set_alignment(arguments)
        if function_name == "create_chart":
            return self._execute_create_chart(arguments)
        if function_name == "list_charts":
            return self._execute_list_charts(arguments)
        if function_name == "update_chart":
            return self._execute_update_chart(arguments)
        if function_name == "delete_chart":
            return self._execute_delete_chart(arguments)
        if function_name == "create_pivot_table":
            return self._execute_create_pivot_table(arguments)
        if function_name == "delete_pivot_table":
            return self._execute_delete_pivot_table(arguments)

        # Text formatting & color tools (Batch 1)
        if function_name == "set_text_format":
            return self._execute_set_text_format(arguments)
        if function_name == "set_text_color":
            return self._execute_set_text_color(arguments)
        if function_name == "set_background_color":
            return self._execute_set_background_color(arguments)
        if function_name == "add_hyperlink":
            return self._execute_add_hyperlink(arguments)

        # Filtering tools (Batch 2)
        if function_name == "set_basic_filter":
            return self._execute_set_basic_filter(arguments)
        if function_name == "clear_basic_filter":
            return self._execute_clear_basic_filter(arguments)
        if function_name == "create_filter_view":
            return self._execute_create_filter_view(arguments)
        if function_name == "delete_filter_view":
            return self._execute_delete_filter_view(arguments)

        # Named & protected range tools (Batch 3)
        if function_name == "create_named_range":
            return self._execute_create_named_range(arguments)
        if function_name == "delete_named_range":
            return self._execute_delete_named_range(arguments)
        if function_name == "list_named_ranges":
            return self._execute_list_named_ranges(arguments)
        if function_name == "protect_range":
            return self._execute_protect_range(arguments)

        # Find/Replace & Copy/Paste tools (Batch 4)
        if function_name == "find_replace":
            return self._execute_find_replace(arguments)
        if function_name == "copy_paste":
            return self._execute_copy_paste(arguments)
        if function_name == "cut_paste":
            return self._execute_cut_paste(arguments)

        # Spreadsheet Properties tools (Batch 8)
        if function_name == "set_spreadsheet_timezone":
            return self._execute_set_spreadsheet_timezone(arguments)
        if function_name == "set_spreadsheet_locale":
            return self._execute_set_spreadsheet_locale(arguments)
        if function_name == "set_recalculation_interval":
            return self._execute_set_recalculation_interval(arguments)
        if function_name == "get_spreadsheet_properties":
            return self._execute_get_spreadsheet_properties(arguments)
        if function_name == "set_spreadsheet_theme":
            return self._execute_set_spreadsheet_theme(arguments)

        # Developer Metadata tools (Batch 9)
        if function_name == "set_developer_metadata":
            return self._execute_set_developer_metadata(arguments)
        if function_name == "get_developer_metadata":
            return self._execute_get_developer_metadata(arguments)
        if function_name == "delete_developer_metadata":
            return self._execute_delete_developer_metadata(arguments)

        # Additional Cell Formatting tools (Batch 10)
        if function_name == "set_text_direction":
            return self._execute_set_text_direction(arguments)
        if function_name == "set_text_rotation":
            return self._execute_set_text_rotation(arguments)
        if function_name == "set_cell_padding":
            return self._execute_set_cell_padding(arguments)
        if function_name == "set_rich_text":
            return self._execute_set_rich_text(arguments)

        # Sheet properties extension tools
        if function_name == "hide_sheet":
            return self._execute_hide_sheet(arguments)
        if function_name == "show_sheet":
            return self._execute_show_sheet(arguments)
        if function_name == "set_tab_color":
            return self._execute_set_tab_color(arguments)
        if function_name == "set_right_to_left":
            return self._execute_set_right_to_left(arguments)
        if function_name == "get_sheet_properties":
            return self._execute_get_sheet_properties(arguments)

        # Protected ranges management tools
        if function_name == "list_protected_ranges":
            return self._execute_list_protected_ranges(arguments)
        if function_name == "update_protected_range":
            return self._execute_update_protected_range(arguments)
        if function_name == "delete_protected_range":
            return self._execute_delete_protected_range(arguments)
        if function_name == "protect_sheet":
            return self._execute_protect_sheet(arguments)

        # Filter views
        if function_name == "list_filter_views":
            return self._execute_list_filter_views(arguments)

        # Dimension groups (row/column grouping)
        if function_name == "create_row_group":
            return self._execute_create_row_group(arguments)
        if function_name == "create_column_group":
            return self._execute_create_column_group(arguments)
        if function_name == "delete_row_group":
            return self._execute_delete_row_group(arguments)
        if function_name == "delete_column_group":
            return self._execute_delete_column_group(arguments)
        if function_name == "collapse_expand_group":
            return self._execute_collapse_expand_group(arguments)
        if function_name == "set_group_control_position":
            return self._execute_set_group_control_position(arguments)

        # Slicers
        if function_name == "list_slicers":
            return self._execute_list_slicers(arguments)
        if function_name == "create_slicer":
            return self._execute_create_slicer(arguments)
        if function_name == "update_slicer":
            return self._execute_update_slicer(arguments)
        if function_name == "delete_slicer":
            return self._execute_delete_slicer(arguments)

        # Tables
        if function_name == "list_tables":
            return self._execute_list_tables(arguments)
        if function_name == "create_table":
            return self._execute_create_table(arguments)
        if function_name == "delete_table":
            return self._execute_delete_table(arguments)
        if function_name == "update_table_column":
            return self._execute_update_table_column(arguments)

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

    def _execute_format_columns(self, arguments: dict) -> dict:
        """Execute the format_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns", "")
        format_type = arguments.get("format_type", "")
        pattern = arguments.get("pattern")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not columns:
            return {"success": False, "message": "columns is required (e.g., 'B' or 'B:E')"}
        if not format_type:
            return {"success": False, "message": "format_type is required"}

        # Validate format_type
        valid_types = ["CURRENCY", "PERCENT", "NUMBER", "DATE", "TEXT"]
        if format_type.upper() not in valid_types:
            return {"success": False, "message": f"Invalid format_type. Must be one of: {', '.join(valid_types)}"}

        try:
            from signal_bot.google_sheets_client import format_columns_sync

            result = format_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns,
                format_type=format_type.upper(),
                pattern=pattern
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Formatted columns {columns} as {format_type}")
            }

        except Exception as e:
            logger.error(f"Error formatting columns: {e}")
            return {"success": False, "message": f"Error formatting columns: {str(e)}"}

    def _execute_clear_range(self, arguments: dict) -> dict:
        """Execute the clear_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C10' or 'B:B')"}

        try:
            from signal_bot.google_sheets_client import clear_range_sync

            result = clear_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Cleared range {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error clearing range: {e}")
            return {"success": False, "message": f"Error clearing range: {str(e)}"}

    def _execute_delete_rows(self, arguments: dict) -> dict:
        """Execute the delete_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if start_row is None:
            return {"success": False, "message": "start_row is required"}
        if start_row < 1:
            return {"success": False, "message": "start_row must be at least 1"}

        try:
            from signal_bot.google_sheets_client import delete_rows_sync

            result = delete_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted row(s)")
            }

        except Exception as e:
            logger.error(f"Error deleting rows: {e}")
            return {"success": False, "message": f"Error deleting rows: {str(e)}"}

    def _execute_delete_columns(self, arguments: dict) -> dict:
        """Execute the delete_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not columns:
            return {"success": False, "message": "columns is required (e.g., 'C' or 'C:E')"}

        try:
            from signal_bot.google_sheets_client import delete_columns_sync

            result = delete_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted column(s) {columns}")
            }

        except Exception as e:
            logger.error(f"Error deleting columns: {e}")
            return {"success": False, "message": f"Error deleting columns: {str(e)}"}

    def _execute_insert_rows(self, arguments: dict) -> dict:
        """Execute the insert_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        row = arguments.get("row")
        count = arguments.get("count", 1)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if row is None:
            return {"success": False, "message": "row is required"}
        if row < 1:
            return {"success": False, "message": "row must be at least 1"}

        try:
            from signal_bot.google_sheets_client import insert_rows_sync

            result = insert_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                start_row=row,
                num_rows=count
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Inserted {count} row(s) at row {row}")
            }

        except Exception as e:
            logger.error(f"Error inserting rows: {e}")
            return {"success": False, "message": f"Error inserting rows: {str(e)}"}

    def _execute_insert_columns(self, arguments: dict) -> dict:
        """Execute the insert_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        column = arguments.get("column", "")
        count = arguments.get("count", 1)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not column:
            return {"success": False, "message": "column is required (e.g., 'C')"}

        try:
            from signal_bot.google_sheets_client import insert_columns_sync

            result = insert_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                column=column,
                num_columns=count
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Inserted {count} column(s) at column {column}")
            }

        except Exception as e:
            logger.error(f"Error inserting columns: {e}")
            return {"success": False, "message": f"Error inserting columns: {str(e)}"}

    def _execute_add_sheet(self, arguments: dict) -> dict:
        """Execute the add_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        title = arguments.get("title", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not title:
            return {"success": False, "message": "title is required"}

        try:
            from signal_bot.google_sheets_client import add_sheet_sync

            result = add_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                title=title
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added sheet '{title}'")
            }

        except Exception as e:
            logger.error(f"Error adding sheet: {e}")
            return {"success": False, "message": f"Error adding sheet: {str(e)}"}

    def _execute_delete_sheet(self, arguments: dict) -> dict:
        """Execute the delete_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import delete_sheet_sync

            result = delete_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted sheet '{sheet_name}'")
            }

        except Exception as e:
            logger.error(f"Error deleting sheet: {e}")
            return {"success": False, "message": f"Error deleting sheet: {str(e)}"}

    def _execute_rename_sheet(self, arguments: dict) -> dict:
        """Execute the rename_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        old_name = arguments.get("old_name", "")
        new_name = arguments.get("new_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not old_name:
            return {"success": False, "message": "old_name is required"}
        if not new_name:
            return {"success": False, "message": "new_name is required"}

        try:
            from signal_bot.google_sheets_client import rename_sheet_sync

            result = rename_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                old_name=old_name,
                new_name=new_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Renamed sheet to '{new_name}'")
            }

        except Exception as e:
            logger.error(f"Error renaming sheet: {e}")
            return {"success": False, "message": f"Error renaming sheet: {str(e)}"}

    def _execute_freeze_rows(self, arguments: dict) -> dict:
        """Execute the freeze_rows tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        num_rows = arguments.get("num_rows")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if num_rows is None:
            return {"success": False, "message": "num_rows is required"}

        try:
            from signal_bot.google_sheets_client import freeze_rows_sync

            result = freeze_rows_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                num_rows=num_rows,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Froze {num_rows} row(s)")
            }

        except Exception as e:
            logger.error(f"Error freezing rows: {e}")
            return {"success": False, "message": f"Error freezing rows: {str(e)}"}

    def _execute_freeze_columns(self, arguments: dict) -> dict:
        """Execute the freeze_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        num_columns = arguments.get("num_columns")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if num_columns is None:
            return {"success": False, "message": "num_columns is required"}

        try:
            from signal_bot.google_sheets_client import freeze_columns_sync

            result = freeze_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                num_columns=num_columns,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Froze {num_columns} column(s)")
            }

        except Exception as e:
            logger.error(f"Error freezing columns: {e}")
            return {"success": False, "message": f"Error freezing columns: {str(e)}"}

    def _execute_sort_range(self, arguments: dict) -> dict:
        """Execute the sort_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        column = arguments.get("column", "")
        ascending = arguments.get("ascending", True)
        has_header = arguments.get("has_header", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not column:
            return {"success": False, "message": "column is required (e.g., 'B')"}

        try:
            from signal_bot.google_sheets_client import sort_range_sync

            result = sort_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sort_column=column,
                ascending=ascending,
                has_header=has_header
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sorted by column {column}")
            }

        except Exception as e:
            logger.error(f"Error sorting range: {e}")
            return {"success": False, "message": f"Error sorting range: {str(e)}"}

    def _execute_auto_resize_columns(self, arguments: dict) -> dict:
        """Execute the auto_resize_columns tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        columns = arguments.get("columns")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import auto_resize_columns_sync

            result = auto_resize_columns_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Auto-resized columns")
            }

        except Exception as e:
            logger.error(f"Error auto-resizing columns: {e}")
            return {"success": False, "message": f"Error auto-resizing columns: {str(e)}"}

    def _execute_merge_cells(self, arguments: dict) -> dict:
        """Execute the merge_cells tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C1')"}

        try:
            from signal_bot.google_sheets_client import merge_cells_sync

            result = merge_cells_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Merged cells {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error merging cells: {e}")
            return {"success": False, "message": f"Error merging cells: {str(e)}"}

    def _execute_unmerge_cells(self, arguments: dict) -> dict:
        """Execute the unmerge_cells tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_notation = arguments.get("range", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:C1')"}

        try:
            from signal_bot.google_sheets_client import unmerge_cells_sync

            result = unmerge_cells_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Unmerged cells {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error unmerging cells: {e}")
            return {"success": False, "message": f"Error unmerging cells: {str(e)}"}

    # Batch 4: Formatting & Validation tool execution methods

    def _execute_conditional_format(self, arguments: dict) -> dict:
        """Execute the conditional_format tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        rule_type = arguments.get("rule_type", "")
        condition_value = arguments.get("condition_value")
        format_type = arguments.get("format_type", "background")
        color = arguments.get("color", "red")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'B2:B100')"}
        if not rule_type:
            return {"success": False, "message": "rule_type is required (greater_than, less_than, equals, contains, not_empty, is_empty)"}

        try:
            from signal_bot.google_sheets_client import conditional_format_sync

            result = conditional_format_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                rule_type=rule_type,
                condition_value=condition_value,
                format_type=format_type,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added conditional formatting to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding conditional format: {e}")
            return {"success": False, "message": f"Error adding conditional format: {str(e)}"}

    def _execute_data_validation(self, arguments: dict) -> dict:
        """Execute the data_validation tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        validation_type = arguments.get("validation_type", "")
        values = arguments.get("values")
        min_value = arguments.get("min_value")
        max_value = arguments.get("max_value")
        strict = arguments.get("strict", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'C2:C100')"}
        if not validation_type:
            return {"success": False, "message": "validation_type is required (dropdown, number_range, date, checkbox)"}

        try:
            from signal_bot.google_sheets_client import data_validation_sync

            result = data_validation_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                validation_type=validation_type,
                values=values,
                min_value=min_value,
                max_value=max_value,
                strict=strict
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added {validation_type} validation to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding data validation: {e}")
            return {"success": False, "message": f"Error adding data validation: {str(e)}"}

    def _execute_alternating_colors(self, arguments: dict) -> dict:
        """Execute the alternating_colors tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        header_color = arguments.get("header_color", "blue")
        first_band_color = arguments.get("first_band_color", "white")
        second_band_color = arguments.get("second_band_color", "lightgray")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import alternating_colors_sync

            result = alternating_colors_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                header_color=header_color,
                first_band_color=first_band_color,
                second_band_color=second_band_color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added alternating colors to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error adding alternating colors: {e}")
            return {"success": False, "message": f"Error adding alternating colors: {str(e)}"}

    # Batch 5: Cell Enhancements tool execution methods

    def _execute_add_note(self, arguments: dict) -> dict:
        """Execute the add_note tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        note = arguments.get("note", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'B2')"}

        try:
            from signal_bot.google_sheets_client import add_note_sync

            result = add_note_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                note=note
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added note to cell {cell}")
            }

        except Exception as e:
            logger.error(f"Error adding note: {e}")
            return {"success": False, "message": f"Error adding note: {str(e)}"}

    def _execute_set_borders(self, arguments: dict) -> dict:
        """Execute the set_borders tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        border_style = arguments.get("border_style", "solid")
        color = arguments.get("color", "black")
        sides = arguments.get("sides", "all")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import set_borders_sync

            result = set_borders_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                border_style=border_style,
                color=color,
                sides=sides
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added borders to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting borders: {e}")
            return {"success": False, "message": f"Error setting borders: {str(e)}"}

    def _execute_set_alignment(self, arguments: dict) -> dict:
        """Execute the set_alignment tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        horizontal = arguments.get("horizontal")
        vertical = arguments.get("vertical")
        wrap = arguments.get("wrap")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not horizontal and not vertical and not wrap:
            return {"success": False, "message": "At least one of horizontal, vertical, or wrap must be specified"}

        try:
            from signal_bot.google_sheets_client import set_alignment_sync

            result = set_alignment_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                horizontal=horizontal,
                vertical=vertical,
                wrap=wrap
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set alignment on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting alignment: {e}")
            return {"success": False, "message": f"Error setting alignment: {str(e)}"}

    # Batch 10: Additional Cell Formatting tool execution methods

    def _execute_set_text_direction(self, arguments: dict) -> dict:
        """Execute the set_text_direction tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        direction = arguments.get("direction", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not direction:
            return {"success": False, "message": "direction is required (left_to_right or right_to_left)"}

        try:
            from signal_bot.google_sheets_client import set_text_direction_sync

            result = set_text_direction_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                direction=direction
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text direction to {direction} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text direction: {e}")
            return {"success": False, "message": f"Error setting text direction: {str(e)}"}

    def _execute_set_text_rotation(self, arguments: dict) -> dict:
        """Execute the set_text_rotation tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        angle = arguments.get("angle")
        vertical = arguments.get("vertical")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if angle is None and not vertical:
            return {"success": False, "message": "Either 'angle' or 'vertical' must be specified"}

        try:
            from signal_bot.google_sheets_client import set_text_rotation_sync

            result = set_text_rotation_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                angle=angle,
                vertical=vertical
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            rotation_desc = "vertical" if vertical else f"{angle} degrees"
            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text rotation to {rotation_desc} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text rotation: {e}")
            return {"success": False, "message": f"Error setting text rotation: {str(e)}"}

    def _execute_set_cell_padding(self, arguments: dict) -> dict:
        """Execute the set_cell_padding tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        top = arguments.get("top")
        right = arguments.get("right")
        bottom = arguments.get("bottom")
        left = arguments.get("left")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if top is None and right is None and bottom is None and left is None:
            return {"success": False, "message": "At least one padding value (top, right, bottom, left) must be specified"}

        try:
            from signal_bot.google_sheets_client import set_cell_padding_sync

            result = set_cell_padding_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                top=top,
                right=right,
                bottom=bottom,
                left=left
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set cell padding on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting cell padding: {e}")
            return {"success": False, "message": f"Error setting cell padding: {str(e)}"}

    def _execute_set_rich_text(self, arguments: dict) -> dict:
        """Execute the set_rich_text tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        text = arguments.get("text", "")
        runs = arguments.get("runs", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'A1')"}
        if not text:
            return {"success": False, "message": "text is required"}
        if not runs or len(runs) == 0:
            return {"success": False, "message": "At least one format run is required"}

        try:
            from signal_bot.google_sheets_client import set_rich_text_sync

            result = set_rich_text_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                text=text,
                runs=runs
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Applied {len(runs)} format run(s) to {cell}")
            }

        except Exception as e:
            logger.error(f"Error setting rich text: {e}")
            return {"success": False, "message": f"Error setting rich text: {str(e)}"}

    # Batch 6: Charts tool execution methods

    def _execute_create_chart(self, arguments: dict) -> dict:
        """Execute the create_chart tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        data_range = arguments.get("data_range", "").strip()
        chart_type = arguments.get("chart_type", "column")
        title = arguments.get("title", "")
        anchor_cell = arguments.get("anchor_cell", "F1")
        legend_position = arguments.get("legend_position", "bottom")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not data_range:
            return {"success": False, "message": "data_range is required (e.g., 'A1:C10')"}

        try:
            from signal_bot.google_sheets_client import create_chart_sync

            result = create_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                data_range=data_range,
                chart_type=chart_type,
                title=title,
                anchor_cell=anchor_cell,
                legend_position=legend_position
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created {chart_type} chart")
            }

        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return {"success": False, "message": f"Error creating chart: {str(e)}"}

    def _execute_list_charts(self, arguments: dict) -> dict:
        """Execute the list_charts tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_charts_sync

            result = list_charts_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Listed charts")
            }

        except Exception as e:
            logger.error(f"Error listing charts: {e}")
            return {"success": False, "message": f"Error listing charts: {str(e)}"}

    def _execute_update_chart(self, arguments: dict) -> dict:
        """Execute the update_chart tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        chart_id = arguments.get("chart_id")
        title = arguments.get("title")
        chart_type = arguments.get("chart_type")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if chart_id is None:
            return {"success": False, "message": "chart_id is required (use list_charts to get IDs)"}

        try:
            from signal_bot.google_sheets_client import update_chart_sync

            result = update_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                chart_id=int(chart_id),
                title=title,
                chart_type=chart_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Updated chart {chart_id}")
            }

        except Exception as e:
            logger.error(f"Error updating chart: {e}")
            return {"success": False, "message": f"Error updating chart: {str(e)}"}

    def _execute_delete_chart(self, arguments: dict) -> dict:
        """Execute the delete_chart tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        chart_id = arguments.get("chart_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if chart_id is None:
            return {"success": False, "message": "chart_id is required (use list_charts to get IDs)"}

        try:
            from signal_bot.google_sheets_client import delete_chart_sync

            result = delete_chart_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                chart_id=int(chart_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted chart {chart_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting chart: {e}")
            return {"success": False, "message": f"Error deleting chart: {str(e)}"}

    # Batch 7: Pivot Tables tool execution methods

    def _execute_create_pivot_table(self, arguments: dict) -> dict:
        """Execute the create_pivot_table tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        row_group_column = arguments.get("row_group_column")
        value_column = arguments.get("value_column")
        summarize_function = arguments.get("summarize_function", "SUM")
        anchor_cell = arguments.get("anchor_cell", "F1")
        column_group_column = arguments.get("column_group_column")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required (e.g., 'A1:D100')"}
        if row_group_column is None:
            return {"success": False, "message": "row_group_column is required (0-based column index to group by)"}
        if value_column is None:
            return {"success": False, "message": "value_column is required (0-based column index to aggregate)"}

        try:
            from signal_bot.google_sheets_client import create_pivot_table_sync

            result = create_pivot_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                row_group_column=int(row_group_column),
                value_column=int(value_column),
                summarize_function=summarize_function,
                anchor_cell=anchor_cell,
                column_group_column=int(column_group_column) if column_group_column is not None else None
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Created pivot table")
            }

        except Exception as e:
            logger.error(f"Error creating pivot table: {e}")
            return {"success": False, "message": f"Error creating pivot table: {str(e)}"}

    def _execute_delete_pivot_table(self, arguments: dict) -> dict:
        """Execute the delete_pivot_table tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        anchor_cell = arguments.get("anchor_cell", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not anchor_cell:
            return {"success": False, "message": "anchor_cell is required (e.g., 'F1')"}

        try:
            from signal_bot.google_sheets_client import delete_pivot_table_sync

            result = delete_pivot_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                anchor_cell=anchor_cell
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted pivot table at {anchor_cell}")
            }

        except Exception as e:
            logger.error(f"Error deleting pivot table: {e}")
            return {"success": False, "message": f"Error deleting pivot table: {str(e)}"}

    # Text formatting & color tool execution methods (Batch 1)

    def _execute_set_text_format(self, arguments: dict) -> dict:
        """Execute the set_text_format tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import set_text_format_sync

            result = set_text_format_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                bold=arguments.get("bold"),
                italic=arguments.get("italic"),
                underline=arguments.get("underline"),
                strikethrough=arguments.get("strikethrough"),
                font_family=arguments.get("font_family"),
                font_size=arguments.get("font_size")
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Applied text formatting to {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text format: {e}")
            return {"success": False, "message": f"Error setting text format: {str(e)}"}

    def _execute_set_text_color(self, arguments: dict) -> dict:
        """Execute the set_text_color tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        color = arguments.get("color", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not color:
            return {"success": False, "message": "color is required (e.g., '#FF0000' or 'red')"}

        try:
            from signal_bot.google_sheets_client import set_text_color_sync

            result = set_text_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set text color to {color} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting text color: {e}")
            return {"success": False, "message": f"Error setting text color: {str(e)}"}

    def _execute_set_background_color(self, arguments: dict) -> dict:
        """Execute the set_background_color tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        color = arguments.get("color", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}
        if not color:
            return {"success": False, "message": "color is required (e.g., '#FFFF00' or 'yellow')"}

        try:
            from signal_bot.google_sheets_client import set_background_color_sync

            result = set_background_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set background color to {color} on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting background color: {e}")
            return {"success": False, "message": f"Error setting background color: {str(e)}"}

    def _execute_add_hyperlink(self, arguments: dict) -> dict:
        """Execute the add_hyperlink tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        cell = arguments.get("cell", "").strip()
        url = arguments.get("url", "").strip()
        display_text = arguments.get("display_text", "").strip() if arguments.get("display_text") else None

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not cell:
            return {"success": False, "message": "cell is required (e.g., 'A1')"}
        if not url:
            return {"success": False, "message": "url is required"}

        try:
            from signal_bot.google_sheets_client import add_hyperlink_sync

            result = add_hyperlink_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                cell=cell,
                url=url,
                display_text=display_text
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Added hyperlink to {cell}")
            }

        except Exception as e:
            logger.error(f"Error adding hyperlink: {e}")
            return {"success": False, "message": f"Error adding hyperlink: {str(e)}"}

    # Filtering tool execution methods (Batch 2)

    def _execute_set_basic_filter(self, arguments: dict) -> dict:
        """Execute the set_basic_filter tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import set_basic_filter_sync

            result = set_basic_filter_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Enabled filter on {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error setting basic filter: {e}")
            return {"success": False, "message": f"Error setting basic filter: {str(e)}"}

    def _execute_clear_basic_filter(self, arguments: dict) -> dict:
        """Execute the clear_basic_filter tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        sheet_name = arguments.get("sheet_name", "").strip() if arguments.get("sheet_name") else None

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import clear_basic_filter_sync

            result = clear_basic_filter_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Cleared filter")
            }

        except Exception as e:
            logger.error(f"Error clearing basic filter: {e}")
            return {"success": False, "message": f"Error clearing basic filter: {str(e)}"}

    def _execute_create_filter_view(self, arguments: dict) -> dict:
        """Execute the create_filter_view tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        title = arguments.get("title", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not title:
            return {"success": False, "message": "title is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:E100')"}

        try:
            from signal_bot.google_sheets_client import create_filter_view_sync

            result = create_filter_view_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                title=title,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created filter view '{title}'")
            }

        except Exception as e:
            logger.error(f"Error creating filter view: {e}")
            return {"success": False, "message": f"Error creating filter view: {str(e)}"}

    def _execute_delete_filter_view(self, arguments: dict) -> dict:
        """Execute the delete_filter_view tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        filter_view_id = arguments.get("filter_view_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if filter_view_id is None:
            return {"success": False, "message": "filter_view_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_filter_view_sync

            result = delete_filter_view_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                filter_view_id=int(filter_view_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted filter view {filter_view_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting filter view: {e}")
            return {"success": False, "message": f"Error deleting filter view: {str(e)}"}

    # Named & protected range tool execution methods (Batch 3)

    def _execute_create_named_range(self, arguments: dict) -> dict:
        """Execute the create_named_range tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        name = arguments.get("name", "").strip()
        range_notation = arguments.get("range", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not name:
            return {"success": False, "message": "name is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A2:A100')"}

        try:
            from signal_bot.google_sheets_client import create_named_range_sync

            result = create_named_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                name=name,
                range_notation=range_notation
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created named range '{name}'")
            }

        except Exception as e:
            logger.error(f"Error creating named range: {e}")
            return {"success": False, "message": f"Error creating named range: {str(e)}"}

    def _execute_delete_named_range(self, arguments: dict) -> dict:
        """Execute the delete_named_range tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        named_range_id = arguments.get("named_range_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not named_range_id:
            return {"success": False, "message": "named_range_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_named_range_sync

            result = delete_named_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                named_range_id=named_range_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted named range")
            }

        except Exception as e:
            logger.error(f"Error deleting named range: {e}")
            return {"success": False, "message": f"Error deleting named range: {str(e)}"}

    def _execute_list_named_ranges(self, arguments: dict) -> dict:
        """Execute the list_named_ranges tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_named_ranges_sync

            result = list_named_ranges_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Listed named ranges")
            }

        except Exception as e:
            logger.error(f"Error listing named ranges: {e}")
            return {"success": False, "message": f"Error listing named ranges: {str(e)}"}

    def _execute_protect_range(self, arguments: dict) -> dict:
        """Execute the protect_range tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        range_notation = arguments.get("range", "").strip()
        description = arguments.get("description", "").strip() if arguments.get("description") else None
        warning_only = arguments.get("warning_only", False)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_notation:
            return {"success": False, "message": "range is required (e.g., 'A1:D10')"}

        try:
            from signal_bot.google_sheets_client import protect_range_sync

            result = protect_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_notation=range_notation,
                description=description,
                warning_only=warning_only
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Protected {range_notation}")
            }

        except Exception as e:
            logger.error(f"Error protecting range: {e}")
            return {"success": False, "message": f"Error protecting range: {str(e)}"}

    # Find/Replace & Copy/Paste tool execution methods (Batch 4)

    def _execute_find_replace(self, arguments: dict) -> dict:
        """Execute the find_replace tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        find = arguments.get("find", "")
        replacement = arguments.get("replacement", "")
        range_notation = arguments.get("range", "").strip() if arguments.get("range") else None
        match_case = arguments.get("match_case", False)
        match_entire_cell = arguments.get("match_entire_cell", False)
        search_formulas = arguments.get("search_formulas", False)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not find:
            return {"success": False, "message": "find text is required"}

        try:
            from signal_bot.google_sheets_client import find_replace_sync

            result = find_replace_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                find=find,
                replacement=replacement,
                range_notation=range_notation,
                match_case=match_case,
                match_entire_cell=match_entire_cell,
                search_formulas=search_formulas
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Find/replace completed")
            }

        except Exception as e:
            logger.error(f"Error in find/replace: {e}")
            return {"success": False, "message": f"Error in find/replace: {str(e)}"}

    def _execute_copy_paste(self, arguments: dict) -> dict:
        """Execute the copy_paste tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        destination_range = arguments.get("destination_range", "").strip()
        paste_type = arguments.get("paste_type", "all").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required"}
        if not destination_range:
            return {"success": False, "message": "destination_range is required"}

        try:
            from signal_bot.google_sheets_client import copy_paste_sync

            result = copy_paste_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                destination_range=destination_range,
                paste_type=paste_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Copied {source_range} to {destination_range}")
            }

        except Exception as e:
            logger.error(f"Error in copy/paste: {e}")
            return {"success": False, "message": f"Error in copy/paste: {str(e)}"}

    def _execute_cut_paste(self, arguments: dict) -> dict:
        """Execute the cut_paste tool call."""
        if not self.bot_data.get('sheets_enabled'):
            return {"success": False, "message": "Google Sheets not enabled for this bot"}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        source_range = arguments.get("source_range", "").strip()
        destination = arguments.get("destination", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not source_range:
            return {"success": False, "message": "source_range is required"}
        if not destination:
            return {"success": False, "message": "destination is required"}

        try:
            from signal_bot.google_sheets_client import cut_paste_sync

            result = cut_paste_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                source_range=source_range,
                destination=destination
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Moved {source_range} to {destination}")
            }

        except Exception as e:
            logger.error(f"Error in cut/paste: {e}")
            return {"success": False, "message": f"Error in cut/paste: {str(e)}"}

    # Spreadsheet Properties tool execution methods (Batch 8)

    def _execute_set_spreadsheet_timezone(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_timezone tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        timezone = arguments.get("timezone", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not timezone:
            return {"success": False, "message": "timezone is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_timezone_sync

            result = set_spreadsheet_timezone_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                timezone=timezone
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Timezone set to {timezone}")
            }

        except Exception as e:
            logger.error(f"Error setting timezone: {e}")
            return {"success": False, "message": f"Error setting timezone: {str(e)}"}

    def _execute_set_spreadsheet_locale(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_locale tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        locale = arguments.get("locale", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not locale:
            return {"success": False, "message": "locale is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_locale_sync

            result = set_spreadsheet_locale_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                locale=locale
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Locale set to {locale}")
            }

        except Exception as e:
            logger.error(f"Error setting locale: {e}")
            return {"success": False, "message": f"Error setting locale: {str(e)}"}

    def _execute_set_recalculation_interval(self, arguments: dict) -> dict:
        """Execute the set_recalculation_interval tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        interval = arguments.get("interval", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not interval:
            return {"success": False, "message": "interval is required"}

        valid_intervals = ["on_change", "minute", "hour"]
        if interval.lower() not in valid_intervals:
            return {"success": False, "message": f"Invalid interval. Must be one of: {', '.join(valid_intervals)}"}

        try:
            from signal_bot.google_sheets_client import set_recalculation_interval_sync

            result = set_recalculation_interval_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                interval=interval
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Recalculation interval set to {interval}")
            }

        except Exception as e:
            logger.error(f"Error setting recalculation interval: {e}")
            return {"success": False, "message": f"Error setting recalculation interval: {str(e)}"}

    def _execute_get_spreadsheet_properties(self, arguments: dict) -> dict:
        """Execute the get_spreadsheet_properties tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_spreadsheet_properties_sync

            result = get_spreadsheet_properties_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Properties for '{result.get('title', 'spreadsheet')}'"
            }

        except Exception as e:
            logger.error(f"Error getting spreadsheet properties: {e}")
            return {"success": False, "message": f"Error getting properties: {str(e)}"}

    def _execute_set_spreadsheet_theme(self, arguments: dict) -> dict:
        """Execute the set_spreadsheet_theme tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        # Extract optional theme parameters
        primary_font = arguments.get("primary_font")
        text_color = arguments.get("text_color")
        background_color = arguments.get("background_color")
        accent1 = arguments.get("accent1")
        accent2 = arguments.get("accent2")
        accent3 = arguments.get("accent3")
        accent4 = arguments.get("accent4")
        accent5 = arguments.get("accent5")
        accent6 = arguments.get("accent6")
        link_color = arguments.get("link_color")

        # Check at least one parameter is provided
        if not any([primary_font, text_color, background_color, accent1, accent2, accent3, accent4, accent5, accent6, link_color]):
            return {"success": False, "message": "At least one theme property (primary_font or a color) is required"}

        try:
            from signal_bot.google_sheets_client import set_spreadsheet_theme_sync

            result = set_spreadsheet_theme_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                primary_font=primary_font,
                text_color=text_color,
                background_color=background_color,
                accent1=accent1,
                accent2=accent2,
                accent3=accent3,
                accent4=accent4,
                accent5=accent5,
                accent6=accent6,
                link_color=link_color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Theme updated")
            }

        except Exception as e:
            logger.error(f"Error setting theme: {e}")
            return {"success": False, "message": f"Error setting theme: {str(e)}"}

    # Developer Metadata tool execution methods (Batch 9)

    def _execute_set_developer_metadata(self, arguments: dict) -> dict:
        """Execute the set_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        key = arguments.get("key", "").strip()
        value = arguments.get("value", "").strip()
        location = arguments.get("location", "spreadsheet").strip().lower()
        sheet_name = arguments.get("sheet_name")
        start_index = arguments.get("start_index")
        end_index = arguments.get("end_index")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not key:
            return {"success": False, "message": "key is required"}
        if not value:
            return {"success": False, "message": "value is required"}

        valid_locations = ["spreadsheet", "sheet", "row", "column"]
        if location not in valid_locations:
            return {"success": False, "message": f"Invalid location. Must be one of: {', '.join(valid_locations)}"}

        try:
            from signal_bot.google_sheets_client import set_developer_metadata_sync

            result = set_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                key=key,
                value=value,
                location=location,
                sheet_name=sheet_name,
                start_index=start_index,
                end_index=end_index
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Metadata '{key}' set")
            }

        except Exception as e:
            logger.error(f"Error setting developer metadata: {e}")
            return {"success": False, "message": f"Error setting metadata: {str(e)}"}

    def _execute_get_developer_metadata(self, arguments: dict) -> dict:
        """Execute the get_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        key = arguments.get("key")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_developer_metadata_sync

            result = get_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                key=key.strip() if key else None
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Found {result.get('count', 0)} metadata entries")
            }

        except Exception as e:
            logger.error(f"Error getting developer metadata: {e}")
            return {"success": False, "message": f"Error getting metadata: {str(e)}"}

    def _execute_delete_developer_metadata(self, arguments: dict) -> dict:
        """Execute the delete_developer_metadata tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "").strip()
        metadata_id = arguments.get("metadata_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if metadata_id is None:
            return {"success": False, "message": "metadata_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_developer_metadata_sync

            result = delete_developer_metadata_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                metadata_id=int(metadata_id)
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted metadata {metadata_id}")
            }

        except Exception as e:
            logger.error(f"Error deleting developer metadata: {e}")
            return {"success": False, "message": f"Error deleting metadata: {str(e)}"}

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

    # =========================================================================
    # Sheet Properties Extension Tools
    # =========================================================================

    def _execute_hide_sheet(self, arguments: dict) -> dict:
        """Execute the hide_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import hide_sheet_sync

            result = hide_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' is now hidden")
            }

        except Exception as e:
            logger.error(f"Error hiding sheet: {e}")
            return {"success": False, "message": f"Error hiding sheet: {str(e)}"}

    def _execute_show_sheet(self, arguments: dict) -> dict:
        """Execute the show_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import show_sheet_sync

            result = show_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' is now visible")
            }

        except Exception as e:
            logger.error(f"Error showing sheet: {e}")
            return {"success": False, "message": f"Error showing sheet: {str(e)}"}

    def _execute_set_tab_color(self, arguments: dict) -> dict:
        """Execute the set_tab_color tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        color = arguments.get("color", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not color:
            return {"success": False, "message": "color is required"}

        try:
            from signal_bot.google_sheets_client import set_tab_color_sync

            result = set_tab_color_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                color=color
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set tab color for '{sheet_name}' to {color}")
            }

        except Exception as e:
            logger.error(f"Error setting tab color: {e}")
            return {"success": False, "message": f"Error setting tab color: {str(e)}"}

    def _execute_set_right_to_left(self, arguments: dict) -> dict:
        """Execute the set_right_to_left tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        right_to_left = arguments.get("right_to_left", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import set_right_to_left_sync

            result = set_right_to_left_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                right_to_left=right_to_left
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Set RTL for '{sheet_name}'")
            }

        except Exception as e:
            logger.error(f"Error setting RTL: {e}")
            return {"success": False, "message": f"Error setting RTL: {str(e)}"}

    def _execute_get_sheet_properties(self, arguments: dict) -> dict:
        """Execute the get_sheet_properties tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import get_sheet_properties_sync

            result = get_sheet_properties_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Sheet properties retrieved")
            }

        except Exception as e:
            logger.error(f"Error getting sheet properties: {e}")
            return {"success": False, "message": f"Error getting sheet properties: {str(e)}"}

    # =========================================================================
    # Protected Ranges Management Tools
    # =========================================================================

    def _execute_list_protected_ranges(self, arguments: dict) -> dict:
        """Execute the list_protected_ranges tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")  # Optional

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_protected_ranges_sync

            result = list_protected_ranges_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protected ranges retrieved")
            }

        except Exception as e:
            logger.error(f"Error listing protected ranges: {e}")
            return {"success": False, "message": f"Error listing protected ranges: {str(e)}"}

    def _execute_update_protected_range(self, arguments: dict) -> dict:
        """Execute the update_protected_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        protected_range_id = arguments.get("protected_range_id")
        description = arguments.get("description")
        warning_only = arguments.get("warning_only")
        editors = arguments.get("editors")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if protected_range_id is None:
            return {"success": False, "message": "protected_range_id is required"}

        try:
            from signal_bot.google_sheets_client import update_protected_range_sync

            result = update_protected_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                protected_range_id=protected_range_id,
                description=description,
                warning_only=warning_only,
                editors=editors
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protected range updated")
            }

        except Exception as e:
            logger.error(f"Error updating protected range: {e}")
            return {"success": False, "message": f"Error updating protected range: {str(e)}"}

    def _execute_delete_protected_range(self, arguments: dict) -> dict:
        """Execute the delete_protected_range tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        protected_range_id = arguments.get("protected_range_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if protected_range_id is None:
            return {"success": False, "message": "protected_range_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_protected_range_sync

            result = delete_protected_range_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                protected_range_id=protected_range_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Protection removed")
            }

        except Exception as e:
            logger.error(f"Error deleting protected range: {e}")
            return {"success": False, "message": f"Error deleting protected range: {str(e)}"}

    def _execute_protect_sheet(self, arguments: dict) -> dict:
        """Execute the protect_sheet tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        description = arguments.get("description")
        warning_only = arguments.get("warning_only", False)
        editors = arguments.get("editors")
        unprotected_ranges = arguments.get("unprotected_ranges")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import protect_sheet_sync

            result = protect_sheet_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                description=description,
                warning_only=warning_only,
                editors=editors,
                unprotected_ranges=unprotected_ranges
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Sheet '{sheet_name}' protected")
            }

        except Exception as e:
            logger.error(f"Error protecting sheet: {e}")
            return {"success": False, "message": f"Error protecting sheet: {str(e)}"}

    # =========================================================================
    # Filter Views Tools
    # =========================================================================

    def _execute_list_filter_views(self, arguments: dict) -> dict:
        """Execute the list_filter_views tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_filter_views_sync

            result = list_filter_views_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Filter views retrieved")
            }

        except Exception as e:
            logger.error(f"Error listing filter views: {e}")
            return {"success": False, "message": f"Error listing filter views: {str(e)}"}

    # =========================================================================
    # Dimension Groups (Row/Column Grouping) Tools
    # =========================================================================

    def _execute_create_row_group(self, arguments: dict) -> dict:
        """Execute the create_row_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if start_row is None or end_row is None:
            return {"success": False, "message": "start_row and end_row are required"}

        try:
            from signal_bot.google_sheets_client import create_row_group_sync

            result = create_row_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created row group {start_row}-{end_row}")
            }

        except Exception as e:
            logger.error(f"Error creating row group: {e}")
            return {"success": False, "message": f"Error creating row group: {str(e)}"}

    def _execute_create_column_group(self, arguments: dict) -> dict:
        """Execute the create_column_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_column = arguments.get("start_column", "")
        end_column = arguments.get("end_column", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not start_column or not end_column:
            return {"success": False, "message": "start_column and end_column are required"}

        try:
            from signal_bot.google_sheets_client import create_column_group_sync

            result = create_column_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_column=start_column,
                end_column=end_column
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Created column group {start_column}-{end_column}")
            }

        except Exception as e:
            logger.error(f"Error creating column group: {e}")
            return {"success": False, "message": f"Error creating column group: {str(e)}"}

    def _execute_delete_row_group(self, arguments: dict) -> dict:
        """Execute the delete_row_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_row = arguments.get("start_row")
        end_row = arguments.get("end_row")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if start_row is None or end_row is None:
            return {"success": False, "message": "start_row and end_row are required"}

        try:
            from signal_bot.google_sheets_client import delete_row_group_sync

            result = delete_row_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_row=start_row,
                end_row=end_row
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted row group {start_row}-{end_row}")
            }

        except Exception as e:
            logger.error(f"Error deleting row group: {e}")
            return {"success": False, "message": f"Error deleting row group: {str(e)}"}

    def _execute_delete_column_group(self, arguments: dict) -> dict:
        """Execute the delete_column_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        start_column = arguments.get("start_column", "")
        end_column = arguments.get("end_column", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not start_column or not end_column:
            return {"success": False, "message": "start_column and end_column are required"}

        try:
            from signal_bot.google_sheets_client import delete_column_group_sync

            result = delete_column_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                start_column=start_column,
                end_column=end_column
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", f"Deleted column group {start_column}-{end_column}")
            }

        except Exception as e:
            logger.error(f"Error deleting column group: {e}")
            return {"success": False, "message": f"Error deleting column group: {str(e)}"}

    def _execute_collapse_expand_group(self, arguments: dict) -> dict:
        """Execute the collapse_expand_group tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        dimension = arguments.get("dimension", "")
        start_index = arguments.get("start_index", "")
        end_index = arguments.get("end_index", "")
        collapsed = arguments.get("collapsed", True)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}
        if not dimension:
            return {"success": False, "message": "dimension is required (ROWS or COLUMNS)"}
        if not start_index or not end_index:
            return {"success": False, "message": "start_index and end_index are required"}

        try:
            from signal_bot.google_sheets_client import update_dimension_group_sync

            # Convert string indices to appropriate types
            if dimension.upper() == "ROWS":
                s_idx = int(start_index)
                e_idx = int(end_index)
            else:
                s_idx = start_index
                e_idx = end_index

            result = update_dimension_group_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                dimension=dimension,
                start_index=s_idx,
                end_index=e_idx,
                collapsed=collapsed
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Group updated")
            }

        except Exception as e:
            logger.error(f"Error updating dimension group: {e}")
            return {"success": False, "message": f"Error updating dimension group: {str(e)}"}

    def _execute_set_group_control_position(self, arguments: dict) -> dict:
        """Execute the set_group_control_position tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name", "")
        row_control_after = arguments.get("row_control_after")
        column_control_after = arguments.get("column_control_after")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not sheet_name:
            return {"success": False, "message": "sheet_name is required"}

        try:
            from signal_bot.google_sheets_client import set_group_control_position_sync

            result = set_group_control_position_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                row_control_after=row_control_after,
                column_control_after=column_control_after
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": result.get("message", "Group control position updated")
            }

        except Exception as e:
            logger.error(f"Error setting group control position: {e}")
            return {"success": False, "message": f"Error setting group control position: {str(e)}"}

    # ==================== Slicers ====================

    def _execute_list_slicers(self, arguments: dict) -> dict:
        """Execute the list_slicers tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        sheet_name = arguments.get("sheet_name")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_slicers_sync

            result = list_slicers_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {len(result.get('slicers', []))} slicers"
            }

        except Exception as e:
            logger.error(f"Error listing slicers: {e}")
            return {"success": False, "message": f"Error listing slicers: {str(e)}"}

    def _execute_create_slicer(self, arguments: dict) -> dict:
        """Execute the create_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        data_range = arguments.get("data_range", "")
        filter_column_index = arguments.get("filter_column_index")
        title = arguments.get("title")
        row_index = arguments.get("row_index", 0)
        column_index = arguments.get("column_index", 0)

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not data_range:
            return {"success": False, "message": "data_range is required"}
        if filter_column_index is None:
            return {"success": False, "message": "filter_column_index is required"}

        try:
            from signal_bot.google_sheets_client import create_slicer_sync

            result = create_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                data_range=data_range,
                filter_column_index=filter_column_index,
                title=title,
                row_index=row_index,
                column_index=column_index
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer created with ID {result.get('slicer_id')}"
            }

        except Exception as e:
            logger.error(f"Error creating slicer: {e}")
            return {"success": False, "message": f"Error creating slicer: {str(e)}"}

    def _execute_update_slicer(self, arguments: dict) -> dict:
        """Execute the update_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        slicer_id = arguments.get("slicer_id")
        title = arguments.get("title")
        filter_values = arguments.get("filter_values")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if slicer_id is None:
            return {"success": False, "message": "slicer_id is required"}

        try:
            from signal_bot.google_sheets_client import update_slicer_sync

            result = update_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                slicer_id=slicer_id,
                title=title,
                filter_values=filter_values
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer {slicer_id} updated"
            }

        except Exception as e:
            logger.error(f"Error updating slicer: {e}")
            return {"success": False, "message": f"Error updating slicer: {str(e)}"}

    def _execute_delete_slicer(self, arguments: dict) -> dict:
        """Execute the delete_slicer tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        slicer_id = arguments.get("slicer_id")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if slicer_id is None:
            return {"success": False, "message": "slicer_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_slicer_sync

            result = delete_slicer_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                slicer_id=slicer_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Slicer {slicer_id} deleted"
            }

        except Exception as e:
            logger.error(f"Error deleting slicer: {e}")
            return {"success": False, "message": f"Error deleting slicer: {str(e)}"}

    # ==================== Tables ====================

    def _execute_list_tables(self, arguments: dict) -> dict:
        """Execute the list_tables tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}

        try:
            from signal_bot.google_sheets_client import list_tables_sync

            result = list_tables_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {len(result.get('tables', []))} tables"
            }

        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return {"success": False, "message": f"Error listing tables: {str(e)}"}

    def _execute_create_table(self, arguments: dict) -> dict:
        """Execute the create_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        range_str = arguments.get("range", "")
        columns = arguments.get("columns", [])

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not range_str:
            return {"success": False, "message": "range is required"}
        if not columns:
            return {"success": False, "message": "columns is required (list of column definitions)"}

        try:
            from signal_bot.google_sheets_client import create_table_sync

            result = create_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                range_str=range_str,
                columns=columns
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Table created with ID {result.get('table_id')}"
            }

        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return {"success": False, "message": f"Error creating table: {str(e)}"}

    def _execute_delete_table(self, arguments: dict) -> dict:
        """Execute the delete_table tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        table_id = arguments.get("table_id", "")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not table_id:
            return {"success": False, "message": "table_id is required"}

        try:
            from signal_bot.google_sheets_client import delete_table_sync

            result = delete_table_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                table_id=table_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Table {table_id} deleted"
            }

        except Exception as e:
            logger.error(f"Error deleting table: {e}")
            return {"success": False, "message": f"Error deleting table: {str(e)}"}

    def _execute_update_table_column(self, arguments: dict) -> dict:
        """Execute the update_table_column tool call."""
        if not self._sheets_enabled():
            return {"success": False, "message": "Google Sheets not enabled or not connected. Connect via admin panel."}

        spreadsheet_id = arguments.get("spreadsheet_id", "")
        table_id = arguments.get("table_id", "")
        column_index = arguments.get("column_index")
        name = arguments.get("name")
        column_type = arguments.get("column_type")

        if not spreadsheet_id:
            return {"success": False, "message": "spreadsheet_id is required"}
        if not table_id:
            return {"success": False, "message": "table_id is required"}
        if column_index is None:
            return {"success": False, "message": "column_index is required"}

        try:
            from signal_bot.google_sheets_client import update_table_column_sync

            result = update_table_column_sync(
                bot_data=self.bot_data,
                spreadsheet_id=spreadsheet_id,
                table_id=table_id,
                column_index=column_index,
                name=name,
                column_type=column_type
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Column {column_index} updated in table {table_id}"
            }

        except Exception as e:
            logger.error(f"Error updating table column: {e}")
            return {"success": False, "message": f"Error updating table column: {str(e)}"}


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
