"""
Chat log tool schemas for Signal bots.

Tools for searching and summarizing chat history.
"""

# Chat log search tools
CHAT_LOG_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_chat_log",
            "description": "Search the chat history for this group. Use when someone asks about past conversations, wants to find when something was discussed, or asks 'what did we talk about'. Can filter by keyword, member, and date range. Returns messages in reverse chronological order (newest first).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "Text to search for in messages (optional). Case-insensitive."
                    },
                    "member_name": {
                        "type": "string",
                        "description": "Filter to messages from a specific person (optional). Partial name match works."
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start of date range in ISO format, e.g. '2024-01-15' or '2024-01-15T14:30:00' (optional)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End of date range in ISO format (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 25, max: 100)"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chat_log_summary",
            "description": "Get a summary of chat activity for a time period. Shows total messages and message counts by sender. Use for questions like 'how active was the chat last week' or 'who talks the most'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["today", "yesterday", "this_week", "last_week", "this_month", "last_month"],
                        "description": "Time period to summarize"
                    },
                    "member_name": {
                        "type": "string",
                        "description": "Filter to a specific member's activity (optional)"
                    }
                },
                "required": ["period"],
                "additionalProperties": False
            }
        }
    }
]
