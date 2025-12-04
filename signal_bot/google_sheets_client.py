"""
Google Sheets and Drive client for Signal bot integration.

Provides OAuth authentication and API operations for creating, reading,
and writing to Google Sheets. Each bot can have its own Google account.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
import httpx

logger = logging.getLogger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Google API endpoints
SHEETS_API_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_API_BASE = "https://www.googleapis.com/drive/v3"

# OAuth scopes - limited access (only files created by app)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


# ============================================================================
# OAuth Helper Functions
# ============================================================================

def get_oauth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """
    Generate Google OAuth consent URL.

    Args:
        client_id: OAuth client ID from Google Cloud Console
        redirect_uri: URL to redirect after authorization
        state: Random state token for CSRF protection

    Returns:
        Full OAuth authorization URL
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Always show consent to get refresh token
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> dict:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from OAuth callback
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: Must match the one used in authorization

    Returns:
        Dict with access_token, refresh_token, expires_in, or error
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
            )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token exchange failed: {error_data}")
                return {"error": error_data.get("error_description", "Token exchange failed")}

            data = response.json()
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in", 3600),
                "token_type": data.get("token_type", "Bearer"),
            }

        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            return {"error": str(e)}


async def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    """
    Refresh an expired access token using the refresh token.

    Args:
        client_id: OAuth client ID
        client_secret: OAuth client secret
        refresh_token: Stored refresh token

    Returns:
        Dict with new access_token, expires_in, or error
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            )

            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Token refresh failed: {error_data}")
                return {"error": error_data.get("error_description", "Token refresh failed")}

            data = response.json()
            return {
                "access_token": data.get("access_token"),
                "expires_in": data.get("expires_in", 3600),
            }

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {"error": str(e)}


def exchange_code_for_tokens_sync(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str
) -> dict:
    """Synchronous wrapper for exchange_code_for_tokens."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                exchange_code_for_tokens(code, client_id, client_secret, redirect_uri)
            )
            return future.result(timeout=60)
    else:
        return asyncio.run(exchange_code_for_tokens(code, client_id, client_secret, redirect_uri))


# ============================================================================
# Token Management
# ============================================================================

# In-memory token cache: bot_id -> {access_token, expiry}
_token_cache = {}


async def get_valid_access_token(bot_data: dict) -> Optional[str]:
    """
    Get a valid access token, refreshing if necessary.

    Args:
        bot_data: Bot configuration dict with google_* credentials

    Returns:
        Valid access token or None if unable to get one
    """
    from signal_bot.models import Bot, db

    bot_id = bot_data.get("id")
    client_id = bot_data.get("google_client_id")
    refresh_token = bot_data.get("google_refresh_token")

    if not client_id or not refresh_token:
        logger.warning(f"Bot {bot_id}: Missing Google credentials")
        return None

    # Check cache first
    cached = _token_cache.get(bot_id)
    if cached and cached.get("expiry") and cached["expiry"] > datetime.utcnow():
        return cached["access_token"]

    # Need to refresh - get client_secret from database (not in bot_data for security)
    try:
        bot = Bot.query.get(bot_id)
        if not bot or not bot.google_client_secret:
            logger.warning(f"Bot {bot_id}: No client secret found")
            return None

        result = await refresh_access_token(client_id, bot.google_client_secret, refresh_token)

        if "error" in result:
            logger.error(f"Bot {bot_id}: Token refresh failed - {result['error']}")
            return None

        access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        expiry = datetime.utcnow() + timedelta(seconds=expires_in - 60)  # 60s buffer

        # Update cache
        _token_cache[bot_id] = {
            "access_token": access_token,
            "expiry": expiry,
        }

        # Update database with new expiry
        bot.google_token_expiry = expiry
        db.session.commit()

        return access_token

    except Exception as e:
        logger.error(f"Bot {bot_id}: Error getting access token - {e}")
        return None


# ============================================================================
# Google Sheets API Operations
# ============================================================================

