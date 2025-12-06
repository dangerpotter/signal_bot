"""
Member memory tool schemas for Signal bots.

Tools for saving and recalling information about group members.
"""

# Member memory tools for Signal bots - save/recall info about group members
MEMBER_MEMORY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_member_memory",
            "description": "Save information about a group member for future reference. Use when someone shares personal details worth remembering: where they live, their job, hobbies, preferences, life events, or other facts. Be selective - only save genuinely useful info, not trivial conversation details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Name of the group member (as they appear in chat)"
                    },
                    "slot_type": {
                        "type": "string",
                        "enum": ["home_location", "work_info", "interests", "media_prefs", "life_events", "response_prefs", "social_notes"],
                        "description": "Category: home_location (where they live), work_info (job/career), interests (hobbies/activities), media_prefs (movies/music/games), life_events (milestones/plans), response_prefs (communication style), social_notes (relationships/group dynamics)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Concise factual information to remember (e.g., 'Lives in Denver, CO', 'Works as a software engineer at Google', 'Big fan of hiking and skiing')"
                    }
                },
                "required": ["member_name", "slot_type", "content"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_member_memories",
            "description": "ALWAYS call this tool when someone asks 'what do you know about me/them' or asks about stored information. This retrieves ACTUAL saved facts from your persistent memory database. Do NOT guess or make up information - call this tool first to get the real stored data, then respond based on what it returns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Name of the group member to recall information about"
                    }
                },
                "required": ["member_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_group_members",
            "description": "List all known group members and what information is stored about each. ALWAYS call this when asked 'what do you know about everyone' or 'who's in the group'. Returns actual stored data, not guesses.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }
]
