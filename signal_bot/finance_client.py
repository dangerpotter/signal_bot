"""
Yahoo Finance API client for Signal bots.

Uses yfinance library to get stock quotes, news, and market data.
Used by the bot's native tool calling system.
"""

import logging
from datetime import datetime
from typing import Optional
import concurrent.futures

logger = logging.getLogger(__name__)

# Valid periods and intervals for price history
VALID_PERIODS = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
VALID_INTERVALS = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]

# Supported sectors for top entities
VALID_SECTORS = [
    "basic-materials", "communication-services", "consumer-cyclical",
    "consumer-defensive", "energy", "financial-services", "healthcare",
    "industrials", "real-estate", "technology", "utilities"
]


def get_ticker_info(symbol: str) -> dict:
    """
    Get comprehensive stock/crypto information.

    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'BTC-USD')

    Returns:
        dict with stock data or error message
    """
    if not symbol:
        return {"error": "Symbol is required"}

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            # Try with common suffixes for international stocks
            return {"error": f"Could not find data for symbol: {symbol}"}

        result = {
            "symbol": info.get("symbol", symbol.upper()),
            "name": info.get("longName") or info.get("shortName", "Unknown"),
            "type": info.get("quoteType", "Unknown"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "Unknown"),
            "price": {
                "current": info.get("regularMarketPrice"),
                "previous_close": info.get("previousClose"),
                "open": info.get("regularMarketOpen"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "change": info.get("regularMarketChange"),
                "change_percent": info.get("regularMarketChangePercent"),
            },
            "volume": {
                "current": info.get("regularMarketVolume"),
                "average": info.get("averageVolume"),
                "average_10d": info.get("averageDailyVolume10Day"),
            },
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "52_week": {
                "high": info.get("fiftyTwoWeekHigh"),
                "low": info.get("fiftyTwoWeekLow"),
            },
            "50_day_avg": info.get("fiftyDayAverage"),
            "200_day_avg": info.get("twoHundredDayAverage"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }

        # Add crypto-specific fields if applicable
        if info.get("quoteType") == "CRYPTOCURRENCY":
            result["circulating_supply"] = info.get("circulatingSupply")
            result["total_supply"] = info.get("totalSupply")

        return result

    except Exception as e:
        logger.error(f"Error getting ticker info for {symbol}: {e}")
        return {"error": f"Failed to get data for {symbol}: {str(e)}"}


def get_ticker_news(symbol: str, count: int = 5) -> dict:
    """
    Get recent news for a stock/crypto.

    Args:
        symbol: Ticker symbol
        count: Number of news items (1-20)

    Returns:
        dict with news list or error
    """
    if not symbol:
        return {"error": "Symbol is required"}

    count = max(1, min(20, count))

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol.upper())
        news = ticker.news

        if not news:
            return {"symbol": symbol.upper(), "news": [], "message": "No recent news found"}

        formatted_news = []
        for item in news[:count]:
            formatted_news.append({
                "title": item.get("title"),
                "publisher": item.get("publisher"),
                "link": item.get("link"),
                "published": datetime.fromtimestamp(item.get("providerPublishTime", 0)).isoformat()
                if item.get("providerPublishTime") else None,
                "type": item.get("type"),
            })

        return {
            "symbol": symbol.upper(),
            "news": formatted_news,
            "count": len(formatted_news)
        }

    except Exception as e:
        logger.error(f"Error getting news for {symbol}: {e}")
        return {"error": f"Failed to get news for {symbol}: {str(e)}"}


def search_symbols(query: str, count: int = 10) -> dict:
    """
    Search for stocks, ETFs, crypto by name or symbol.

    Args:
        query: Search term (company name, ticker, etc.)
        count: Max results (1-25)

    Returns:
        dict with search results or error
    """
    if not query:
        return {"error": "Search query is required"}

    count = max(1, min(25, count))

    try:
        import yfinance as yf

        # yfinance doesn't have a direct search API, but we can use the Ticker
        # to validate symbols. For a real search, we'd need Yahoo Finance search API.
        # Let's try the query as a direct symbol first
        ticker = yf.Ticker(query.upper())
        info = ticker.info

        results = []

        if info and info.get("symbol"):
            results.append({
                "symbol": info.get("symbol"),
                "name": info.get("longName") or info.get("shortName", "Unknown"),
                "type": info.get("quoteType", "Unknown"),
                "exchange": info.get("exchange", "Unknown"),
            })

        # For broader search capability, use yfinance's search (if available)
        try:
            search_results = yf.Search(query)
            if hasattr(search_results, 'quotes') and search_results.quotes:
                for quote in search_results.quotes[:count]:
                    if quote.get("symbol") not in [r["symbol"] for r in results]:
                        results.append({
                            "symbol": quote.get("symbol"),
                            "name": quote.get("longname") or quote.get("shortname", "Unknown"),
                            "type": quote.get("quoteType", "Unknown"),
                            "exchange": quote.get("exchange", "Unknown"),
                        })
        except Exception:
            # Search not available in this version, continue with direct lookup
            pass

        if not results:
            return {"query": query, "results": [], "message": "No matches found"}

        return {
            "query": query,
            "results": results[:count],
            "count": len(results[:count])
        }

    except Exception as e:
        logger.error(f"Error searching for {query}: {e}")
        return {"error": f"Search failed: {str(e)}"}


def get_top_entities(entity_type: str = "companies", sector: str = "technology", count: int = 10) -> dict:
    """
    Get top performing entities by sector.

    Note: yfinance doesn't have a direct screener API. This provides commonly
    tracked tickers per sector as a workaround.

    Args:
        entity_type: companies, etfs, or mutual_funds
        sector: Sector name (technology, healthcare, etc.)
        count: Number of results (1-25)

    Returns:
        dict with top performers or error
    """
    count = max(1, min(25, count))

    # Popular tickers by sector (curated list since yfinance lacks screener)
    sector_tickers = {
        "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AVGO", "ORCL", "CRM", "AMD", "ADBE"],
        "healthcare": ["UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY"],
        "financial-services": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "C", "SPGI"],
        "consumer-cyclical": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "LOW", "TJX", "BKNG", "MAR"],
        "consumer-defensive": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MDLZ", "CL", "EL", "KHC"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "industrials": ["CAT", "UNP", "HON", "UPS", "BA", "RTX", "DE", "LMT", "GE", "MMM"],
        "basic-materials": ["LIN", "APD", "SHW", "ECL", "DD", "NEM", "FCX", "NUE", "DOW", "CTVA"],
        "real-estate": ["PLD", "AMT", "EQIX", "PSA", "SPG", "O", "WELL", "DLR", "AVB", "EQR"],
        "utilities": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "XEL", "EXC", "WEC", "ED"],
        "communication-services": ["GOOGL", "META", "NFLX", "DIS", "CMCSA", "VZ", "T", "TMUS", "CHTR", "EA"],
    }

    etf_tickers = {
        "technology": ["QQQ", "XLK", "VGT", "ARKK", "SMH"],
        "healthcare": ["XLV", "VHT", "IBB", "XBI", "ARKG"],
        "financial-services": ["XLF", "VFH", "KRE", "KBE", "ARKF"],
        "energy": ["XLE", "VDE", "OIH", "XOP", "AMLP"],
        "default": ["SPY", "QQQ", "IWM", "DIA", "VTI"],
    }

    try:
        import yfinance as yf

        # Normalize sector name
        sector_key = sector.lower().replace(" ", "-")
        if sector_key not in sector_tickers:
            sector_key = "technology"  # Default

        if entity_type == "etfs":
            tickers_list = etf_tickers.get(sector_key, etf_tickers["default"])
        else:
            tickers_list = sector_tickers.get(sector_key, sector_tickers["technology"])

        results = []
        for symbol in tickers_list[:count]:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if info and info.get("regularMarketPrice"):
                    results.append({
                        "symbol": symbol,
                        "name": info.get("longName") or info.get("shortName", symbol),
                        "price": info.get("regularMarketPrice"),
                        "change_percent": info.get("regularMarketChangePercent"),
                        "market_cap": info.get("marketCap"),
                        "volume": info.get("regularMarketVolume"),
                    })
            except Exception:
                continue

        # Sort by change percent (best performers first)
        results.sort(key=lambda x: x.get("change_percent") or 0, reverse=True)

        return {
            "entity_type": entity_type,
            "sector": sector_key,
            "results": results,
            "count": len(results)
        }

    except Exception as e:
        logger.error(f"Error getting top entities: {e}")
        return {"error": f"Failed to get top entities: {str(e)}"}


