"""
Basic tool schemas for Signal bots.

Contains weather, time, Wikipedia, reaction, and dice tools.
"""

# Weather tool for Signal bots
WEATHER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather conditions and forecast for a location. Use this when users ask about weather, temperature, or conditions for any city or location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The location to get weather for. Can be a city name (e.g., 'London'), city and country (e.g., 'Paris, France'), US zip code (e.g., '10001'), UK postcode, or coordinates (e.g., '48.8567,2.3508')."
                },
                "days": {
                    "type": "integer",
                    "description": "Number of forecast days to include (1-7). Default is 1 for just today.",
                    "default": 1
                }
            },
            "required": ["location"],
            "additionalProperties": False
        }
    }
}

# Time/date tools for Signal bots
TIME_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "Get the current date and time for a specific timezone. Common US timezones: America/New_York (Eastern), America/Chicago (Central), America/Denver (Mountain), America/Los_Angeles (Pacific). Use UTC for universal time. Use this when users ask about the current time, date, or day of the week.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone name (e.g., 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'UTC', 'Europe/London'). Defaults to UTC if not specified.",
                        "default": "UTC"
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
            "name": "get_unix_timestamp",
            "description": "Get the current Unix timestamp (seconds since January 1, 1970 UTC). Useful for precise time calculations or when users need a universal timestamp.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }
]

# Wikipedia tools for Signal bots
WIKIPEDIA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_wikipedia",
            "description": "Search Wikipedia for articles matching a query. Returns titles, descriptions, and excerpts. Use this when users want to find information about a topic, person, place, concept, or event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search terms to find Wikipedia articles (e.g., 'Albert Einstein', 'quantum mechanics', 'World War II')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-20)",
                        "default": 5
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_wikipedia_article",
            "description": "Get the summary/introduction of a specific Wikipedia article. Returns the extract, description, URL, and image if available. Use this after searching to get details about a specific article, or when users ask about a specific topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The exact title of the Wikipedia article (e.g., 'Albert Einstein', 'Python (programming language)')"
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_random_wikipedia_article",
            "description": "Get a random Wikipedia article summary. Use this when users want to learn something new, are bored, or explicitly ask for a random fact or article.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }
]

# Reaction tool for Signal bots - allows reacting to messages with emoji
REACTION_TOOL = {
    "type": "function",
    "function": {
        "name": "react_to_message",
        "description": "React to a message in the conversation with an emoji. Messages are numbered [0], [1], etc. at the start of each line. React to messages you find funny, interesting, clever, or wholesome. Be selective - don't react to everything, only messages that genuinely deserve a reaction.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_index": {
                    "type": "integer",
                    "description": "The index of the message to react to (shown as [idx] at the start of each message in the conversation)"
                },
                "emoji": {
                    "type": "string",
                    "description": "A single emoji to react with (e.g., '😂', '❤️', '🔥', '💀', '👍', '🤯')"
                }
            },
            "required": ["message_index", "emoji"],
            "additionalProperties": False
        }
    }
}

# Dice rolling tools for tabletop games (D&D, etc.)
DICE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "roll_dice",
            "description": "Roll dice using standard tabletop notation. Supports modifiers, advantage/disadvantage, and drop/keep mechanics. Use this for D&D, tabletop games, or any random number needs. Examples: '1d20', '2d6+3', '4d6 drop lowest', '1d20 advantage'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notation": {
                        "type": "string",
                        "description": "Dice notation. Format: NdS+M where N=count, S=sides, M=modifier. Supports: 'd20', '2d6+3', '4d6 drop lowest', '1d20 advantage', '1d20 disadvantage', '2d20 keep highest', '1d%' (percentile). Shorthands: 'adv'/'dis', 'dl'/'dh' (drop), 'kh'/'kl' (keep)."
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional label for the roll (e.g., 'attack roll', 'saving throw', 'damage')"
                    }
                },
                "required": ["notation"],
                "additionalProperties": False
            }
        }
    }
]
