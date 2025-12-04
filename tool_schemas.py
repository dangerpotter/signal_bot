"""
Tool schemas for OpenRouter native function calling.

Defines OpenAI-compatible tool specifications for agent commands.
These replace the regex-parsed !command syntax with structured function calls.
"""

# Available AI models for the add_ai tool
AVAILABLE_MODELS = [
    "Claude Opus 4.5", "Claude 3 Opus", "Claude Sonnet 4.5", "Claude Haiku 4.5",
    "Claude Sonnet 4", "Claude 4 Opus", "Claude Opus 4.1", "Claude 3.7 Sonnet",
    "Gemini 3 Pro", "Gemini 2.5 Pro", "Gemini 2.5 Flash",
    "GPT 5.1", "GPT 5", "GPT 5 Pro", "GPT 4o", "GPT 4.1",
    "Grok 4", "Grok 3",
    "DeepSeek R1",
    "Kimi K2", "Kimi K2 Thinking",
    "Qwen 3 Max",
]

# Tool definitions in OpenAI function calling format
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text description. Use when you want to create visual content to share with the group. Be specific and detailed in your prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate. Be specific about style, composition, lighting, subject matter, mood, and artistic direction."
                    }
                },
                "required": ["prompt"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "Generate a short video clip using Sora. Use for cinematic scenes or dynamic visual content. Write prompts in film direction style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Film-direction style prompt describing shot type, subject, action, setting, lighting, camera motion, and mood. Be cinematic and specific."
                    }
                },
                "required": ["prompt"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_ai",
            "description": "Invite another AI model to join the conversation. Use to add different perspectives or specialized capabilities. Maximum 5 AIs can participate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": f"The model name to add. Available: {', '.join(AVAILABLE_MODELS[:10])}... and more."
                    },
                    "persona": {
                        "type": "string",
                        "description": "Optional persona or role for the new AI participant (e.g., 'the skeptic', 'chaos agent', 'voice of reason')"
                    }
                },
                "required": ["model"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_ai",
            "description": "Remove an AI participant from the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The AI identifier to remove (e.g., 'AI-3', 'AI-2')"
                    }
                },
                "required": ["target"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mute_self",
            "description": "Skip your next turn to listen and observe the conversation without contributing. Use when you want to let others speak.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_models",
            "description": "Query the list of available AI models that can be invited to the conversation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }
]

# Signal bot only supports image generation
SIGNAL_TOOLS = [
    tool for tool in AGENT_TOOLS
    if tool["function"]["name"] == "generate_image"
]

# Finance tools for Signal bots
FINANCE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_quote",
            "description": "Get current stock/crypto price and key metrics including market cap, P/E ratio, 52-week range, and volume. Works with stocks (AAPL, MSFT), ETFs (SPY, QQQ), and crypto (BTC-USD, ETH-USD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'MSFT', 'BTC-USD', 'ETH-USD')"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_news",
            "description": "Get recent news articles for a stock or cryptocurrency.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'TSLA', 'BTC-USD')"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of news articles to return (1-20)",
                        "default": 5
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_stocks",
            "description": "Search for stocks, ETFs, or crypto by name or symbol. Use when you need to find a ticker symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term - company name, ticker, or keyword (e.g., 'Apple', 'electric vehicles', 'bitcoin')"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Maximum results to return (1-25)",
                        "default": 10
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
            "name": "get_top_stocks",
            "description": "Get top performing stocks or ETFs by sector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type of entity: 'companies' or 'etfs'",
                        "enum": ["companies", "etfs"],
                        "default": "companies"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Market sector",
                        "enum": ["technology", "healthcare", "financial-services", "consumer-cyclical", "consumer-defensive", "energy", "industrials", "basic-materials", "real-estate", "utilities", "communication-services"],
                        "default": "technology"
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of results (1-25)",
                        "default": 10
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
            "name": "get_price_history",
            "description": "Get historical price data for charting or analysis. Returns OHLCV data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'SPY', 'BTC-USD')"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period for data",
                        "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"],
                        "default": "1mo"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval/granularity",
                        "enum": ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
                        "default": "1d"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_options",
            "description": "Get options chain data including calls and puts with strike prices, bids, asks, and implied volatility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'SPY', 'TSLA')"
                    },
                    "option_type": {
                        "type": "string",
                        "description": "Type of options to return",
                        "enum": ["call", "put", "both"],
                        "default": "both"
                    },
                    "date": {
                        "type": "string",
                        "description": "Expiration date in YYYY-MM-DD format (optional, defaults to nearest expiration)"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_earnings",
            "description": "Get earnings data including historical earnings, EPS, and next earnings date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'MSFT', 'GOOGL')"
                    },
                    "period": {
                        "type": "string",
                        "description": "Earnings period type",
                        "enum": ["annual", "quarterly"],
                        "default": "quarterly"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_analyst_ratings",
            "description": "Get analyst recommendations (buy/hold/sell counts), price targets (low/mean/high), and recent upgrades/downgrades. Shows what Wall Street analysts think about a stock.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'TSLA', 'GOOGL')"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dividends",
            "description": "Get dividend information including yield, payment dates, ex-dividend date, payout ratio, and stock split history. Use this when someone asks about dividends or income investing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'KO', 'JNJ', 'VYM')"
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "Include last 8 dividend payment amounts",
                        "default": False
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_financials",
            "description": "Get key financial metrics: revenue, profit margins, assets, debt, and cash flow. Returns highlights from income statement, balance sheet, and cash flow statement - not full statements.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'MSFT', 'AMZN')"
                    },
                    "period": {
                        "type": "string",
                        "description": "Annual or quarterly financials",
                        "enum": ["annual", "quarterly"],
                        "default": "annual"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_holders",
            "description": "Get ownership information: percentage held by insiders and institutions, top institutional holders (Vanguard, Blackrock, etc.), and recent insider buying/selling activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'AAPL', 'NVDA', 'TSLA')"
                    }
                },
                "required": ["symbol"],
                "additionalProperties": False
            }
        }
    }
]

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