async def create_spreadsheet(
    access_token: str,
    title: str,
    sheet_names: Optional[list] = None
) -> dict:
    """
    Create a new Google Sheets spreadsheet.

    Args:
        access_token: Valid Google OAuth access token
        title: Title for the new spreadsheet
        sheet_names: Optional list of sheet names (default: ["Sheet1"])

    Returns:
        Dict with spreadsheet_id, spreadsheet_url, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Build request body
    sheets = []
    if sheet_names:
        for name in sheet_names:
            sheets.append({"properties": {"title": name}})
    else:
        sheets.append({"properties": {"title": "Sheet1"}})

    body = {
        "properties": {"title": title},
        "sheets": sheets,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                SHEETS_API_BASE,
                headers=headers,
                json=body
            )

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Create spreadsheet failed: {error_msg}")
                return {"error": error_msg}

            data = response.json()
            spreadsheet_id = data.get("spreadsheetId")

            return {
                "spreadsheet_id": spreadsheet_id,
                "title": title,
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                "sheets": [s["properties"]["title"] for s in data.get("sheets", [])],
            }

        except Exception as e:
            logger.error(f"Error creating spreadsheet: {e}")
            return {"error": str(e)}


async def read_range(
    access_token: str,
    spreadsheet_id: str,
    range_notation: str
) -> dict:
    """
    Read values from a spreadsheet range.

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation (e.g., "Sheet1!A1:D10")

    Returns:
        Dict with values (2D array), or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    # URL encode the range
    from urllib.parse import quote
    encoded_range = quote(range_notation, safe='')
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{encoded_range}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": "Spreadsheet or range not found"}

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": error_msg}

            data = response.json()
            values = data.get("values", [])

            return {
                "range": data.get("range"),
                "values": values,
                "row_count": len(values),
                "col_count": max(len(row) for row in values) if values else 0,
            }

        except Exception as e:
            logger.error(f"Error reading range: {e}")
            return {"error": str(e)}


async def write_range(
    access_token: str,
    spreadsheet_id: str,
    range_notation: str,
    values: list
) -> dict:
    """
    Write values to a spreadsheet range.

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation (e.g., "Sheet1!A1")
        values: 2D array of values to write

    Returns:
        Dict with updated range info, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    from urllib.parse import quote
    encoded_range = quote(range_notation, safe='')
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{encoded_range}?valueInputOption=USER_ENTERED"

    body = {"values": values}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.put(url, headers=headers, json=body)

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": error_msg}

            data = response.json()
            return {
                "updated_range": data.get("updatedRange"),
                "updated_rows": data.get("updatedRows"),
                "updated_columns": data.get("updatedColumns"),
                "updated_cells": data.get("updatedCells"),
            }

        except Exception as e:
            logger.error(f"Error writing range: {e}")
            return {"error": str(e)}


async def append_rows(
    access_token: str,
    spreadsheet_id: str,
    range_notation: str,
    values: list
) -> dict:
    """
    Append rows to a spreadsheet.

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID
        range_notation: Target range (e.g., "Sheet1!A:Z" to append to Sheet1)
        values: 2D array of rows to append

    Returns:
        Dict with appended range info, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    from urllib.parse import quote
    encoded_range = quote(range_notation, safe='')
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{encoded_range}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"

    body = {"values": values}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=body)

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": error_msg}

            data = response.json()
            updates = data.get("updates", {})
            return {
                "updated_range": updates.get("updatedRange"),
                "updated_rows": updates.get("updatedRows"),
                "updated_cells": updates.get("updatedCells"),
            }

        except Exception as e:
            logger.error(f"Error appending rows: {e}")
            return {"error": str(e)}


