"""
Finance tool schemas for Signal bots.

Contains stock, crypto, and financial data tools.
"""

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

# Two-phase meta-tool categories for finance tools
FINANCE_CATEGORIES = {
    "finance_quotes": {
        "description": "Get current stock/crypto prices, search tickers, find top movers",
        "sub_tools": ["get_stock_quote", "search_stocks", "get_top_stocks"]
    },
    "finance_analysis": {
        "description": "Get news, analyst ratings, and ownership data",
        "sub_tools": ["get_stock_news", "get_analyst_ratings", "get_holders"]
    },
    "finance_fundamentals": {
        "description": "Get price history, earnings, dividends, financials, options",
        "sub_tools": ["get_price_history", "get_earnings", "get_dividends", "get_financials", "get_options"]
    }
}