# Google Sheets tools for Signal bots
SHEETS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_spreadsheet",
            "description": "Create a new Google Sheets spreadsheet for tracking data, expenses, lists, or any collaborative information. The spreadsheet will be registered for this group and can be accessed later. Use when someone wants to track something, create a list, or organize data collaboratively.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the spreadsheet (e.g., 'Colorado Trip Expenses 2025', 'Movie Watchlist', 'Fantasy Football Standings')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this spreadsheet is for",
                        "default": ""
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
            "name": "list_spreadsheets",
            "description": "List all spreadsheets that have been created for this group. Returns titles, descriptions, URLs, and when they were last accessed. Use when someone asks what sheets exist or wants to find a specific one.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_sheet",
            "description": "Read data from a spreadsheet range. Returns the values as a table. Use when someone wants to see what's in a sheet, check totals, or view the current data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID (from list_spreadsheets or create_spreadsheet)"
                    },
                    "range": {
                        "type": "string",
                        "description": "The range to read in A1 notation (e.g., 'Sheet1!A1:D10', 'Sheet1!A:D' for full columns). Default reads the first 100 rows.",
                        "default": "Sheet1!A1:Z100"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_sheet",
            "description": "Write data to a specific range in a spreadsheet. Overwrites existing data in that range. Use for setting up headers, updating specific cells, or replacing a section of data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Target range in A1 notation (e.g., 'Sheet1!A1' to start at A1, 'Sheet1!A1:C3' for a specific area)"
                    },
                    "values": {
                        "type": "array",
                        "description": "2D array of values to write. Each inner array is a row. Example: [[\"Name\", \"Amount\"], [\"John\", 50], [\"Jane\", 75]]",
                        "items": {
                            "type": "array",
                            "items": {}
                        }
                    }
                },
                "required": ["spreadsheet_id", "range", "values"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_row_to_sheet",
            "description": "Add a new row of data to a spreadsheet. Appends to the end of existing data. By default adds timestamp and attribution columns (for expense tracking, logging). Set include_metadata to false for simple data entry where you want values placed directly in columns (like adding a member name to column A).",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "values": {
                        "type": "array",
                        "description": "Array of values for the new row. With include_metadata=true (default), timestamp and attribution are prepended. With include_metadata=false, values go directly into columns starting at A. Example: [\"Jeff\"] with include_metadata=false adds Jeff to column A.",
                        "items": {}
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "If true (default), prepends timestamp and who-added-it columns. Set to false for simple data entry where you want values in columns as-is (e.g., adding a name to a member list)."
                    }
                },
                "required": ["spreadsheet_id", "values"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_sheets",
            "description": "Search for spreadsheets by title. Use when you need to find a specific sheet but don't have the ID, or when someone references a sheet by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term to find in spreadsheet titles (e.g., 'Colorado', 'expenses', 'watchlist')"
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
            "name": "format_columns",
            "description": "Format columns in a spreadsheet (e.g., as currency, percentage, date). Use when someone asks to format columns to display values a certain way, like '$' for money or '%' for percentages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "columns": {
                        "type": "string",
                        "description": "Column range in A1 notation (e.g., 'B' for single column, 'B:E' for columns B through E)"
                    },
                    "format_type": {
                        "type": "string",
                        "enum": ["CURRENCY", "PERCENT", "NUMBER", "DATE", "TEXT"],
                        "description": "Type of format: CURRENCY ($), PERCENT (%), NUMBER (decimal), DATE, or TEXT (plain)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional custom pattern (e.g., '$#,##0.00' for currency). Uses sensible defaults if not provided."
                    }
                },
                "required": ["spreadsheet_id", "columns", "format_type"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_range",
            "description": "Clear values from a range in a spreadsheet. Use when someone asks to clear, empty, or erase data from cells. Does not delete rows/columns, just clears the contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range to clear in A1 notation (e.g., 'A1:C10', 'B:B' for entire column B, 'Sheet1!A1:D5' for specific sheet)"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_rows",
            "description": "Delete rows from a spreadsheet. Use when someone asks to remove or delete entire rows. This shifts other rows up.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "start_row": {
                        "type": "integer",
                        "description": "First row to delete (1-indexed, so row 1 is the first row)"
                    },
                    "end_row": {
                        "type": "integer",
                        "description": "Last row to delete (1-indexed, inclusive). Omit to delete just the start_row."
                    }
                },
                "required": ["spreadsheet_id", "start_row"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_columns",
            "description": "Delete columns from a spreadsheet. Use when someone asks to remove or delete entire columns. This shifts other columns left.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "columns": {
                        "type": "string",
                        "description": "Column(s) to delete in letter notation (e.g., 'C' for single column, 'C:E' for columns C through E)"
                    }
                },
                "required": ["spreadsheet_id", "columns"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_rows",
            "description": "Insert empty rows into a spreadsheet. Use when someone asks to add new rows. Existing rows shift down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "row": {
                        "type": "integer",
                        "description": "Row number where new rows will be inserted (1-indexed). Existing content at this row moves down."
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of rows to insert (default 1)"
                    }
                },
                "required": ["spreadsheet_id", "row"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_columns",
            "description": "Insert empty columns into a spreadsheet. Use when someone asks to add new columns. Existing columns shift right.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "column": {
                        "type": "string",
                        "description": "Column letter where new columns will be inserted (e.g., 'C'). Existing content at this column moves right."
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of columns to insert (default 1)"
                    }
                },
                "required": ["spreadsheet_id", "column"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_sheet",
            "description": "Add a new sheet/tab to a spreadsheet. Use when someone wants to create a new tab.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Name for the new sheet/tab"
                    }
                },
                "required": ["spreadsheet_id", "title"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_sheet",
            "description": "Delete a sheet/tab from a spreadsheet. Use when someone wants to remove an entire tab. Cannot delete the last remaining sheet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet/tab to delete"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_sheet",
            "description": "Rename a sheet/tab in a spreadsheet. Use when someone wants to change a tab's name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "old_name": {
                        "type": "string",
                        "description": "Current name of the sheet/tab"
                    },
                    "new_name": {
                        "type": "string",
                        "description": "New name for the sheet/tab"
                    }
                },
                "required": ["spreadsheet_id", "old_name", "new_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_rows",
            "description": "Freeze rows at the top of a sheet so they stay visible when scrolling. Use when someone wants to keep headers visible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "num_rows": {
                        "type": "integer",
                        "description": "Number of rows to freeze (e.g., 1 for just the header row). Use 0 to unfreeze."
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: specific sheet name. Defaults to first sheet if not provided."
                    }
                },
                "required": ["spreadsheet_id", "num_rows"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_columns",
            "description": "Freeze columns at the left of a sheet so they stay visible when scrolling. Use when someone wants to keep labels visible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "num_columns": {
                        "type": "integer",
                        "description": "Number of columns to freeze (e.g., 1 for just column A). Use 0 to unfreeze."
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: specific sheet name. Defaults to first sheet if not provided."
                    }
                },
                "required": ["spreadsheet_id", "num_columns"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_range",
            "description": "Sort data in a spreadsheet by a column. Use when someone asks to sort data alphabetically, by number, by date, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "column": {
                        "type": "string",
                        "description": "Column to sort by (e.g., 'B' to sort by column B)"
                    },
                    "ascending": {
                        "type": "boolean",
                        "description": "True for A-Z/smallest-first (default), False for Z-A/largest-first"
                    },
                    "has_header": {
                        "type": "boolean",
                        "description": "True if first row is a header and should not be sorted (default True)"
                    }
                },
                "required": ["spreadsheet_id", "column"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "auto_resize_columns",
            "description": "Auto-resize columns to fit their content. Use when columns are too narrow or too wide for the data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "columns": {
                        "type": "string",
                        "description": "Optional: column range to resize (e.g., 'A:E'). If not provided, resizes all columns."
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "merge_cells",
            "description": "Merge multiple cells into one. Use for creating headers that span multiple columns, or combining cells for layout purposes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range of cells to merge in A1 notation (e.g., 'A1:C1' to merge first 3 cells of row 1)"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "unmerge_cells",
            "description": "Unmerge previously merged cells back into individual cells.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range of merged cells to unmerge in A1 notation (e.g., 'A1:C1')"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    # Batch 4: Formatting & Validation
    {
        "type": "function",
        "function": {
            "name": "conditional_format",
            "description": "Add conditional formatting to highlight cells based on their values. Use when someone asks to highlight values greater/less than a threshold, color cells containing certain text, or show empty/filled cells differently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range to format in A1 notation (e.g., 'B2:B100')"
                    },
                    "rule_type": {
                        "type": "string",
                        "enum": ["greater_than", "less_than", "equals", "contains", "not_empty", "is_empty"],
                        "description": "Type of condition to check"
                    },
                    "condition_value": {
                        "type": "string",
                        "description": "Value to compare against (e.g., '100' for greater_than 100, 'error' for contains 'error'). Not needed for not_empty/is_empty."
                    },
                    "format_type": {
                        "type": "string",
                        "enum": ["background", "text"],
                        "description": "What to color: 'background' for cell fill, 'text' for font color. Default: background"
                    },
                    "color": {
                        "type": "string",
                        "enum": ["red", "green", "yellow", "orange", "blue", "purple"],
                        "description": "Color to apply when condition is met. Default: red"
                    }
                },
                "required": ["spreadsheet_id", "range", "rule_type"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "data_validation",
            "description": "Add data validation rules to cells. Use for dropdown lists, restricting to number ranges, or adding checkboxes. Helps prevent invalid data entry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range to validate in A1 notation (e.g., 'C2:C100')"
                    },
                    "validation_type": {
                        "type": "string",
                        "enum": ["dropdown", "number_range", "date", "checkbox"],
                        "description": "Type of validation: dropdown (list of options), number_range (min/max), date (valid dates only), checkbox (true/false)"
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "For dropdown: list of allowed values (e.g., ['Yes', 'No', 'Maybe'])"
                    },
                    "min_value": {
                        "type": "number",
                        "description": "For number_range: minimum allowed value"
                    },
                    "max_value": {
                        "type": "number",
                        "description": "For number_range: maximum allowed value"
                    },
                    "strict": {
                        "type": "boolean",
                        "description": "If true (default), reject invalid input. If false, show warning but allow."
                    }
                },
                "required": ["spreadsheet_id", "range", "validation_type"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "alternating_colors",
            "description": "Add alternating row colors (zebra stripes) to make data easier to read. Applies a header color and two alternating band colors for data rows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range to apply banding in A1 notation (e.g., 'A1:E100')"
                    },
                    "header_color": {
                        "type": "string",
                        "enum": ["blue", "green", "gray", "orange", "purple", "red"],
                        "description": "Color for the header row. Default: blue"
                    },
                    "first_band_color": {
                        "type": "string",
                        "enum": ["white", "lightgray", "lightblue", "lightgreen", "lightyellow", "lightpurple"],
                        "description": "Color for odd data rows. Default: white"
                    },
                    "second_band_color": {
                        "type": "string",
                        "enum": ["white", "lightgray", "lightblue", "lightgreen", "lightyellow", "lightpurple"],
                        "description": "Color for even data rows. Default: lightgray"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    # Batch 5: Cell Enhancements
    {
        "type": "function",
        "function": {
            "name": "add_note",
            "description": "Add a note (comment) to a specific cell. Notes appear as small triangles in the corner and show on hover. Use for adding context, explanations, or reminders to data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "cell": {
                        "type": "string",
                        "description": "Cell in A1 notation (e.g., 'B2', 'D5')"
                    },
                    "note": {
                        "type": "string",
                        "description": "The note text to add. Use empty string to clear an existing note."
                    }
                },
                "required": ["spreadsheet_id", "cell", "note"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_borders",
            "description": "Add borders around cells to create visual structure. Use for tables, separating sections, or highlighting important data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10')"
                    },
                    "border_style": {
                        "type": "string",
                        "enum": ["solid", "dashed", "dotted", "double", "thick", "medium", "none"],
                        "description": "Style of the border line. Default: solid"
                    },
                    "color": {
                        "type": "string",
                        "enum": ["black", "gray", "lightgray", "red", "blue", "green"],
                        "description": "Border color. Default: black"
                    },
                    "sides": {
                        "type": "string",
                        "enum": ["all", "outer", "inner", "top", "bottom", "left", "right"],
                        "description": "Which sides to add borders: 'all' (every cell edge), 'outer' (just the perimeter), 'inner' (grid lines only), or specific sides. Default: all"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_alignment",
            "description": "Set text alignment and wrapping for cells. Use for centering headers, right-aligning numbers, or wrapping long text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10')"
                    },
                    "horizontal": {
                        "type": "string",
                        "enum": ["left", "center", "right"],
                        "description": "Horizontal text alignment"
                    },
                    "vertical": {
                        "type": "string",
                        "enum": ["top", "middle", "bottom"],
                        "description": "Vertical text alignment"
                    },
                    "wrap": {
                        "type": "string",
                        "enum": ["overflow", "clip", "wrap"],
                        "description": "Text wrapping: 'overflow' (spill into next cell), 'clip' (cut off), 'wrap' (wrap to multiple lines)"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    # Batch 10: Additional Cell Formatting
    {
        "type": "function",
        "function": {
            "name": "set_text_direction",
            "description": "Set text direction for cells. Use for right-to-left languages like Arabic, Hebrew, or Persian. Can also force left-to-right for specific cells.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10')"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["left_to_right", "right_to_left"],
                        "description": "Text direction: 'left_to_right' (default for English) or 'right_to_left' (for Arabic, Hebrew, etc.)"
                    }
                },
                "required": ["spreadsheet_id", "range", "direction"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_text_rotation",
            "description": "Rotate text within cells. Use for angled column headers, vertical labels, or creative layouts. Can specify an angle or make text stack vertically.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10')"
                    },
                    "angle": {
                        "type": "integer",
                        "description": "Rotation angle in degrees, from -90 to 90. Positive angles tilt upward, negative tilt downward. Use 0 to reset to horizontal."
                    },
                    "vertical": {
                        "type": "boolean",
                        "description": "If true, stack characters vertically (one letter per line). Cannot be combined with angle."
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_cell_padding",
            "description": "Set inner padding (spacing) within cells. Adds space between the cell content and its borders. Use to improve readability or create visual breathing room.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10')"
                    },
                    "top": {
                        "type": "integer",
                        "description": "Top padding in pixels"
                    },
                    "right": {
                        "type": "integer",
                        "description": "Right padding in pixels"
                    },
                    "bottom": {
                        "type": "integer",
                        "description": "Bottom padding in pixels"
                    },
                    "left": {
                        "type": "integer",
                        "description": "Left padding in pixels"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_rich_text",
            "description": "Apply mixed formatting within a single cell. Different parts of the text can have different formatting (bold, italic, colors, etc.). Useful for highlighting specific words or creating styled cell content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "cell": {
                        "type": "string",
                        "description": "Single cell in A1 notation (e.g., 'A1', 'Sheet1!B2')"
                    },
                    "text": {
                        "type": "string",
                        "description": "The full text content of the cell"
                    },
                    "runs": {
                        "type": "array",
                        "description": "Array of format runs. Each run starts at an index and applies formatting until the next run.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "start": {
                                    "type": "integer",
                                    "description": "Character index where this format starts (0-based)"
                                },
                                "bold": {
                                    "type": "boolean",
                                    "description": "Make text bold"
                                },
                                "italic": {
                                    "type": "boolean",
                                    "description": "Make text italic"
                                },
                                "underline": {
                                    "type": "boolean",
                                    "description": "Underline text"
                                },
                                "strikethrough": {
                                    "type": "boolean",
                                    "description": "Strikethrough text"
                                },
                                "color": {
                                    "type": "string",
                                    "description": "Text color as hex (#FF0000) or name (red, blue, etc.)"
                                },
                                "font_size": {
                                    "type": "integer",
                                    "description": "Font size in points"
                                },
                                "font_family": {
                                    "type": "string",
                                    "description": "Font name (e.g., 'Arial', 'Times New Roman')"
                                }
                            },
                            "required": ["start"]
                        }
                    }
                },
                "required": ["spreadsheet_id", "cell", "text", "runs"],
                "additionalProperties": False
            }
        }
    },
    # Batch 6: Charts
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "Create an embedded chart from spreadsheet data. Use to visualize data as bar charts, line graphs, pie charts, etc. The first column becomes labels (X-axis), other columns become data series.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "data_range": {
                        "type": "string",
                        "description": "Data range in A1 notation (e.g., 'A1:C10'). First column = labels, other columns = values."
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "column", "pie", "area", "scatter"],
                        "description": "Type of chart. Default: column"
                    },
                    "title": {
                        "type": "string",
                        "description": "Chart title (optional)"
                    },
                    "anchor_cell": {
                        "type": "string",
                        "description": "Cell where chart top-left corner is placed (e.g., 'F1'). Default: F1"
                    },
                    "legend_position": {
                        "type": "string",
                        "enum": ["bottom", "top", "left", "right", "none"],
                        "description": "Where to show the legend. Default: bottom"
                    }
                },
                "required": ["spreadsheet_id", "data_range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_charts",
            "description": "List all charts in a spreadsheet. Returns chart IDs and titles, useful before updating or deleting charts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_chart",
            "description": "Update an existing chart's properties like title or chart type. Use list_charts first to get the chart_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "chart_id": {
                        "type": "integer",
                        "description": "The chart ID (get from list_charts)"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the chart"
                    },
                    "chart_type": {
                        "type": "string",
                        "enum": ["bar", "line", "column", "area", "scatter"],
                        "description": "New chart type (cannot change to/from pie)"
                    }
                },
                "required": ["spreadsheet_id", "chart_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_chart",
            "description": "Delete an embedded chart from a spreadsheet. Use list_charts first to get the chart_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "chart_id": {
                        "type": "integer",
                        "description": "The chart ID to delete (get from list_charts)"
                    }
                },
                "required": ["spreadsheet_id", "chart_id"],
                "additionalProperties": False
            }
        }
    },
    # Batch 7: Pivot Tables
    {
        "type": "function",
        "function": {
            "name": "create_pivot_table",
            "description": "Create a pivot table with multi-dimensional grouping, date/histogram rules, and multiple aggregations. Column indexes are 0-based (A=0, B=1, C=2). Supports date grouping (YEAR_MONTH, QUARTER, etc.) and histogram buckets for numeric data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "source_range": {
                        "type": "string",
                        "description": "Source data range in A1 notation (e.g., 'A1:D100'). Should include headers."
                    },
                    "row_groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "integer", "description": "Column index (0-based) to group by"},
                                "date_group_rule": {"type": "string", "enum": ["SECOND", "MINUTE", "HOUR", "HOUR_MINUTE", "HOUR_MINUTE_AMPM", "DAY_OF_WEEK", "DAY_OF_YEAR", "DAY_OF_MONTH", "DAY_MONTH", "MONTH", "QUARTER", "YEAR", "YEAR_MONTH", "YEAR_QUARTER", "YEAR_MONTH_DAY"], "description": "Group dates by this time unit"},
                                "histogram_rule": {"type": "object", "properties": {"interval": {"type": "number"}, "start": {"type": "number"}, "end": {"type": "number"}}, "description": "Group numbers into buckets. interval required, start/end optional."},
                                "manual_group_rule": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "items"]}, "description": "Custom grouping of values. E.g., [{\"name\": \"East\", \"items\": [\"NY\", \"MA\"]}, {\"name\": \"West\", \"items\": [\"CA\", \"OR\"]}]"},
                                "label": {"type": "string", "description": "Custom label for this group"},
                                "show_totals": {"type": "boolean", "description": "Show totals for this group (overrides global)"},
                                "sort_order": {"type": "string", "enum": ["ASCENDING", "DESCENDING"], "description": "Sort order (overrides global)"},
                                "repeat_headings": {"type": "boolean", "description": "Repeat headings for hierarchical groups"},
                                "group_limit": {"type": "integer", "description": "Maximum number of items to show in this group (top N)"}
                            },
                            "required": ["column"]
                        },
                        "description": "Row groupings. Simple: [{\"column\": 0}]. With date rule: [{\"column\": 0, \"date_group_rule\": \"YEAR_MONTH\"}]. With limit: [{\"column\": 0, \"group_limit\": 10}]"
                    },
                    "values": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "integer", "description": "Column index (0-based) to aggregate"},
                                "function": {"type": "string", "enum": ["SUM", "COUNT", "AVERAGE", "MIN", "MAX", "COUNTA", "COUNTUNIQUE", "MEDIAN", "PRODUCT", "STDEV", "STDEVP", "VAR", "VARP"], "description": "Aggregation function. Default: SUM"},
                                "name": {"type": "string", "description": "Custom display name (e.g., 'Total Sales')"},
                                "calculated_display_type": {"type": "string", "enum": ["PERCENT_OF_ROW_TOTAL", "PERCENT_OF_COLUMN_TOTAL", "PERCENT_OF_GRAND_TOTAL"], "description": "Show as percentage"}
                            },
                            "required": ["column"]
                        },
                        "description": "Value columns to aggregate. E.g., [{\"column\": 2, \"function\": \"SUM\", \"name\": \"Total\"}, {\"column\": 2, \"function\": \"COUNT\"}]"
                    },
                    "anchor_cell": {
                        "type": "string",
                        "description": "Cell where pivot table is placed (e.g., 'F1'). Default: F1"
                    },
                    "column_groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "integer", "description": "Column index (0-based)"},
                                "date_group_rule": {"type": "string", "enum": ["SECOND", "MINUTE", "HOUR", "HOUR_MINUTE", "HOUR_MINUTE_AMPM", "DAY_OF_WEEK", "DAY_OF_YEAR", "DAY_OF_MONTH", "DAY_MONTH", "MONTH", "QUARTER", "YEAR", "YEAR_MONTH", "YEAR_QUARTER", "YEAR_MONTH_DAY"], "description": "Group dates by this time unit"},
                                "histogram_rule": {"type": "object", "properties": {"interval": {"type": "number"}, "start": {"type": "number"}, "end": {"type": "number"}}, "description": "Group numbers into buckets"},
                                "manual_group_rule": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}}}, "required": ["name", "items"]}, "description": "Custom grouping of values"},
                                "label": {"type": "string", "description": "Custom label for this group"},
                                "show_totals": {"type": "boolean", "description": "Show totals for this group"},
                                "sort_order": {"type": "string", "enum": ["ASCENDING", "DESCENDING"], "description": "Sort order"},
                                "group_limit": {"type": "integer", "description": "Maximum number of items to show"}
                            },
                            "required": ["column"]
                        },
                        "description": "Column groupings (cross-tabulation). E.g., [{\"column\": 3, \"date_group_rule\": \"QUARTER\"}]"
                    },
                    "show_totals": {
                        "type": "boolean",
                        "description": "Show row and column totals. Default: true"
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["ASCENDING", "DESCENDING"],
                        "description": "Default sort order for groups. Default: ASCENDING"
                    },
                    "value_layout": {
                        "type": "string",
                        "enum": ["HORIZONTAL", "VERTICAL"],
                        "description": "Layout for multiple values - HORIZONTAL (as columns) or VERTICAL (as rows). Default: HORIZONTAL"
                    },
                    "filter_specs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "integer", "description": "Column index (0-based) to filter"},
                                "visible_values": {"type": "array", "items": {"type": "string"}, "description": "Only include rows with these values"},
                                "condition_type": {"type": "string", "enum": ["NUMBER_GREATER", "NUMBER_GREATER_THAN_EQ", "NUMBER_LESS", "NUMBER_LESS_THAN_EQ", "NUMBER_EQ", "NUMBER_NOT_EQ", "NUMBER_BETWEEN", "NUMBER_NOT_BETWEEN", "TEXT_CONTAINS", "TEXT_NOT_CONTAINS", "TEXT_STARTS_WITH", "TEXT_ENDS_WITH", "TEXT_EQ", "TEXT_IS_EMAIL", "TEXT_IS_URL", "DATE_EQ", "DATE_BEFORE", "DATE_AFTER", "DATE_ON_OR_BEFORE", "DATE_ON_OR_AFTER", "DATE_BETWEEN", "DATE_NOT_BETWEEN", "DATE_IS_VALID", "BLANK", "NOT_BLANK"], "description": "Condition type for filtering"},
                                "condition_values": {"type": "array", "items": {"type": "string"}, "description": "Values for the condition (1 for most, 2 for BETWEEN)"},
                                "visible_by_default": {"type": "boolean", "description": "If true, show all except visible_values. Default: true"}
                            },
                            "required": ["column"]
                        },
                        "description": "Filters to apply to source data before aggregation. E.g., [{\"column\": 0, \"visible_values\": [\"Active\", \"Pending\"]}] or [{\"column\": 2, \"condition_type\": \"NUMBER_GREATER\", \"condition_values\": [\"100\"]}]"
                    }
                },
                "required": ["spreadsheet_id", "source_range", "row_groups", "values"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_pivot_table",
            "description": "Delete a pivot table from a spreadsheet. Specify the anchor cell where the pivot table starts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "anchor_cell": {
                        "type": "string",
                        "description": "Cell where pivot table is anchored (e.g., 'F1')"
                    }
                },
                "required": ["spreadsheet_id", "anchor_cell"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_pivot_tables",
            "description": "List all pivot tables in a spreadsheet. Returns anchor cell, source range, and summary of row/column groups for each.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_pivot_table",
            "description": "Get detailed configuration of a specific pivot table. Returns row groups, column groups, values, filters, and all settings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "anchor_cell": {
                        "type": "string",
                        "description": "Cell where pivot table is anchored (e.g., 'F1')"
                    }
                },
                "required": ["spreadsheet_id", "anchor_cell"],
                "additionalProperties": False
            }
        }
    },
    # Batch 1: Text Formatting & Colors
    {
        "type": "function",
        "function": {
            "name": "set_text_format",
            "description": "Apply rich text formatting to a range of cells. Set bold, italic, underline, strikethrough, font family, and font size. Only specified options are applied - omit any you don't want to change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10', 'Sheet1!B2:C5')"
                    },
                    "bold": {
                        "type": "boolean",
                        "description": "Make text bold"
                    },
                    "italic": {
                        "type": "boolean",
                        "description": "Make text italic"
                    },
                    "underline": {
                        "type": "boolean",
                        "description": "Underline text"
                    },
                    "strikethrough": {
                        "type": "boolean",
                        "description": "Strikethrough text"
                    },
                    "font_family": {
                        "type": "string",
                        "description": "Font name (e.g., 'Arial', 'Times New Roman', 'Courier New')"
                    },
                    "font_size": {
                        "type": "integer",
                        "description": "Font size in points (e.g., 10, 12, 14)"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_text_color",
            "description": "Set the text (foreground) color for a range of cells. Use hex codes like '#FF0000' or color names like 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'gray', 'cyan', 'magenta'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10', 'Sheet1!B2:C5')"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color as hex code (#FF0000) or name (red, blue, green, etc.)"
                    }
                },
                "required": ["spreadsheet_id", "range", "color"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_background_color",
            "description": "Set the background (fill) color for a range of cells. Use hex codes like '#FFFF00' or color names like 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink', 'black', 'white', 'gray', 'cyan', 'magenta'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:D10', 'Sheet1!B2:C5')"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color as hex code (#FFFF00) or name (red, blue, yellow, etc.)"
                    }
                },
                "required": ["spreadsheet_id", "range", "color"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_hyperlink",
            "description": "Add a clickable hyperlink to a cell. The cell will display the URL or custom text and open the link when clicked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "cell": {
                        "type": "string",
                        "description": "Cell in A1 notation (e.g., 'A1', 'Sheet1!B2')"
                    },
                    "url": {
                        "type": "string",
                        "description": "The URL to link to"
                    },
                    "display_text": {
                        "type": "string",
                        "description": "Optional text to display instead of the URL"
                    }
                },
                "required": ["spreadsheet_id", "cell", "url"],
                "additionalProperties": False
            }
        }
    },
    # Batch 2: Filtering
    {
        "type": "function",
        "function": {
            "name": "set_basic_filter",
            "description": "Enable auto-filter dropdown menus on a range of data. Creates filter buttons in the header row that allow filtering and sorting the data below.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation covering the data to filter (e.g., 'A1:E100'). Include header row."
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clear_basic_filter",
            "description": "Remove the basic filter from a sheet. This removes the filter dropdown buttons but keeps the data intact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet to clear filter from. Defaults to first sheet if not specified."
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_filter_view",
            "description": "Create a named filter view that can be saved and reused. Filter views allow different users to see different filtered views of the same data without affecting others.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Name for the filter view (e.g., 'High Priority Items', 'Q4 Sales')"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A1:E100'). Include header row."
                    }
                },
                "required": ["spreadsheet_id", "title", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_filter_view",
            "description": "Delete a filter view by its ID. Use list_filter_views to get filter view IDs first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "filter_view_id": {
                        "type": "integer",
                        "description": "The ID of the filter view to delete"
                    }
                },
                "required": ["spreadsheet_id", "filter_view_id"],
                "additionalProperties": False
            }
        }
    },
    # Batch 3: Named & Protected Ranges
    {
        "type": "function",
        "function": {
            "name": "create_named_range",
            "description": "Create a named range that can be referenced in formulas by name instead of cell addresses. For example, name 'A2:A100' as 'Expenses' to use =SUM(Expenses) in formulas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the range (letters, numbers, underscores only, e.g., 'TotalExpenses', 'Q4_Sales')"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range in A1 notation (e.g., 'A2:A100', 'Sheet1!B2:D50')"
                    }
                },
                "required": ["spreadsheet_id", "name", "range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_named_range",
            "description": "Delete a named range by its ID. Use list_named_ranges to get the IDs first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "named_range_id": {
                        "type": "string",
                        "description": "The ID of the named range to delete"
                    }
                },
                "required": ["spreadsheet_id", "named_range_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_named_ranges",
            "description": "List all named ranges in a spreadsheet with their IDs and cell ranges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "protect_range",
            "description": "Protect a range of cells from editing. Can show a warning when users try to edit, or completely lock the cells. Only the spreadsheet owner can edit protected ranges.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "range": {
                        "type": "string",
                        "description": "Range to protect in A1 notation (e.g., 'A1:D10')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of why this range is protected"
                    },
                    "warning_only": {
                        "type": "boolean",
                        "description": "If true, show a warning but allow editing. If false, completely lock the cells. Default: false"
                    }
                },
                "required": ["spreadsheet_id", "range"],
                "additionalProperties": False
            }
        }
    },
    # Batch 4: Find/Replace & Copy/Paste
    {
        "type": "function",
        "function": {
            "name": "find_replace",
            "description": "Search and replace text values across a spreadsheet or within a specific range. Returns the number of replacements made.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "find": {
                        "type": "string",
                        "description": "The text to search for"
                    },
                    "replacement": {
                        "type": "string",
                        "description": "The text to replace matches with"
                    },
                    "range": {
                        "type": "string",
                        "description": "Optional range to limit search (e.g., 'A1:D100'). If omitted, searches entire sheet."
                    },
                    "match_case": {
                        "type": "boolean",
                        "description": "If true, search is case-sensitive. Default: false"
                    },
                    "match_entire_cell": {
                        "type": "boolean",
                        "description": "If true, only replace cells that exactly match. Default: false"
                    },
                    "search_formulas": {
                        "type": "boolean",
                        "description": "If true, search in formula text instead of displayed values. Default: false"
                    }
                },
                "required": ["spreadsheet_id", "find", "replacement"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_paste",
            "description": "Copy cells from one location to another within the same spreadsheet. Can copy just values, just formatting, or everything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "source_range": {
                        "type": "string",
                        "description": "Source range in A1 notation (e.g., 'A1:D10')"
                    },
                    "destination_range": {
                        "type": "string",
                        "description": "Destination range in A1 notation (e.g., 'F1:I10')"
                    },
                    "paste_type": {
                        "type": "string",
                        "enum": ["all", "values", "format"],
                        "description": "What to paste: 'all' (everything), 'values' (just values), 'format' (just formatting). Default: 'all'"
                    }
                },
                "required": ["spreadsheet_id", "source_range", "destination_range"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cut_paste",
            "description": "Move cells from one location to another within the same spreadsheet. The source cells are cleared after pasting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "source_range": {
                        "type": "string",
                        "description": "Source range in A1 notation (e.g., 'A1:D10')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination cell (top-left corner) in A1 notation (e.g., 'F1')"
                    }
                },
                "required": ["spreadsheet_id", "source_range", "destination"],
                "additionalProperties": False
            }
        }
    },
    # Batch 8: Spreadsheet Properties
    {
        "type": "function",
        "function": {
            "name": "set_spreadsheet_timezone",
            "description": "Set the timezone for a spreadsheet. Affects date/time functions like NOW(), TODAY(), and how dates are displayed. Use IANA timezone names.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone name (e.g., 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Europe/London', 'Asia/Tokyo', 'UTC')"
                    }
                },
                "required": ["spreadsheet_id", "timezone"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_spreadsheet_locale",
            "description": "Set the locale for a spreadsheet. Affects number formatting (1,234.56 vs 1.234,56), date formatting, and currency symbols.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "locale": {
                        "type": "string",
                        "description": "Locale code: 'en_US' (US English), 'en_GB' (UK), 'de_DE' (German), 'fr_FR' (French), 'es_ES' (Spanish), 'ja_JP' (Japanese), 'zh_CN' (Chinese), etc."
                    }
                },
                "required": ["spreadsheet_id", "locale"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_recalculation_interval",
            "description": "Control how often volatile functions (NOW, TODAY, RAND, RANDBETWEEN, etc.) recalculate. Use 'hour' for large sheets with many volatile functions to improve performance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["on_change", "minute", "hour"],
                        "description": "Recalculation frequency: 'on_change' (every edit), 'minute' (every minute), 'hour' (every hour)"
                    }
                },
                "required": ["spreadsheet_id", "interval"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_spreadsheet_properties",
            "description": "Get spreadsheet settings including title, locale, timezone, recalculation interval, and theme. Use to check current configuration before making changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_spreadsheet_theme",
            "description": "Set the spreadsheet theme including primary font and theme colors. Theme colors affect charts, conditional formatting, and other UI elements. All color parameters are optional - only specified colors are changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "primary_font": {
                        "type": "string",
                        "description": "Primary font family (e.g., 'Arial', 'Roboto', 'Times New Roman', 'Courier New', 'Georgia')"
                    },
                    "text_color": {
                        "type": "string",
                        "description": "Main text color - hex code like '#000000' or name like 'black'"
                    },
                    "background_color": {
                        "type": "string",
                        "description": "Main background color - hex code like '#FFFFFF' or name like 'white'"
                    },
                    "accent1": {
                        "type": "string",
                        "description": "Accent color 1 (primary accent for charts/highlights)"
                    },
                    "accent2": {
                        "type": "string",
                        "description": "Accent color 2"
                    },
                    "accent3": {
                        "type": "string",
                        "description": "Accent color 3"
                    },
                    "accent4": {
                        "type": "string",
                        "description": "Accent color 4"
                    },
                    "accent5": {
                        "type": "string",
                        "description": "Accent color 5"
                    },
                    "accent6": {
                        "type": "string",
                        "description": "Accent color 6"
                    },
                    "link_color": {
                        "type": "string",
                        "description": "Hyperlink color"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    # Batch 9: Developer Metadata
    {
        "type": "function",
        "function": {
            "name": "set_developer_metadata",
            "description": "Store custom key-value metadata on a spreadsheet, sheet, row, or column. Metadata is invisible to regular users but can be retrieved programmatically. Useful for bot annotations, tracking, or storing processing state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "Metadata key (e.g., 'created_by', 'status', 'version', 'processed_at')"
                    },
                    "value": {
                        "type": "string",
                        "description": "Metadata value to store"
                    },
                    "location": {
                        "type": "string",
                        "enum": ["spreadsheet", "sheet", "row", "column"],
                        "description": "Where to attach metadata: 'spreadsheet' (entire file), 'sheet' (specific tab), 'row' (row range), 'column' (column range). Default: spreadsheet"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Sheet name (required for sheet/row/column locations)"
                    },
                    "start_index": {
                        "type": "integer",
                        "description": "Start row/column index, 0-based (required for row/column locations). Row 1 = index 0."
                    },
                    "end_index": {
                        "type": "integer",
                        "description": "End row/column index, exclusive (required for row/column locations). To target row 5, use start_index=4, end_index=5."
                    }
                },
                "required": ["spreadsheet_id", "key", "value"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_developer_metadata",
            "description": "Retrieve developer metadata from a spreadsheet. Can get a specific key or list all metadata. Returns metadata IDs needed for deletion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "Optional: specific metadata key to retrieve. Omit to list all metadata."
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_developer_metadata",
            "description": "Delete developer metadata from a spreadsheet by its metadata ID. Use get_developer_metadata first to find the ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "metadata_id": {
                        "type": "integer",
                        "description": "The metadata ID to delete (from get_developer_metadata)"
                    }
                },
                "required": ["spreadsheet_id", "metadata_id"],
                "additionalProperties": False
            }
        }
    },
    # Sheet Properties Extensions
    {
        "type": "function",
        "function": {
            "name": "hide_sheet",
            "description": "Hide a sheet tab from view. Hidden sheets still exist and can be accessed by name, but won't appear in the tab bar. Use to declutter the spreadsheet UI or hide work-in-progress sheets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet to hide"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_sheet",
            "description": "Show (unhide) a hidden sheet tab. Makes a previously hidden sheet visible in the tab bar again.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the hidden sheet to show"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_tab_color",
            "description": "Set the color of a sheet tab. Useful for visually organizing sheets by category (e.g., red for expenses, green for income, blue for reports).",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "color": {
                        "type": "string",
                        "description": "Tab color - hex code like '#FF0000' or name like 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink'"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "color"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_right_to_left",
            "description": "Set whether a sheet uses right-to-left layout. Use for languages like Arabic, Hebrew, Persian that read right-to-left. Affects text direction, column order, and scrolling.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "right_to_left": {
                        "type": "boolean",
                        "description": "True for right-to-left layout, False for left-to-right (default: True)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sheet_properties",
            "description": "Get properties of a specific sheet or all sheets in a spreadsheet. Returns visibility (hidden), tab color, frozen rows/columns, row/column counts, and RTL setting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: Name of specific sheet. If omitted, returns properties for all sheets."
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    # Protected Ranges Management
    {
        "type": "function",
        "function": {
            "name": "list_protected_ranges",
            "description": "List all protected ranges in a spreadsheet. Shows which cells are locked, who can edit them, and whether they show warnings. Use before modifying protections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: Filter to show only protections on this sheet"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_protected_range",
            "description": "Update settings for an existing protected range. Can change description, switch between warning/locked mode, or modify who can edit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "protected_range_id": {
                        "type": "integer",
                        "description": "ID of the protected range (from list_protected_ranges)"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description explaining why this range is protected"
                    },
                    "warning_only": {
                        "type": "boolean",
                        "description": "True to show warning but allow editing, False to lock completely"
                    },
                    "editors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email addresses who can edit this range"
                    }
                },
                "required": ["spreadsheet_id", "protected_range_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_protected_range",
            "description": "Remove protection from a range, allowing anyone with sheet access to edit it. Use list_protected_ranges first to find the ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "protected_range_id": {
                        "type": "integer",
                        "description": "ID of the protected range to unprotect"
                    }
                },
                "required": ["spreadsheet_id", "protected_range_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "protect_sheet",
            "description": "Protect an entire sheet while optionally leaving some ranges editable. Use for templates, forms, or dashboards where only certain cells should be changed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet to protect"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of why the sheet is protected"
                    },
                    "warning_only": {
                        "type": "boolean",
                        "description": "True to show warning but allow editing (default: False = locked)"
                    },
                    "editors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email addresses who can edit the protected areas"
                    },
                    "unprotected_ranges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of A1 ranges that remain editable (e.g., ['B2:B100', 'D2:D100'] for input columns)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    # Filter Views
    {
        "type": "function",
        "function": {
            "name": "list_filter_views",
            "description": "List all saved filter views in a spreadsheet. Filter views allow different users to see different filtered views of the same data without affecting others.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: Filter to show only views on this sheet"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    # Dimension Groups (Row/Column Grouping)
    {
        "type": "function",
        "function": {
            "name": "create_row_group",
            "description": "Create a collapsible row group. Use to organize data hierarchically - e.g., group monthly rows under a quarter header, or detail rows under a category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "start_row": {
                        "type": "integer",
                        "description": "First row of the group (1-indexed)"
                    },
                    "end_row": {
                        "type": "integer",
                        "description": "Last row of the group (inclusive)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "start_row", "end_row"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_column_group",
            "description": "Create a collapsible column group. Use to hide related columns together - e.g., group detailed breakdown columns that can be expanded when needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "start_column": {
                        "type": "string",
                        "description": "First column letter (e.g., 'B')"
                    },
                    "end_column": {
                        "type": "string",
                        "description": "Last column letter (e.g., 'D', inclusive)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "start_column", "end_column"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_row_group",
            "description": "Remove a row group (ungroup rows). The rows remain but are no longer collapsible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "start_row": {
                        "type": "integer",
                        "description": "First row of the group"
                    },
                    "end_row": {
                        "type": "integer",
                        "description": "Last row of the group"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "start_row", "end_row"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_column_group",
            "description": "Remove a column group (ungroup columns). The columns remain but are no longer collapsible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "start_column": {
                        "type": "string",
                        "description": "First column letter"
                    },
                    "end_column": {
                        "type": "string",
                        "description": "Last column letter"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "start_column", "end_column"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "collapse_expand_group",
            "description": "Collapse or expand a row/column group. Collapsed groups hide their contents; expanded groups show them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "dimension": {
                        "type": "string",
                        "enum": ["ROWS", "COLUMNS"],
                        "description": "Whether this is a row or column group"
                    },
                    "start_index": {
                        "type": "string",
                        "description": "Start of group: row number (e.g., '5') for ROWS, column letter (e.g., 'B') for COLUMNS"
                    },
                    "end_index": {
                        "type": "string",
                        "description": "End of group: row number for ROWS, column letter for COLUMNS"
                    },
                    "collapsed": {
                        "type": "boolean",
                        "description": "True to collapse (hide), False to expand (show)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "dimension", "start_index", "end_index", "collapsed"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_group_control_position",
            "description": "Set where the +/- group controls appear. By default they appear before the grouped rows/columns; this can change them to appear after.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "row_control_after": {
                        "type": "boolean",
                        "description": "True to show row group controls below the group instead of above"
                    },
                    "column_control_after": {
                        "type": "boolean",
                        "description": "True to show column group controls after the group instead of before"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name"],
                "additionalProperties": False
            }
        }
    },
    # Slicers
    {
        "type": "function",
        "function": {
            "name": "list_slicers",
            "description": "List all slicers in a spreadsheet. Slicers are interactive filter widgets that let users filter data visually.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: Filter to show only slicers on this sheet"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_slicer",
            "description": "Create a slicer widget for interactive data filtering. Slicers show a list of unique values from a column and let users click to filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "data_range": {
                        "type": "string",
                        "description": "Range the slicer filters (e.g., 'A1:E100')"
                    },
                    "column_index": {
                        "type": "integer",
                        "description": "0-based column index in the data range to filter by"
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the slicer"
                    },
                    "anchor_row": {
                        "type": "integer",
                        "description": "Row to position the slicer (0-indexed, default: 0)"
                    },
                    "anchor_col": {
                        "type": "integer",
                        "description": "Column to position the slicer (0-indexed, default: 0)"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "data_range", "column_index"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_slicer",
            "description": "Update a slicer's settings like title or which column it filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "slicer_id": {
                        "type": "integer",
                        "description": "ID of the slicer (from list_slicers)"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title for the slicer"
                    },
                    "column_index": {
                        "type": "integer",
                        "description": "New column index to filter by"
                    }
                },
                "required": ["spreadsheet_id", "slicer_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_slicer",
            "description": "Delete a slicer widget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "slicer_id": {
                        "type": "integer",
                        "description": "ID of the slicer to delete"
                    }
                },
                "required": ["spreadsheet_id", "slicer_id"],
                "additionalProperties": False
            }
        }
    },
    # Tables (Structured Data)
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List all structured tables in a spreadsheet. Tables have typed columns and automatic formatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Optional: Filter to show only tables on this sheet"
                    }
                },
                "required": ["spreadsheet_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_table",
            "description": "Create a structured table with typed columns. Tables support column types like TEXT, DOUBLE, CURRENCY, PERCENT, DATE, TIME, DATE_TIME, BOOLEAN, DROPDOWN, and chip types (FILES_CHIP, PEOPLE_CHIP, FINANCE_CHIP, PLACE_CHIP, RATINGS_CHIP).",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Name of the sheet"
                    },
                    "range_notation": {
                        "type": "string",
                        "description": "Range for the table (e.g., 'A1:E20')"
                    },
                    "name": {
                        "type": "string",
                        "description": "Unique name for the table"
                    },
                    "columns": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Column header name"},
                                "type": {"type": "string", "description": "Column type: TEXT, DOUBLE, CURRENCY, PERCENT, DATE, TIME, DATE_TIME, BOOLEAN, DROPDOWN, FILES_CHIP, PEOPLE_CHIP, FINANCE_CHIP, PLACE_CHIP, RATINGS_CHIP"},
                                "dropdown_values": {"type": "array", "items": {"type": "string"}, "description": "Values for DROPDOWN type"}
                            },
                            "required": ["name"]
                        },
                        "description": "Column definitions with name and type"
                    }
                },
                "required": ["spreadsheet_id", "sheet_name", "range_notation", "name", "columns"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_table",
            "description": "Delete a table (data remains, just loses table structure and formatting).",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "table_id": {
                        "type": "string",
                        "description": "ID of the table to delete (from list_tables)"
                    }
                },
                "required": ["spreadsheet_id", "table_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_table_column",
            "description": "Update a table column's name, type, or dropdown values.",
            "parameters": {
                "type": "object",
                "properties": {
                    "spreadsheet_id": {
                        "type": "string",
                        "description": "The Google Sheets ID"
                    },
                    "table_id": {
                        "type": "string",
                        "description": "ID of the table"
                    },
                    "column_index": {
                        "type": "integer",
                        "description": "0-based index of the column to update"
                    },
                    "column_name": {
                        "type": "string",
                        "description": "New column name"
                    },
                    "column_type": {
                        "type": "string",
                        "description": "New column type"
                    },
                    "dropdown_values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "New dropdown values (for DROPDOWN type)"
                    }
                },
                "required": ["spreadsheet_id", "table_id", "column_index"],
                "additionalProperties": False
            }
        }
    }
]

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

