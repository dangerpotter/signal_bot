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
    Limited to image generation only.
    """

    def __init__(
        self,
        bot_data: dict,
        group_id: str,
        send_image_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            bot_data: Bot configuration dict
            group_id: The Signal group ID
            send_image_callback: Optional callback to send the generated image
        """
        self.bot_data = bot_data
        self.group_id = group_id
        self.send_image_callback = send_image_callback

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
