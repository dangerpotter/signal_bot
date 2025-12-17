"""
Chat log tool executor mixin for Signal bots.

Provides methods for searching and summarizing chat history.
"""

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


class ChatLogToolsMixin:
    """Mixin providing chat log search tool execution methods."""

    # Type hints for attributes provided by SignalToolExecutorBase
    bot_data: dict
    group_id: str

    def _execute_search_chat_log(self, arguments: dict) -> dict:
        """Execute the search_chat_log tool call."""
        if not self.bot_data.get('chat_log_enabled'):
            return {"success": False, "message": "Chat log tool disabled for this bot"}

        keyword = arguments.get("keyword")
        member_name = arguments.get("member_name")
        start_date_str = arguments.get("start_date")
        end_date_str = arguments.get("end_date")
        limit = min(arguments.get("limit", 25), 100)  # Cap at 100

        # Parse dates if provided
        start_date = None
        end_date = None
        try:
            if start_date_str:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError as e:
            return {"success": False, "message": f"Invalid date format: {e}"}

        try:
            from signal_bot.models import ChatLog

            results = ChatLog.search(
                group_id=self.group_id,
                keyword=keyword,
                member_name=member_name,
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )

            if not results:
                return {
                    "success": True,
                    "message": "No messages found matching your search criteria",
                    "data": {"messages": [], "count": 0}
                }

            # Format results for the AI
            formatted_messages = []
            for msg in results:
                formatted_messages.append({
                    "timestamp": msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if msg.timestamp else None,
                    "sender": msg.sender_name,
                    "is_bot": msg.is_bot,
                    "content": msg.content[:500] if msg.content else ""  # Truncate long messages
                })

            return {
                "success": True,
                "data": {
                    "messages": formatted_messages,
                    "count": len(formatted_messages),
                    "search_params": {
                        "keyword": keyword,
                        "member_name": member_name,
                        "start_date": start_date_str,
                        "end_date": end_date_str
                    }
                },
                "message": f"Found {len(formatted_messages)} message(s)"
            }

        except Exception as e:
            logger.error(f"Error searching chat log: {e}")
            return {"success": False, "message": f"Error searching chat log: {str(e)}"}

    def _execute_get_chat_log_summary(self, arguments: dict) -> dict:
        """Execute the get_chat_log_summary tool call."""
        if not self.bot_data.get('chat_log_enabled'):
            return {"success": False, "message": "Chat log tool disabled for this bot"}

        period = arguments.get("period")
        member_name = arguments.get("member_name")

        if not period:
            return {"success": False, "message": "period is required"}

        # Calculate date range based on period
        now = datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == "today":
            start_date = today
            end_date = now
        elif period == "yesterday":
            start_date = today - timedelta(days=1)
            end_date = today
        elif period == "this_week":
            # Start of current week (Monday)
            start_date = today - timedelta(days=today.weekday())
            end_date = now
        elif period == "last_week":
            # Last week Monday to Sunday
            this_monday = today - timedelta(days=today.weekday())
            start_date = this_monday - timedelta(weeks=1)
            end_date = this_monday
        elif period == "this_month":
            start_date = today.replace(day=1)
            end_date = now
        elif period == "last_month":
            # First day of last month to first day of this month
            first_of_this_month = today.replace(day=1)
            last_month = first_of_this_month - timedelta(days=1)
            start_date = last_month.replace(day=1)
            end_date = first_of_this_month
        else:
            return {"success": False, "message": f"Invalid period: {period}"}

        try:
            from signal_bot.models import ChatLog

            summary = ChatLog.get_summary(
                group_id=self.group_id,
                start_date=start_date,
                end_date=end_date,
                member_name=member_name
            )

            return {
                "success": True,
                "data": summary,
                "message": f"Chat activity summary for {period}: {summary.get('total_messages', 0)} messages"
            }

        except Exception as e:
            logger.error(f"Error getting chat log summary: {e}")
            return {"success": False, "message": f"Error getting chat log summary: {str(e)}"}