def get_price_history(symbol: str, period: str = "1mo", interval: str = "1d") -> dict:
    """
    Get historical price data.

    Args:
        symbol: Ticker symbol
        period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)

    Returns:
        dict with price history or error
    """
    if not symbol:
        return {"error": "Symbol is required"}

    # Validate and normalize inputs
    period = period.lower() if period else "1mo"
    interval = interval.lower() if interval else "1d"

    if period not in VALID_PERIODS:
        period = "1mo"
    if interval not in VALID_INTERVALS:
        interval = "1d"

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return {"error": f"No price history found for {symbol}"}

        # Convert to list of dicts
        history_data = []
        for date, row in hist.iterrows():
            history_data.append({
                "date": date.isoformat() if hasattr(date, 'isoformat') else str(date),
                "open": round(row["Open"], 2) if row["Open"] else None,
                "high": round(row["High"], 2) if row["High"] else None,
                "low": round(row["Low"], 2) if row["Low"] else None,
                "close": round(row["Close"], 2) if row["Close"] else None,
                "volume": int(row["Volume"]) if row["Volume"] else None,
            })

        # Limit response size
        max_points = 100
        if len(history_data) > max_points:
            # Sample evenly
            step = len(history_data) // max_points
            history_data = history_data[::step][:max_points]

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data_points": len(history_data),
            "history": history_data
        }

    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {e}")
        return {"error": f"Failed to get price history: {str(e)}"}


