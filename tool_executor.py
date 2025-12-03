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
            function_name: Name of the function ('generate_image' or 'get_weather')
            arguments: Dictionary of function arguments

        Returns:
            Dict with 'success' and 'message' keys
        """
        if function_name == "get_weather":
            return self._execute_weather(arguments)

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