def get_tools_for_context(
    context: str = "gui",
    image_enabled: bool = False,
    weather_enabled: bool = False,
    finance_enabled: bool = False,
    time_enabled: bool = False,
    wikipedia_enabled: bool = False,
    reaction_enabled: bool = False,
    sheets_enabled: bool = False,
    member_memory_enabled: bool = False
) -> list:
    """
    Return appropriate tools based on context and enabled features.

    Args:
        context: "gui" for main app (all tools), "signal" for Signal bot
        image_enabled: Include image generation tool (Signal bot only)
        weather_enabled: Include weather tool (Signal bot only)
        finance_enabled: Include finance tools (Signal bot only)
        time_enabled: Include time/date tools (Signal bot only)
        wikipedia_enabled: Include Wikipedia tools (Signal bot only)
        reaction_enabled: Include emoji reaction tool (Signal bot only)
        sheets_enabled: Include Google Sheets tools (Signal bot only)
        member_memory_enabled: Include member memory tools (Signal bot only)

    Returns:
        List of tool definitions appropriate for the context
    """
    if context == "signal":
        tools = []
        if image_enabled:
            tools.extend(SIGNAL_TOOLS)
        if weather_enabled:
            tools.append(WEATHER_TOOL)
        if finance_enabled:
            tools.extend(FINANCE_TOOLS)
        if time_enabled:
            tools.extend(TIME_TOOLS)
        if wikipedia_enabled:
            tools.extend(WIKIPEDIA_TOOLS)
        if reaction_enabled:
            tools.append(REACTION_TOOL)
        if sheets_enabled:
            tools.extend(SHEETS_TOOLS)
        if member_memory_enabled:
            tools.extend(MEMBER_MEMORY_TOOLS)
        return tools
    return AGENT_TOOLS