def get_option_chain(symbol: str, option_type: str = "both", date: Optional[str] = None) -> dict:
    """
    Get options chain data.

    Args:
        symbol: Ticker symbol
        option_type: 'call', 'put', or 'both'
        date: Expiration date (YYYY-MM-DD) or None for nearest

    Returns:
        dict with options data or error
    """
    if not symbol:
        return {"error": "Symbol is required"}

    option_type = option_type.lower() if option_type else "both"
    if option_type not in ["call", "put", "both"]:
        option_type = "both"

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol.upper())

        # Get available expiration dates
        expirations = ticker.options
        if not expirations:
            return {"error": f"No options available for {symbol}"}

        # Select expiration date
        if date and date in expirations:
            exp_date = date
        else:
            exp_date = expirations[0]  # Nearest expiration

        # Get options chain
        opt = ticker.option_chain(exp_date)

        result = {
            "symbol": symbol.upper(),
            "expiration_date": exp_date,
            "available_expirations": list(expirations[:10]),  # Limit list
        }

        def format_options(df, limit=20):
            """Format options dataframe to dict list."""
            options = []
            for _, row in df.head(limit).iterrows():
                options.append({
                    "strike": row.get("strike"),
                    "last_price": row.get("lastPrice"),
                    "bid": row.get("bid"),
                    "ask": row.get("ask"),
                    "volume": int(row.get("volume")) if row.get("volume") else None,
                    "open_interest": int(row.get("openInterest")) if row.get("openInterest") else None,
                    "implied_volatility": round(row.get("impliedVolatility", 0) * 100, 2),
                    "in_the_money": row.get("inTheMoney"),
                })
            return options

        if option_type in ["call", "both"]:
            result["calls"] = format_options(opt.calls)
            result["calls_count"] = len(opt.calls)

        if option_type in ["put", "both"]:
            result["puts"] = format_options(opt.puts)
            result["puts_count"] = len(opt.puts)

        return result

    except Exception as e:
        logger.error(f"Error getting options for {symbol}: {e}")
        return {"error": f"Failed to get options data: {str(e)}"}


