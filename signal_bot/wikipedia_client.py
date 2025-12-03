"""
Wikipedia API client for Signal bots.

Uses Wikipedia's REST API to search articles and retrieve summaries.
Used by the bot's native tool calling system.
"""

import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Wikipedia REST API base URLs
WIKI_API_BASE = "https://en.wikipedia.org/w/rest.php/v1"
WIKI_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"

# User agent as required by Wikipedia API
USER_AGENT = "LiminalBackroomsBot/1.0 (Signal bot; educational/research use)"


async def search_wikipedia(query: str, limit: int = 5) -> dict:
    """
    Search Wikipedia for articles matching a query.

    Args:
        query: Search terms
        limit: Maximum number of results (1-20)

    Returns:
        dict with search results or error message
    """
    if not query:
        return {"error": "Search query is required"}

    query = query.strip()
    if not query:
        return {"error": "Search query cannot be empty"}

    limit = max(1, min(20, limit))

    params = {
        "q": query,
        "limit": limit
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{WIKI_API_BASE}/search/page",
                params=params,
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Wikipedia search error {response.status_code}: {response.text}")
                return {"error": f"Wikipedia API error: {response.status_code}"}

            data = response.json()
            pages = data.get("pages", [])

            if not pages:
                return {
                    "query": query,
                    "results": [],
                    "message": f"No Wikipedia articles found for '{query}'"
                }

            results = []
            for page in pages[:limit]:
                results.append({
                    "title": page.get("title"),
                    "description": page.get("description", ""),
                    "excerpt": page.get("excerpt", ""),
                    "key": page.get("key"),  # URL-safe title
                    "url": f"https://en.wikipedia.org/wiki/{page.get('key', '')}"
                })

            return {
                "query": query,
                "results": results,
                "count": len(results)
            }

    except httpx.TimeoutException:
        logger.error("Wikipedia search request timed out")
        return {"error": "Wikipedia search timed out"}
    except httpx.RequestError as e:
        logger.error(f"Wikipedia search request error: {e}")
        return {"error": f"Wikipedia request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected Wikipedia search error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


async def get_wikipedia_summary(title: str) -> dict:
    """
    Get the summary/intro of a Wikipedia article.

    Args:
        title: Article title (can use spaces or underscores)

    Returns:
        dict with article summary or error message
    """
    if not title:
        return {"error": "Article title is required"}

    title = title.strip()
    if not title:
        return {"error": "Article title cannot be empty"}

    # Replace spaces with underscores for URL
    url_title = title.replace(" ", "_")

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(
                f"{WIKI_SUMMARY_BASE}/{url_title}",
                headers=headers
            )

            if response.status_code == 404:
                return {
                    "title": title,
                    "exists": False,
                    "error": f"No Wikipedia article found for '{title}'"
                }

            if response.status_code != 200:
                logger.error(f"Wikipedia summary error {response.status_code}: {response.text}")
                return {"error": f"Wikipedia API error: {response.status_code}"}

            data = response.json()

            # Check if it's a disambiguation page
            page_type = data.get("type", "standard")

            result = {
                "title": data.get("title"),
                "display_title": data.get("displaytitle"),
                "description": data.get("description", ""),
                "extract": data.get("extract", ""),  # Plain text summary
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "exists": True,
                "type": page_type
            }

            # Add thumbnail if available
            thumbnail = data.get("thumbnail")
            if thumbnail:
                result["thumbnail"] = {
                    "url": thumbnail.get("source"),
                    "width": thumbnail.get("width"),
                    "height": thumbnail.get("height")
                }

            # Add original image if available
            original = data.get("originalimage")
            if original:
                result["image"] = {
                    "url": original.get("source"),
                    "width": original.get("width"),
                    "height": original.get("height")
                }

            # Add coordinates if available
            coordinates = data.get("coordinates")
            if coordinates:
                result["coordinates"] = {
                    "latitude": coordinates.get("lat"),
                    "longitude": coordinates.get("lon")
                }

            # Warn if disambiguation page
            if page_type == "disambiguation":
                result["message"] = "This is a disambiguation page - search for a more specific term"

            return result

    except httpx.TimeoutException:
        logger.error("Wikipedia summary request timed out")
        return {"error": "Wikipedia request timed out"}
    except httpx.RequestError as e:
        logger.error(f"Wikipedia summary request error: {e}")
        return {"error": f"Wikipedia request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected Wikipedia summary error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


async def get_random_article() -> dict:
    """
    Get a random Wikipedia article summary.

    Returns:
        dict with random article summary or error message
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Use the random article endpoint
            response = await client.get(
                "https://en.wikipedia.org/api/rest_v1/page/random/summary",
                headers=headers
            )

            if response.status_code != 200:
                logger.error(f"Wikipedia random error {response.status_code}: {response.text}")
                return {"error": f"Wikipedia API error: {response.status_code}"}

            data = response.json()

            result = {
                "title": data.get("title"),
                "display_title": data.get("displaytitle"),
                "description": data.get("description", ""),
                "extract": data.get("extract", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "exists": True,
                "type": data.get("type", "standard")
            }

            # Add thumbnail if available
            thumbnail = data.get("thumbnail")
            if thumbnail:
                result["thumbnail"] = {
                    "url": thumbnail.get("source"),
                    "width": thumbnail.get("width"),
                    "height": thumbnail.get("height")
                }

            return result

    except httpx.TimeoutException:
        logger.error("Wikipedia random request timed out")
        return {"error": "Wikipedia request timed out"}
    except httpx.RequestError as e:
        logger.error(f"Wikipedia random request error: {e}")
        return {"error": f"Wikipedia request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected Wikipedia random error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


# Synchronous wrappers for use in tool executor

def search_wikipedia_sync(query: str, limit: int = 5) -> dict:
    """
    Synchronous wrapper for search_wikipedia().
    Use this when calling from non-async code.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    search_wikipedia(query, limit)
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(search_wikipedia(query, limit))
    except RuntimeError:
        return asyncio.run(search_wikipedia(query, limit))


def get_wikipedia_summary_sync(title: str) -> dict:
    """
    Synchronous wrapper for get_wikipedia_summary().
    Use this when calling from non-async code.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_wikipedia_summary(title)
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(get_wikipedia_summary(title))
    except RuntimeError:
        return asyncio.run(get_wikipedia_summary(title))


def get_random_article_sync() -> dict:
    """
    Synchronous wrapper for get_random_article().
    Use this when calling from non-async code.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_random_article()
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(get_random_article())
    except RuntimeError:
        return asyncio.run(get_random_article())
