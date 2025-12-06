"""
Google Calendar client for Signal bot integration.

Provides API operations for creating calendars, managing events,
and sharing calendars. Shares OAuth credentials with Google Sheets.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from urllib.parse import urlencode, quote
import httpx
from flask import Flask

logger = logging.getLogger(__name__)

# Flask app reference for database context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app


# Google Calendar API endpoint
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"


# ============================================================================
# Calendar API Operations (Async)
# ============================================================================

async def create_calendar(
    access_token: str,
    title: str,
    description: str = "",
    timezone: str = "UTC",
    make_public: bool = True
) -> dict:
    """
    Create a new secondary calendar.

    Args:
        access_token: Valid Google OAuth access token
        title: Calendar title/summary
        description: Optional description
        timezone: IANA timezone (e.g., "America/New_York")
        make_public: If True (default), automatically make calendar publicly viewable

    Returns:
        Dict with calendar_id, url, is_public, share_link, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    body = {
        "summary": title,
        "description": description,
        "timeZone": timezone,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{CALENDAR_API_BASE}/calendars",
                headers=headers,
                json=body
            )

            if response.status_code not in (200, 201):
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")

                # Check for permission errors (user needs to reconnect for calendar scope)
                if response.status_code == 403 and "insufficient" in error_msg.lower():
                    return {"error": "Calendar permission not granted. Please disconnect and reconnect to Google in the admin panel to grant Calendar access."}

                logger.error(f"Create calendar failed: {error_msg}")
                return {"error": error_msg}

            data = response.json()
            calendar_id = data.get("id")

            result = {
                "calendar_id": calendar_id,
                "title": data.get("summary"),
                "description": data.get("description", ""),
                "timezone": data.get("timeZone"),
                "url": f"https://calendar.google.com/calendar/embed?src={quote(calendar_id)}",
                "is_public": False,
            }

            # Auto-make public if requested
            if make_public:
                share_result = await share_calendar(access_token, calendar_id, make_public=True)
                if "error" not in share_result:
                    result["is_public"] = True
                    result["share_link"] = share_result.get("share_link")
                    logger.info(f"Calendar '{title}' created and made public")
                else:
                    # Calendar created but sharing failed - log warning but don't fail
                    logger.warning(f"Calendar created but sharing failed: {share_result.get('error')}")
                    result["share_warning"] = f"Calendar created but not made public: {share_result.get('error')}"

            return result

        except Exception as e:
            logger.error(f"Error creating calendar: {e}")
            return {"error": str(e)}


