"""
GUI tool executor for the main application.

Bridges OpenRouter tool calls to the ConversationManager's execute_agent_command method.
"""

import logging
from typing import Callable

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