async def get_spreadsheet_metadata(access_token: str, spreadsheet_id: str) -> dict:
    """
    Get metadata about a spreadsheet (title, sheets, etc).

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID

    Returns:
        Dict with spreadsheet metadata, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}?fields=properties,sheets.properties"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return {"error": "Spreadsheet not found"}

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": error_msg}

            data = response.json()
            props = data.get("properties", {})
            sheets = data.get("sheets", [])

            return {
                "spreadsheet_id": spreadsheet_id,
                "title": props.get("title"),
                "locale": props.get("locale"),
                "sheets": [
                    {
                        "title": s["properties"]["title"],
                        "sheet_id": s["properties"]["sheetId"],
                        "row_count": s["properties"].get("gridProperties", {}).get("rowCount"),
                        "col_count": s["properties"].get("gridProperties", {}).get("columnCount"),
                    }
                    for s in sheets
                ],
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
            }

        except Exception as e:
            logger.error(f"Error getting spreadsheet metadata: {e}")
            return {"error": str(e)}


# ============================================================================
# Google Drive API Operations
# ============================================================================

async def list_spreadsheets_from_drive(
    access_token: str,
    query: Optional[str] = None,
    limit: int = 20
) -> dict:
    """
    List spreadsheets from Google Drive.

    Args:
        access_token: Valid Google OAuth access token
        query: Optional search query for file names
        limit: Maximum number of results

    Returns:
        Dict with files list, or error
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    # Build query - only get spreadsheets created by this app
    q_parts = ["mimeType='application/vnd.google-apps.spreadsheet'"]
    if query:
        q_parts.append(f"name contains '{query}'")

    params = {
        "q": " and ".join(q_parts),
        "fields": "files(id,name,createdTime,modifiedTime,webViewLink)",
        "pageSize": min(limit, 100),
        "orderBy": "modifiedTime desc",
    }

    url = f"{DRIVE_API_BASE}/files?{urlencode(params)}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                return {"error": error_msg}

            data = response.json()
            files = data.get("files", [])

            return {
                "spreadsheets": [
                    {
                        "spreadsheet_id": f["id"],
                        "title": f["name"],
                        "created_at": f.get("createdTime"),
                        "modified_at": f.get("modifiedTime"),
                        "url": f.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{f['id']}"),
                    }
                    for f in files
                ],
                "count": len(files),
            }

        except Exception as e:
            logger.error(f"Error listing spreadsheets from Drive: {e}")
            return {"error": str(e)}


async def search_drive(access_token: str, query: str, limit: int = 10) -> dict:
    """
    Search for files in Google Drive by name.

    Args:
        access_token: Valid Google OAuth access token
        query: Search query for file names
        limit: Maximum number of results

    Returns:
        Dict with matching files, or error
    """
    return await list_spreadsheets_from_drive(access_token, query=query, limit=limit)


# ============================================================================
# Sync Wrappers for Tool Executor
# ============================================================================

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


def create_spreadsheet_sync(
    bot_data: dict,
    group_id: str,
    title: str,
    description: str = "",
    created_by: str = None
) -> dict:
    """
    Create a new spreadsheet and register it in the database.

    Args:
        bot_data: Bot configuration dict
        group_id: Signal group ID
        title: Spreadsheet title
        description: What this sheet is for
        created_by: Name of user who requested creation

    Returns:
        Dict with spreadsheet info or error
    """
    async def _create():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        result = await create_spreadsheet(access_token, title)
        if "error" in result:
            return result

        # Register in database
        from signal_bot.models import SheetsRegistry, db

        try:
            registry = SheetsRegistry(
                bot_id=bot_data["id"],
                group_id=group_id,
                spreadsheet_id=result["spreadsheet_id"],
                title=title,
                description=description,
                created_by=created_by,
            )
            db.session.add(registry)
            db.session.commit()

            result["description"] = description
            result["created_by"] = created_by
            result["registered"] = True

        except Exception as e:
            logger.error(f"Error registering spreadsheet: {e}")
            # Still return success - sheet was created, just not registered
            result["registered"] = False
            result["registration_error"] = str(e)

        return result

    return _run_async(_create())


