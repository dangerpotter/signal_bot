"""
Weather API client for Signal bots.

Calls WeatherAPI.com to get current weather and forecasts.
Used by the bot's native tool calling system.
"""

import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_API_BASE = "https://api.weatherapi.com/v1"


async def get_weather(location: str, days: int = 1) -> dict:
    """
    Get current weather and forecast for a location.

    Args:
        location: City name, address, lat/lon, or postal code
        days: Number of forecast days (1-7)

    Returns:
        dict with weather data or error message
    """
    if not WEATHER_API_KEY:
        logger.error("WEATHER_API_KEY not set in environment")
        return {"error": "Weather API key not configured"}

    if not location:
        return {"error": "Location is required"}

    days = max(1, min(7, days))  # Clamp to 1-7

    params = {
        "key": WEATHER_API_KEY,
        "q": location,
        "days": days,
        "aqi": "yes",  # Include air quality
        "alerts": "yes"  # Include weather alerts
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{WEATHER_API_BASE}/forecast.json",
                params=params
            )

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                except Exception:
                    error_msg = response.text
                logger.error(f"Weather API error {response.status_code}: {error_msg}")
                return {"error": f"Weather API error: {error_msg}"}

            data = response.json()
            return _format_weather_response(data)

    except httpx.TimeoutException:
        logger.error("Weather API request timed out")
        return {"error": "Weather API request timed out"}
    except httpx.RequestError as e:
        logger.error(f"Weather API request error: {e}")
        return {"error": f"Weather API request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected weather API error: {e}")
        return {"error": f"Unexpected error: {str(e)}"}


def _format_weather_response(data: dict) -> dict:
    """
    Format the WeatherAPI response into a more concise, useful format.
    """
    location = data.get("location", {})
    current = data.get("current", {})
    forecast = data.get("forecast", {}).get("forecastday", [])
    alerts = data.get("alerts", {}).get("alert", [])

    result = {
        "location": {
            "name": location.get("name"),
            "region": location.get("region"),
            "country": location.get("country"),
            "localtime": location.get("localtime"),
            "timezone": location.get("tz_id")
        },
        "current": {
            "temp_f": current.get("temp_f"),
            "temp_c": current.get("temp_c"),
            "feels_like_f": current.get("feelslike_f"),
            "feels_like_c": current.get("feelslike_c"),
            "condition": current.get("condition", {}).get("text"),
            "humidity": current.get("humidity"),
            "wind_mph": current.get("wind_mph"),
            "wind_dir": current.get("wind_dir"),
            "uv": current.get("uv"),
            "visibility_miles": current.get("vis_miles")
        },
        "forecast": [],
        "alerts": []
    }

    # Add air quality if available
    aqi = current.get("air_quality", {})
    if aqi:
        result["current"]["air_quality"] = {
            "us_epa_index": aqi.get("us-epa-index"),
            "pm2_5": round(aqi.get("pm2_5", 0), 1),
            "pm10": round(aqi.get("pm10", 0), 1)
        }

    # Format forecast days
    for day in forecast:
        day_data = day.get("day", {})
        result["forecast"].append({
            "date": day.get("date"),
            "high_f": day_data.get("maxtemp_f"),
            "low_f": day_data.get("mintemp_f"),
            "high_c": day_data.get("maxtemp_c"),
            "low_c": day_data.get("mintemp_c"),
            "condition": day_data.get("condition", {}).get("text"),
            "chance_of_rain": day_data.get("daily_chance_of_rain"),
            "chance_of_snow": day_data.get("daily_chance_of_snow"),
            "sunrise": day.get("astro", {}).get("sunrise"),
            "sunset": day.get("astro", {}).get("sunset")
        })

    # Add any weather alerts
    for alert in alerts[:3]:  # Limit to 3 alerts
        result["alerts"].append({
            "headline": alert.get("headline"),
            "severity": alert.get("severity"),
            "event": alert.get("event"),
            "effective": alert.get("effective"),
            "expires": alert.get("expires")
        })

    return result


def get_weather_sync(location: str, days: int = 1) -> dict:
    """
    Synchronous wrapper for get_weather().
    Use this when calling from non-async code.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in an async context, create a new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    get_weather(location, days)
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(get_weather(location, days))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(get_weather(location, days))