# Models known to support OpenAI-compatible function/tool calling via OpenRouter
TOOL_CAPABLE_MODEL_PATTERNS = [
    # Claude models (Anthropic)
    "claude-opus-4", "claude-sonnet-4", "claude-haiku-4",
    "claude-3-opus", "claude-3-sonnet", "claude-3.5-sonnet", "claude-3.5-haiku",
    "claude-3.7-sonnet",
    # OpenAI models
    "openai/gpt-5", "openai/gpt-4o", "openai/gpt-4.1", "openai/o1", "openai/o3",
    # Google models
    "google/gemini-3", "google/gemini-2.5", "google/gemini-2.0",
    # Grok
    "x-ai/grok-4", "x-ai/grok-3",
    # Others with tool support
    "anthropic/",  # Any anthropic model
]


def model_supports_tools(model_id: str) -> bool:
    """
    Check if a model supports function/tool calling.

    Args:
        model_id: The model ID string (e.g., 'claude-sonnet-4', 'openai/gpt-4o')

    Returns:
        True if the model likely supports tool calling
    """
    normalized = model_id.lower()

    # Normalize model ID - add anthropic/ prefix for Claude models
    if normalized.startswith("claude-") and not normalized.startswith("anthropic/"):
        normalized = f"anthropic/{normalized}"

    # Check against known capable patterns
    for pattern in TOOL_CAPABLE_MODEL_PATTERNS:
        if pattern.lower() in normalized:
            return True

    return False