async def list_events(
    access_token: str,
    calendar_id: str,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    single_events: bool = True
) -> dict:
    """
    List events from a calendar.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        time_min: Lower bound (RFC3339 timestamp with timezone)
        time_max: Upper bound (RFC3339 timestamp)
        max_results: Maximum number of events (default 10)
        single_events: Expand recurring events (default True)

    Returns:
        Dict with events list, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    params = {
        "maxResults": min(max_results, 100),
        "singleEvents": str(single_events).lower(),
        "orderBy": "startTime" if single_events else "updated",
    }

    if time_min:
        params["timeMin"] = time_min
    else:
        # Default to now
        params["timeMin"] = datetime.utcnow().isoformat() + "Z"

    if time_max:
        params["timeMax"] = time_max

    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events?{urlencode(params)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": "Calendar not found"}

            if response.status_code == 403:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "")
                if "insufficient" in error_msg.lower():
                    return {"error": "Calendar permission not granted. Please disconnect and reconnect to Google in the admin panel."}
                return {"error": error_msg or "Access denied"}

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            data = response.json()
            events = data.get("items", [])

            return {
                "events": [_format_event(e) for e in events],
                "count": len(events),
                "calendar_id": calendar_id,
            }

        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return {"error": str(e)}


async def get_event(
    access_token: str,
    calendar_id: str,
    event_id: str
) -> dict:
    """
    Get a single event by ID.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        event_id: Event ID

    Returns:
        Dict with event details, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events/{event_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": "Event not found"}

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            return {"event": _format_event(response.json())}

        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return {"error": str(e)}


async def create_event(
    access_token: str,
    calendar_id: str,
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    attendees: Optional[List[str]] = None,
    all_day: bool = False,
    timezone: str = "UTC",
    reminders: Optional[List[dict]] = None,
    send_notifications: bool = True
) -> dict:
    """
    Create a new calendar event.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        title: Event title/summary
        start_time: Start time (ISO 8601 format or date for all-day)
        end_time: End time (ISO 8601 format or date for all-day)
        description: Optional event description
        location: Optional location string
        attendees: Optional list of email addresses to invite
        all_day: If True, use date-only format for all-day events
        timezone: IANA timezone for the event
        reminders: Optional list of reminders [{"method": "email/popup", "minutes": 30}]
        send_notifications: If True (default), send email invitations to attendees

    Returns:
        Dict with event details, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Build event body
    body = {
        "summary": title,
        "description": description,
        "location": location,
    }

    # Handle start/end times
    if all_day:
        body["start"] = {"date": start_time}
        body["end"] = {"date": end_time}
    else:
        body["start"] = {"dateTime": start_time, "timeZone": timezone}
        body["end"] = {"dateTime": end_time, "timeZone": timezone}

    # Add attendees if provided
    if attendees:
        body["attendees"] = [{"email": email} for email in attendees]

    # Add custom reminders if provided
    if reminders:
        body["reminders"] = {
            "useDefault": False,
            "overrides": reminders
        }

    # Build URL with query params for notifications
    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events"
    if attendees and send_notifications:
        url += "?sendUpdates=all"  # Send email invitations to all attendees

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=body)

            if response.status_code not in (200, 201):
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                logger.error(f"Create event failed: {error_msg}")
                return {"error": error_msg}

            result = {"event": _format_event(response.json())}
            if attendees:
                result["invitations_sent"] = send_notifications
                result["attendees"] = attendees
            return result

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"error": str(e)}


async def update_event(
    access_token: str,
    calendar_id: str,
    event_id: str,
    updates: dict
) -> dict:
    """
    Update an existing event.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        event_id: Event ID to update
        updates: Dict of fields to update (title, description, location, start_time, end_time, etc.)

    Returns:
        Dict with updated event, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events/{event_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First get the existing event
            get_response = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
            if get_response.status_code != 200:
                if get_response.status_code == 404:
                    return {"error": "Event not found"}
                error_data = get_response.json() if get_response.text else {}
                return {"error": error_data.get("error", {}).get("message", "Failed to get event")}

            event = get_response.json()

            # Apply updates
            if "title" in updates:
                event["summary"] = updates["title"]
            if "description" in updates:
                event["description"] = updates["description"]
            if "location" in updates:
                event["location"] = updates["location"]
            if "start_time" in updates:
                timezone = updates.get("timezone", "UTC")
                if updates.get("all_day"):
                    event["start"] = {"date": updates["start_time"]}
                else:
                    event["start"] = {"dateTime": updates["start_time"], "timeZone": timezone}
            if "end_time" in updates:
                timezone = updates.get("timezone", "UTC")
                if updates.get("all_day"):
                    event["end"] = {"date": updates["end_time"]}
                else:
                    event["end"] = {"dateTime": updates["end_time"], "timeZone": timezone}

            # PUT the updated event
            response = await client.put(url, headers=headers, json=event)

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            return {"event": _format_event(response.json())}

        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {"error": str(e)}


async def delete_event(
    access_token: str,
    calendar_id: str,
    event_id: str
) -> dict:
    """
    Delete an event from a calendar.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        event_id: Event ID to delete

    Returns:
        Dict with success status, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events/{event_id}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.delete(url, headers=headers)

            if response.status_code == 404:
                return {"error": "Event not found"}

            if response.status_code not in (200, 204):
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            return {"success": True, "message": "Event deleted"}

        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {"error": str(e)}


async def quick_add_event(
    access_token: str,
    calendar_id: str,
    text: str
) -> dict:
    """
    Create an event using natural language (Google's Quick Add).

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        text: Natural language description (e.g., "Dinner with John at 7pm tomorrow")

    Returns:
        Dict with created event, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/events/quickAdd?text={quote(text)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers)

            if response.status_code not in (200, 201):
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            return {"event": _format_event(response.json())}

        except Exception as e:
            logger.error(f"Error quick adding event: {e}")
            return {"error": str(e)}


async def share_calendar(
    access_token: str,
    calendar_id: str,
    email: Optional[str] = None,
    role: str = "reader",
    make_public: bool = False
) -> dict:
    """
    Share a calendar with a user or make it public.

    Args:
        access_token: Valid Google OAuth access token
        calendar_id: Google Calendar ID
        email: Email address to share with (None if making public)
        role: Access role - "reader", "writer", "owner"
        make_public: If True, make calendar publicly readable

    Returns:
        Dict with share info or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    if make_public:
        body = {
            "role": "reader",
            "scope": {"type": "default"}  # Anyone can view
        }
    elif email:
        body = {
            "role": role,
            "scope": {"type": "user", "value": email}
        }
    else:
        return {"error": "Must provide email or set make_public=True"}

    url = f"{CALENDAR_API_BASE}/calendars/{quote(calendar_id, safe='')}/acl"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=body)

            if response.status_code not in (200, 201):
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            data = response.json()

            # Build share link for public calendars
            share_link = None
            if make_public:
                share_link = f"https://calendar.google.com/calendar/embed?src={quote(calendar_id)}"

            return {
                "success": True,
                "role": data.get("role"),
                "scope": data.get("scope"),
                "share_link": share_link,
            }

        except Exception as e:
            logger.error(f"Error sharing calendar: {e}")
            return {"error": str(e)}


# ============================================================================
# Helper Functions
# ============================================================================

def _format_event(event: dict) -> dict:
    """Format a Google Calendar event for display."""
    start = event.get("start", {})
    end = event.get("end", {})

    return {
        "event_id": event.get("id"),
        "title": event.get("summary", "(No title)"),
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "timezone": start.get("timeZone", ""),
        "all_day": "date" in start and "dateTime" not in start,
        "status": event.get("status"),
        "html_link": event.get("htmlLink"),
        "created": event.get("created"),
        "updated": event.get("updated"),
        "attendees": [
            {"email": a.get("email"), "status": a.get("responseStatus")}
            for a in event.get("attendees", [])
        ],
    }


def _run_async(coro):
    """Helper to run async coroutine from sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=60)
    else:
        return asyncio.run(coro)


# ============================================================================
# Sync Wrappers for Tool Executor
# ============================================================================

def create_calendar_sync(
    bot_data: dict,
    group_id: str,
    title: str,
    description: str = "",
    timezone: str = "UTC",
    created_by: str = None,
    make_public: bool = True
) -> dict:
    """Create a new calendar and register it in the database."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _create():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please reconnect via admin panel (Calendar scope may be needed)."}

        result = await create_calendar(access_token, title, description, timezone, make_public)
        if "error" in result:
            return result

        # Register in database
        from signal_bot.models import CalendarRegistry, db

        try:
            if _flask_app:
                with _flask_app.app_context():
                    registry = CalendarRegistry(
                        bot_id=bot_data["id"],
                        group_id=group_id,
                        calendar_id=result["calendar_id"],
                        title=title,
                        description=description,
                        timezone=timezone,
                        created_by=created_by,
                        is_public=result.get("is_public", False),
                        share_link=result.get("share_link"),
                    )
                    db.session.add(registry)
                    db.session.commit()

            result["registered"] = True
            result["created_by"] = created_by

        except Exception as e:
            logger.error(f"Error registering calendar: {e}")
            result["registered"] = False
            result["registration_error"] = str(e)

        return result

    return _run_async(_create())


def list_calendars_sync(bot_data: dict, group_id: str) -> dict:
    """List all registered calendars for this bot+group."""
    from signal_bot.models import CalendarRegistry

    try:
        if _flask_app:
            with _flask_app.app_context():
                calendars = CalendarRegistry.get_calendars_for_group(bot_data["id"], group_id)
                return {
                    "calendars": [c.to_dict() for c in calendars],
                    "count": len(calendars),
                }
        return {"calendars": [], "count": 0}
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        return {"error": str(e)}


def list_events_sync(
    bot_data: dict,
    calendar_id: str,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10
) -> dict:
    """List events from a calendar."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _list():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please reconnect via admin panel."}

        result = await list_events(access_token, calendar_id, time_min, time_max, max_results)

        # Update last_accessed
        if "error" not in result:
            from signal_bot.models import CalendarRegistry, db
            try:
                if _flask_app:
                    with _flask_app.app_context():
                        cal = CalendarRegistry.query.filter_by(calendar_id=calendar_id).first()
                        if cal:
                            cal.last_accessed = datetime.utcnow()
                            db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update last_accessed: {e}")

        return result

    return _run_async(_list())


def get_event_sync(bot_data: dict, calendar_id: str, event_id: str) -> dict:
    """Get a single event."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _get():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}
        return await get_event(access_token, calendar_id, event_id)

    return _run_async(_get())


def create_event_sync(
    bot_data: dict,
    calendar_id: str,
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
    location: str = "",
    all_day: bool = False,
    timezone: str = "UTC",
    attendees: Optional[List[str]] = None,
    send_notifications: bool = True
) -> dict:
    """Create a new event with optional attendees."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _create():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}
        return await create_event(
            access_token, calendar_id, title, start_time, end_time,
            description, location, attendees, all_day, timezone,
            send_notifications=send_notifications
        )

    return _run_async(_create())


def update_event_sync(
    bot_data: dict,
    calendar_id: str,
    event_id: str,
    updates: dict
) -> dict:
    """Update an existing event."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _update():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}
        return await update_event(access_token, calendar_id, event_id, updates)

    return _run_async(_update())


def delete_event_sync(bot_data: dict, calendar_id: str, event_id: str) -> dict:
    """Delete an event."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _delete():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}
        return await delete_event(access_token, calendar_id, event_id)

    return _run_async(_delete())


def quick_add_event_sync(bot_data: dict, calendar_id: str, text: str) -> dict:
    """Quick add an event using natural language."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _quick_add():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}
        return await quick_add_event(access_token, calendar_id, text)

    return _run_async(_quick_add())


def share_calendar_sync(
    bot_data: dict,
    calendar_id: str,
    email: Optional[str] = None,
    role: str = "reader",
    make_public: bool = False
) -> dict:
    """Share a calendar with a user or make it public."""
    from signal_bot.google_sheets_client import get_valid_access_token

    async def _share():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google."}

        result = await share_calendar(access_token, calendar_id, email, role, make_public)

        # Update registry if made public
        if "error" not in result and make_public:
            from signal_bot.models import CalendarRegistry, db
            try:
                if _flask_app:
                    with _flask_app.app_context():
                        cal = CalendarRegistry.query.filter_by(calendar_id=calendar_id).first()
                        if cal:
                            cal.is_public = True
                            cal.share_link = result.get("share_link")
                            db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update calendar registry: {e}")

        return result

    return _run_async(_share())