def get_earnings(symbol: str, period: str = "quarterly") -> dict:
    """
    Get earnings data and upcoming earnings date.

    Args:
        symbol: Ticker symbol
        period: 'annual' or 'quarterly'

    Returns:
        dict with earnings data or error
    """
    if not symbol:
        return {"error": "Symbol is required"}

    period = period.lower() if period else "quarterly"
    if period not in ["annual", "quarterly"]:
        period = "quarterly"

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        result = {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName", symbol),
            "period": period,
        }

        # Get earnings dates
        try:
            calendar = ticker.calendar
            if calendar is not None and not calendar.empty:
                if hasattr(calendar, 'to_dict'):
                    cal_dict = calendar.to_dict()
                    result["next_earnings_date"] = str(cal_dict.get("Earnings Date", [None])[0])
                    result["earnings_estimate"] = cal_dict.get("Earnings Average", [None])[0]
                    result["revenue_estimate"] = cal_dict.get("Revenue Average", [None])[0]
        except Exception:
            pass

        # Get earnings history
        try:
            if period == "quarterly":
                earnings = ticker.quarterly_earnings
            else:
                earnings = ticker.earnings

            if earnings is not None and not earnings.empty:
                earnings_list = []
                for date, row in earnings.iterrows():
                    earnings_list.append({
                        "date": str(date),
                        "revenue": row.get("Revenue"),
                        "earnings": row.get("Earnings"),
                    })
                result["earnings_history"] = earnings_list[:8]  # Last 8 periods
        except Exception:
            result["earnings_history"] = []

        # Get EPS data
        result["trailing_eps"] = info.get("trailingEps")
        result["forward_eps"] = info.get("forwardEps")
        result["peg_ratio"] = info.get("pegRatio")

        return result

    except Exception as e:
        logger.error(f"Error getting earnings for {symbol}: {e}")
        return {"error": f"Failed to get earnings data: {str(e)}"}


# Synchronous wrappers for use in tool executor
# yfinance is already synchronous, so these are simple pass-throughs
# but we keep the pattern consistent with weather_client.py

def get_ticker_info_sync(symbol: str) -> dict:
    """Synchronous wrapper for get_ticker_info."""
    return get_ticker_info(symbol)


def get_ticker_news_sync(symbol: str, count: int = 5) -> dict:
    """Synchronous wrapper for get_ticker_news."""
    return get_ticker_news(symbol, count)


def search_symbols_sync(query: str, count: int = 10) -> dict:
    """Synchronous wrapper for search_symbols."""
    return search_symbols(query, count)


def get_top_entities_sync(entity_type: str = "companies", sector: str = "technology", count: int = 10) -> dict:
    """Synchronous wrapper for get_top_entities."""
    return get_top_entities(entity_type, sector, count)


def get_price_history_sync(symbol: str, period: str = "1mo", interval: str = "1d") -> dict:
    """Synchronous wrapper for get_price_history."""
    return get_price_history(symbol, period, interval)


def get_option_chain_sync(symbol: str, option_type: str = "both", date: Optional[str] = None) -> dict:
    """Synchronous wrapper for get_option_chain."""
    return get_option_chain(symbol, option_type, date)


def get_earnings_sync(symbol: str, period: str = "quarterly") -> dict:
    """Synchronous wrapper for get_earnings."""
    return get_earnings(symbol, period)
