"""
TheNewsAPI client for Signal bots.

Uses TheNewsAPI (thenewsapi.com) to fetch news articles.
Free tier: 100 requests/month.

Used as a fallback when Yahoo Finance news returns null data.
"""

import logging
import os
import requests
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# API configuration
NEWS_API_BASE_URL = "https://api.thenewsapi.com/v1/news"
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


def search_news(
    query: str,
    limit: int = 5,
    language: str = "en",
    categories: Optional[str] = None
) -> dict:
    """
    Search for news articles using TheNewsAPI.

    Args:
        query: Search term (company name, topic, etc.)
        limit: Number of articles to return (1-10 on free tier)
        language: Language code (default: en)
        categories: Comma-separated categories (business, tech, general, etc.)

    Returns:
        dict with news list or error
    """
    if not NEWS_API_KEY:
        return {"error": "NEWS_API_KEY not configured"}

    if not query:
        return {"error": "Search query is required"}

    # Clamp limit to reasonable range
    limit = max(1, min(10, limit))

    try:
        params = {
            "api_token": NEWS_API_KEY,
            "search": query,
            "language": language,
            "limit": limit,
            "sort": "published_at"
        }

        if categories:
            params["categories"] = categories

        response = requests.get(
            f"{NEWS_API_BASE_URL}/top",
            params=params,
            timeout=10
        )

        if response.status_code == 401:
            return {"error": "Invalid NEWS_API_KEY"}
        elif response.status_code == 402:
            return {"error": "News API usage limit reached (100/month)"}
        elif response.status_code == 429:
            return {"error": "News API rate limit reached"}
        elif response.status_code != 200:
            return {"error": f"News API error: {response.status_code}"}

        data = response.json()
        articles = data.get("data", [])

        if not articles:
            return {
                "query": query,
                "news": [],
                "message": "No articles found for this search"
            }

        formatted_news = []
        for article in articles:
            formatted_news.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "snippet": article.get("snippet"),
                "url": article.get("url"),
                "image_url": article.get("image_url"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "categories": article.get("categories", [])
            })

        return {
            "query": query,
            "news": formatted_news,
            "count": len(formatted_news),
            "source": "thenewsapi"
        }

    except requests.exceptions.Timeout:
        logger.error("News API request timed out")
        return {"error": "News API request timed out"}
    except requests.exceptions.RequestException as e:
        logger.error(f"News API request failed: {e}")
        return {"error": f"News API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error fetching news for '{query}': {e}")
        return {"error": f"Failed to fetch news: {str(e)}"}


def get_top_news(
    limit: int = 5,
    language: str = "en",
    locale: str = "us",
    categories: Optional[str] = None
) -> dict:
    """
    Get top news stories.

    Args:
        limit: Number of articles to return (1-10 on free tier)
        language: Language code (default: en)
        locale: Country code (default: us)
        categories: Comma-separated categories (business, tech, general, etc.)

    Returns:
        dict with news list or error
    """
    if not NEWS_API_KEY:
        return {"error": "NEWS_API_KEY not configured"}

    limit = max(1, min(10, limit))

    try:
        params = {
            "api_token": NEWS_API_KEY,
            "language": language,
            "locale": locale,
            "limit": limit
        }

        if categories:
            params["categories"] = categories

        response = requests.get(
            f"{NEWS_API_BASE_URL}/top",
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            return {"error": f"News API error: {response.status_code}"}

        data = response.json()
        articles = data.get("data", [])

        if not articles:
            return {
                "news": [],
                "message": "No top stories available"
            }

        formatted_news = []
        for article in articles:
            formatted_news.append({
                "title": article.get("title"),
                "description": article.get("description"),
                "snippet": article.get("snippet"),
                "url": article.get("url"),
                "image_url": article.get("image_url"),
                "source": article.get("source"),
                "published_at": article.get("published_at"),
                "categories": article.get("categories", [])
            })

        return {
            "news": formatted_news,
            "count": len(formatted_news),
            "source": "thenewsapi"
        }

    except Exception as e:
        logger.error(f"Error fetching top news: {e}")
        return {"error": f"Failed to fetch top news: {str(e)}"}


def get_stock_news(symbol: str, company_name: Optional[str] = None, count: int = 5) -> dict:
    """
    Get news for a stock symbol. Uses company name for better search results.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        company_name: Optional company name for better search (e.g., 'Apple', 'Tesla')
        count: Number of articles to return

    Returns:
        dict with news list or error
    """
    # Build search query - prefer company name if available
    if company_name:
        # Use company name with stock symbol for better results
        search_query = f'"{company_name}" | {symbol}'
    else:
        # Map common symbols to company names for better search
        symbol_to_name = {
            "AAPL": "Apple",
            "TSLA": "Tesla",
            "MSFT": "Microsoft",
            "GOOGL": "Google",
            "GOOG": "Google",
            "AMZN": "Amazon",
            "META": "Meta Facebook",
            "NVDA": "NVIDIA",
            "AMD": "AMD",
            "INTC": "Intel",
            "NFLX": "Netflix",
            "DIS": "Disney",
            "BA": "Boeing",
            "JPM": "JPMorgan",
            "V": "Visa",
            "MA": "Mastercard",
            "WMT": "Walmart",
            "KO": "Coca-Cola",
            "PEP": "Pepsi",
            "MCD": "McDonald's",
        }
        name = symbol_to_name.get(symbol.upper(), symbol)
        search_query = f'"{name}" stock' if name != symbol else f"{symbol} stock"

    result = search_news(
        query=search_query,
        limit=count,
        categories="business,tech"
    )

    # Add symbol to result for reference
    if "error" not in result:
        result["symbol"] = symbol.upper()

    return result
