"""
Basic tool executor mixins for Signal bots.

Contains weather, time, Wikipedia, dice, and reaction tool methods.
"""

import logging

logger = logging.getLogger(__name__)


class BasicToolsMixin:
    """Mixin providing basic tool execution methods."""

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

    # Reaction tool
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

    # Dice rolling tool
    def _execute_roll_dice(self, arguments: dict) -> dict:
        """Execute the roll_dice tool call for tabletop gaming."""
        try:
            from signal_bot.dice_client import roll_dice

            notation = arguments.get("notation", "1d20")
            reason = arguments.get("reason")

            result = roll_dice(notation, reason)

            if result.get("success"):
                return {
                    "success": True,
                    "data": {
                        "notation": result.get("notation"),
                        "rolls": result.get("rolls"),
                        "kept": result.get("kept"),
                        "dropped": result.get("dropped"),
                        "modifier": result.get("modifier"),
                        "total": result.get("total"),
                        "critical": result.get("critical"),
                        "fumble": result.get("fumble"),
                        "advantage": result.get("advantage"),
                        "disadvantage": result.get("disadvantage"),
                        "reason": result.get("reason"),
                    },
                    "message": result.get("formatted")
                }
            else:
                return {
                    "success": False,
                    "message": result.get("error", "Unknown dice error")
                }

        except Exception as e:
            logger.error(f"Error rolling dice: {e}")
            return {"success": False, "message": f"Error rolling dice: {str(e)}"}