def list_spreadsheets_sync(bot_data: dict, group_id: str) -> dict:
    """
    List all registered spreadsheets for this bot+group.

    Args:
        bot_data: Bot configuration dict
        group_id: Signal group ID

    Returns:
        Dict with spreadsheets list or error
    """
    from signal_bot.models import SheetsRegistry

    try:
        sheets = SheetsRegistry.get_sheets_for_group(bot_data["id"], group_id)
        return {
            "spreadsheets": [s.to_dict() for s in sheets],
            "count": len(sheets),
        }
    except Exception as e:
        logger.error(f"Error listing spreadsheets: {e}")
        return {"error": str(e)}


def read_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str
) -> dict:
    """
    Read values from a spreadsheet range.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation (e.g., "Sheet1!A1:D10")

    Returns:
        Dict with values or error
    """
    async def _read():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        result = await read_range(access_token, spreadsheet_id, range_notation)

        # Update last_accessed if successful
        if "error" not in result:
            from signal_bot.models import SheetsRegistry, db
            try:
                sheet = SheetsRegistry.query.filter_by(spreadsheet_id=spreadsheet_id).first()
                if sheet:
                    sheet.last_accessed = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update last_accessed: {e}")

        return result

    return _run_async(_read())


def write_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str,
    values: list
) -> dict:
    """
    Write values to a spreadsheet range.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation
        values: 2D array of values

    Returns:
        Dict with update info or error
    """
    async def _write():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        result = await write_range(access_token, spreadsheet_id, range_notation, values)

        # Update last_accessed if successful
        if "error" not in result:
            from signal_bot.models import SheetsRegistry, db
            try:
                sheet = SheetsRegistry.query.filter_by(spreadsheet_id=spreadsheet_id).first()
                if sheet:
                    sheet.last_accessed = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update last_accessed: {e}")

        return result

    return _run_async(_write())


def append_to_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    values: list,
    added_by: str = None
) -> dict:
    """
    Append a row to a spreadsheet with automatic timestamp and attribution.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        values: 1D array of values for the row
        added_by: Name of person who added this data

    Returns:
        Dict with update info or error
    """
    async def _append():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Add timestamp and attribution to the row
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        row_with_meta = [timestamp, added_by or "Unknown"] + list(values)

        # Append to Sheet1 by default (covers full range to find last row)
        result = await append_rows(access_token, spreadsheet_id, "Sheet1!A:Z", [row_with_meta])

        # Update last_accessed if successful
        if "error" not in result:
            from signal_bot.models import SheetsRegistry, db
            try:
                sheet = SheetsRegistry.query.filter_by(spreadsheet_id=spreadsheet_id).first()
                if sheet:
                    sheet.last_accessed = datetime.utcnow()
                    db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update last_accessed: {e}")

            result["row_added"] = row_with_meta

        return result

    return _run_async(_append())


def search_sheets_sync(bot_data: dict, group_id: str, query: str) -> dict:
    """
    Search registered spreadsheets by title.

    Args:
        bot_data: Bot configuration dict
        group_id: Signal group ID
        query: Search query

    Returns:
        Dict with matching spreadsheets or error
    """
    from signal_bot.models import SheetsRegistry

    try:
        sheets = SheetsRegistry.search_sheets(bot_data["id"], group_id, query)
        return {
            "spreadsheets": [s.to_dict() for s in sheets],
            "count": len(sheets),
            "query": query,
        }
    except Exception as e:
        logger.error(f"Error searching spreadsheets: {e}")
        return {"error": str(e)}


def get_spreadsheet_info_sync(bot_data: dict, spreadsheet_id: str) -> dict:
    """
    Get metadata about a specific spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID

    Returns:
        Dict with spreadsheet metadata or error
    """
    async def _get_info():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        return await get_spreadsheet_metadata(access_token, spreadsheet_id)

    return _run_async(_get_info())
