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

def get_tools_for_context(
    context: str = "gui",
    image_enabled: bool = False,
    weather_enabled: bool = False,
    finance_enabled: bool = False
) -> list:
    """
    Return appropriate tools based on context and enabled features.

    Args:
        context: "gui" for main app (all tools), "signal" for Signal bot
        image_enabled: Include image generation tool (Signal bot only)
        weather_enabled: Include weather tool (Signal bot only)
        finance_enabled: Include finance tools (Signal bot only)

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
