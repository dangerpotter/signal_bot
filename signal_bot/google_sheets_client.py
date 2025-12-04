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
from flask import Flask

logger = logging.getLogger(__name__)

# Flask app reference for database context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set the Flask app for database context."""
    global _flask_app
    _flask_app = app

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
        # Get client_secret from database (requires Flask app context)
        client_secret = None
        if _flask_app:
            with _flask_app.app_context():
                bot = Bot.query.get(bot_id)
                if bot and bot.google_client_secret:
                    client_secret = bot.google_client_secret

        if not client_secret:
            logger.warning(f"Bot {bot_id}: No client secret found")
            return None

        result = await refresh_access_token(client_id, client_secret, refresh_token)

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

        # Update database with new expiry (requires Flask app context)
        if _flask_app:
            with _flask_app.app_context():
                bot = Bot.query.get(bot_id)
                if bot:
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
            # Escape underscores in spreadsheet_id to prevent markdown URL mangling
            escaped_id = spreadsheet_id.replace('_', '\\_') if spreadsheet_id else spreadsheet_id

            return {
                "spreadsheet_id": spreadsheet_id,
                "title": title,
                "url": f"https://docs.google.com/spreadsheets/d/{escaped_id}",
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


async def clear_range(access_token: str, spreadsheet_id: str, range_notation: str) -> dict:
    """
    Clear values from a range in a spreadsheet.

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation range (e.g., 'Sheet1!A1:C10' or 'B:B')

    Returns:
        Dict with cleared range info, or error
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    from urllib.parse import quote
    encoded_range = quote(range_notation, safe='')
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}/values/{encoded_range}:clear"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json={})

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": error_msg}

            data = response.json()
            return {
                "cleared_range": data.get("clearedRange"),
                "spreadsheet_id": data.get("spreadsheetId"),
            }

        except Exception as e:
            logger.error(f"Error clearing range: {e}")
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


async def batch_update(access_token: str, spreadsheet_id: str, requests: list) -> dict:
    """
    Execute a batchUpdate request on a spreadsheet.

    Args:
        access_token: Valid Google OAuth access token
        spreadsheet_id: Google Sheets ID
        requests: List of update request objects

    Returns:
        Dict with response data, or error
    """
    url = f"{SHEETS_API_BASE}/{spreadsheet_id}:batchUpdate"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {"requests": requests}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, headers=headers, json=body)

            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {response.status_code}")
                return {"error": f"batchUpdate failed: {error_msg}"}

            return response.json()

        except Exception as e:
            logger.error(f"Error in batchUpdate: {e}")
            return {"error": str(e)}


def parse_column_range(columns: str) -> tuple:
    """
    Convert column notation to 0-indexed range.

    Args:
        columns: Column in A1 notation ('B' or 'B:E')

    Returns:
        Tuple of (start_index, end_index) - end is exclusive

    Examples:
        'B' -> (1, 2)
        'B:E' -> (1, 5)
        'AA' -> (26, 27)
    """
    def col_to_index(col: str) -> int:
        col = col.upper().strip()
        result = 0
        for char in col:
            result = result * 26 + (ord(char) - ord('A') + 1)
        return result - 1  # 0-indexed

    if ':' in columns:
        start, end = columns.split(':')
        return col_to_index(start), col_to_index(end) + 1
    else:
        idx = col_to_index(columns)
        return idx, idx + 1


def parse_row_range(rows: str) -> tuple:
    """
    Convert row notation to 0-indexed range.

    Args:
        rows: Row number or range ('5' or '5:10')

    Returns:
        Tuple of (start_index, end_index) - end is exclusive, 0-indexed

    Examples:
        '5' -> (4, 5)      # Row 5 is index 4
        '5:10' -> (4, 10)  # Rows 5-10
        '1' -> (0, 1)      # Row 1 is index 0
    """
    if ':' in rows:
        start, end = rows.split(':')
        return int(start) - 1, int(end)  # Convert to 0-indexed, end is exclusive
    else:
        idx = int(rows) - 1  # Convert to 0-indexed
        return idx, idx + 1


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
            if _flask_app:
                with _flask_app.app_context():
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
        if _flask_app:
            with _flask_app.app_context():
                sheets = SheetsRegistry.get_sheets_for_group(bot_data["id"], group_id)
                return {
                    "spreadsheets": [s.to_dict() for s in sheets],
                    "count": len(sheets),
                }
        return {"spreadsheets": [], "count": 0}
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
                if _flask_app:
                    with _flask_app.app_context():
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
                if _flask_app:
                    with _flask_app.app_context():
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
    added_by: str = None,
    include_metadata: bool = True
) -> dict:
    """
    Append a row to a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        values: 1D array of values for the row
        added_by: Name of person who added this data
        include_metadata: If True (default), prepends timestamp and attribution columns.
                         If False, appends values directly without metadata.

    Returns:
        Dict with update info or error
    """
    async def _append():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Conditionally add timestamp and attribution to the row
        if include_metadata:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
            row_data = [timestamp, added_by or "Unknown"] + list(values)
        else:
            row_data = list(values)

        # Append to Sheet1 by default (covers full range to find last row)
        result = await append_rows(access_token, spreadsheet_id, "Sheet1!A:Z", [row_data])

        # Update last_accessed if successful
        if "error" not in result:
            from signal_bot.models import SheetsRegistry, db
            try:
                if _flask_app:
                    with _flask_app.app_context():
                        sheet = SheetsRegistry.query.filter_by(spreadsheet_id=spreadsheet_id).first()
                        if sheet:
                            sheet.last_accessed = datetime.utcnow()
                            db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update last_accessed: {e}")

            result["row_added"] = row_data

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
        if _flask_app:
            with _flask_app.app_context():
                sheets = SheetsRegistry.search_sheets(bot_data["id"], group_id, query)
                return {
                    "spreadsheets": [s.to_dict() for s in sheets],
                    "count": len(sheets),
                    "query": query,
                }
        return {"spreadsheets": [], "count": 0, "query": query}
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


# Default format patterns for common types
DEFAULT_FORMAT_PATTERNS = {
    "CURRENCY": "$#,##0.00",
    "PERCENT": "0.00%",
    "NUMBER": "#,##0.00",
    "DATE": "yyyy-mm-dd",
    "TEXT": "@",
}


def format_columns_sync(
    bot_data: dict,
    spreadsheet_id: str,
    columns: str,
    format_type: str,
    pattern: str = None
) -> dict:
    """
    Format columns with a specified number format (currency, percent, etc).

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        columns: Column range in A1 notation ('B' or 'B:E')
        format_type: One of CURRENCY, PERCENT, NUMBER, DATE, TEXT
        pattern: Optional custom format pattern

    Returns:
        Dict with result or error
    """
    async def _format():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheetId from metadata (need numeric ID, not string spreadsheet_id)
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]  # Use first sheet

        # Parse column range
        try:
            start_col, end_col = parse_column_range(columns)
        except Exception as e:
            return {"error": f"Invalid column range '{columns}': {e}"}

        # Use provided pattern or default
        format_pattern = pattern or DEFAULT_FORMAT_PATTERNS.get(format_type, "")

        # Build repeatCell request
        request = {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": format_type,
                            "pattern": format_pattern
                        }
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "columns": columns,
            "format_type": format_type,
            "pattern": format_pattern,
            "message": f"Formatted columns {columns} as {format_type}"
        }

    return _run_async(_format())


def clear_range_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str
) -> dict:
    """
    Clear values from a range in a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        range_notation: A1 notation range (e.g., 'Sheet1!A1:C10', 'B:B', 'A5:A10')

    Returns:
        Dict with result or error
    """
    async def _clear():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        result = await clear_range(access_token, spreadsheet_id, range_notation)

        if "error" in result:
            return result

        return {
            "success": True,
            "cleared_range": result.get("cleared_range"),
            "message": f"Cleared range {result.get('cleared_range', range_notation)}"
        }

    return _run_async(_clear())


def delete_rows_sync(
    bot_data: dict,
    spreadsheet_id: str,
    start_row: int,
    end_row: int = None
) -> dict:
    """
    Delete rows from a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        start_row: First row to delete (1-indexed)
        end_row: Last row to delete (1-indexed, inclusive). If None, deletes single row.

    Returns:
        Dict with result or error
    """
    async def _delete():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheetId from metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Convert to 0-indexed
        start_idx = start_row - 1
        end_idx = (end_row if end_row else start_row)  # end is exclusive in API

        request = {
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_idx,
                    "endIndex": end_idx
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        rows_deleted = end_idx - start_idx
        return {
            "success": True,
            "rows_deleted": rows_deleted,
            "message": f"Deleted {rows_deleted} row(s) starting at row {start_row}"
        }

    return _run_async(_delete())


def delete_columns_sync(
    bot_data: dict,
    spreadsheet_id: str,
    columns: str
) -> dict:
    """
    Delete columns from a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        columns: Column(s) to delete in A1 notation ('C' or 'C:E')

    Returns:
        Dict with result or error
    """
    async def _delete():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheetId from metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse column range
        try:
            start_col, end_col = parse_column_range(columns)
        except Exception as e:
            return {"error": f"Invalid column range '{columns}': {e}"}

        request = {
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_col,
                    "endIndex": end_col
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        cols_deleted = end_col - start_col
        return {
            "success": True,
            "columns_deleted": cols_deleted,
            "columns": columns,
            "message": f"Deleted column(s) {columns}"
        }

    return _run_async(_delete())


def insert_rows_sync(
    bot_data: dict,
    spreadsheet_id: str,
    start_row: int,
    num_rows: int = 1
) -> dict:
    """
    Insert empty rows into a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        start_row: Row number where new rows will be inserted (1-indexed)
        num_rows: Number of rows to insert (default 1)

    Returns:
        Dict with result or error
    """
    async def _insert():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheetId from metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Convert to 0-indexed
        start_idx = start_row - 1

        request = {
            "insertDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "ROWS",
                    "startIndex": start_idx,
                    "endIndex": start_idx + num_rows
                },
                "inheritFromBefore": start_idx > 0  # Inherit formatting from row above if not first row
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "rows_inserted": num_rows,
            "at_row": start_row,
            "message": f"Inserted {num_rows} row(s) at row {start_row}"
        }

    return _run_async(_insert())


def insert_columns_sync(
    bot_data: dict,
    spreadsheet_id: str,
    column: str,
    num_columns: int = 1
) -> dict:
    """
    Insert empty columns into a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        column: Column letter where new columns will be inserted (e.g., 'C')
        num_columns: Number of columns to insert (default 1)

    Returns:
        Dict with result or error
    """
    async def _insert():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheetId from metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse column
        try:
            start_col, _ = parse_column_range(column)
        except Exception as e:
            return {"error": f"Invalid column '{column}': {e}"}

        request = {
            "insertDimension": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_col,
                    "endIndex": start_col + num_columns
                },
                "inheritFromBefore": start_col > 0  # Inherit formatting from column to left if not first
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "columns_inserted": num_columns,
            "at_column": column,
            "message": f"Inserted {num_columns} column(s) at column {column}"
        }

    return _run_async(_insert())


# ============================================================================
# Sheet Management Functions (Batch 2)
# ============================================================================

def add_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    title: str
) -> dict:
    """
    Add a new sheet/tab to a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        title: Name for the new sheet

    Returns:
        Dict with new sheet info or error
    """
    async def _add():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        request = {
            "addSheet": {
                "properties": {
                    "title": title
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        # Extract the new sheet's properties from the response
        replies = result.get("replies", [])
        if replies and "addSheet" in replies[0]:
            sheet_props = replies[0]["addSheet"]["properties"]
            return {
                "success": True,
                "sheet_id": sheet_props.get("sheetId"),
                "title": sheet_props.get("title"),
                "message": f"Added new sheet '{title}'"
            }

        return {
            "success": True,
            "title": title,
            "message": f"Added new sheet '{title}'"
        }

    return _run_async(_add())


def delete_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    sheet_name: str
) -> dict:
    """
    Delete a sheet/tab from a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        sheet_name: Name of the sheet to delete

    Returns:
        Dict with result or error
    """
    async def _delete():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet ID from name
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        sheet_id = None
        for sheet in metadata.get("sheets", []):
            if sheet["title"].lower() == sheet_name.lower():
                sheet_id = sheet["sheet_id"]
                break

        if sheet_id is None:
            return {"error": f"Sheet '{sheet_name}' not found"}

        # Check if this is the only sheet
        if len(metadata.get("sheets", [])) == 1:
            return {"error": "Cannot delete the only sheet in a spreadsheet"}

        request = {
            "deleteSheet": {
                "sheetId": sheet_id
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "deleted_sheet": sheet_name,
            "message": f"Deleted sheet '{sheet_name}'"
        }

    return _run_async(_delete())


def rename_sheet_sync(
    bot_data: dict,
    spreadsheet_id: str,
    old_name: str,
    new_name: str
) -> dict:
    """
    Rename a sheet/tab in a spreadsheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        old_name: Current name of the sheet
        new_name: New name for the sheet

    Returns:
        Dict with result or error
    """
    async def _rename():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet ID from name
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        sheet_id = None
        for sheet in metadata.get("sheets", []):
            if sheet["title"].lower() == old_name.lower():
                sheet_id = sheet["sheet_id"]
                break

        if sheet_id is None:
            return {"error": f"Sheet '{old_name}' not found"}

        request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "title": new_name
                },
                "fields": "title"
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "old_name": old_name,
            "new_name": new_name,
            "message": f"Renamed sheet from '{old_name}' to '{new_name}'"
        }

    return _run_async(_rename())


def freeze_rows_sync(
    bot_data: dict,
    spreadsheet_id: str,
    num_rows: int,
    sheet_name: str = None
) -> dict:
    """
    Freeze rows at the top of a sheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        num_rows: Number of rows to freeze (0 to unfreeze)
        sheet_name: Optional sheet name (defaults to first sheet)

    Returns:
        Dict with result or error
    """
    async def _freeze():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet ID
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = None
        if sheet_name:
            for sheet in metadata.get("sheets", []):
                if sheet["title"].lower() == sheet_name.lower():
                    sheet_id = sheet["sheet_id"]
                    break
            if sheet_id is None:
                return {"error": f"Sheet '{sheet_name}' not found"}
        else:
            sheet_id = metadata["sheets"][0]["sheet_id"]

        request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenRowCount": num_rows
                    }
                },
                "fields": "gridProperties.frozenRowCount"
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        if num_rows == 0:
            return {
                "success": True,
                "message": "Unfroze all rows"
            }
        return {
            "success": True,
            "frozen_rows": num_rows,
            "message": f"Froze top {num_rows} row(s)"
        }

    return _run_async(_freeze())


def freeze_columns_sync(
    bot_data: dict,
    spreadsheet_id: str,
    num_columns: int,
    sheet_name: str = None
) -> dict:
    """
    Freeze columns at the left of a sheet.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        num_columns: Number of columns to freeze (0 to unfreeze)
        sheet_name: Optional sheet name (defaults to first sheet)

    Returns:
        Dict with result or error
    """
    async def _freeze():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet ID
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = None
        if sheet_name:
            for sheet in metadata.get("sheets", []):
                if sheet["title"].lower() == sheet_name.lower():
                    sheet_id = sheet["sheet_id"]
                    break
            if sheet_id is None:
                return {"error": f"Sheet '{sheet_name}' not found"}
        else:
            sheet_id = metadata["sheets"][0]["sheet_id"]

        request = {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {
                        "frozenColumnCount": num_columns
                    }
                },
                "fields": "gridProperties.frozenColumnCount"
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        if num_columns == 0:
            return {
                "success": True,
                "message": "Unfroze all columns"
            }
        return {
            "success": True,
            "frozen_columns": num_columns,
            "message": f"Froze left {num_columns} column(s)"
        }

    return _run_async(_freeze())


# ============================================================================
# Data Operations Functions (Batch 3)
# ============================================================================

def sort_range_sync(
    bot_data: dict,
    spreadsheet_id: str,
    sort_column: str,
    ascending: bool = True,
    range_notation: str = None,
    has_header: bool = True
) -> dict:
    """
    Sort data in a spreadsheet by a column.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        sort_column: Column to sort by (e.g., 'B')
        ascending: Sort ascending (True) or descending (False)
        range_notation: Optional range to sort (defaults to all data)
        has_header: If True, excludes first row from sort

    Returns:
        Dict with result or error
    """
    async def _sort():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet = metadata["sheets"][0]
        sheet_id = sheet["sheet_id"]
        row_count = sheet.get("row_count", 1000)
        col_count = sheet.get("col_count", 26)

        # Parse sort column
        try:
            sort_col_idx, _ = parse_column_range(sort_column)
        except Exception as e:
            return {"error": f"Invalid sort column '{sort_column}': {e}"}

        # Determine range to sort
        start_row = 1 if has_header else 0  # Skip header if present
        start_col = 0
        end_col = col_count

        if range_notation:
            # Parse custom range - for now just use full data area
            pass  # TODO: Parse A1 notation for custom ranges

        request = {
            "sortRange": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": row_count,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "sortSpecs": [
                    {
                        "dimensionIndex": sort_col_idx,
                        "sortOrder": "ASCENDING" if ascending else "DESCENDING"
                    }
                ]
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        order = "ascending" if ascending else "descending"
        return {
            "success": True,
            "sort_column": sort_column,
            "order": order,
            "message": f"Sorted by column {sort_column} ({order})"
        }

    return _run_async(_sort())


def auto_resize_columns_sync(
    bot_data: dict,
    spreadsheet_id: str,
    columns: str = None
) -> dict:
    """
    Auto-resize columns to fit content.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        columns: Optional column range (e.g., 'A:E'). If None, resizes all columns.

    Returns:
        Dict with result or error
    """
    async def _resize():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet = metadata["sheets"][0]
        sheet_id = sheet["sheet_id"]
        col_count = sheet.get("col_count", 26)

        # Determine column range
        if columns:
            try:
                start_col, end_col = parse_column_range(columns)
            except Exception as e:
                return {"error": f"Invalid column range '{columns}': {e}"}
        else:
            start_col = 0
            end_col = col_count

        request = {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": start_col,
                    "endIndex": end_col
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        col_desc = columns if columns else "all columns"
        return {
            "success": True,
            "columns": col_desc,
            "message": f"Auto-resized {col_desc} to fit content"
        }

    return _run_async(_resize())


def merge_cells_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str,
    merge_type: str = "MERGE_ALL"
) -> dict:
    """
    Merge cells in a range.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        range_notation: Range to merge in A1 notation (e.g., 'A1:C1')
        merge_type: MERGE_ALL (default), MERGE_COLUMNS, or MERGE_ROWS

    Returns:
        Dict with result or error
    """
    async def _merge():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse A1 notation range (e.g., "A1:C3")
        # Simple parser for common cases
        try:
            range_notation_clean = range_notation.upper().strip()
            if '!' in range_notation_clean:
                # Sheet1!A1:C3 format - strip sheet name
                range_notation_clean = range_notation_clean.split('!')[1]

            if ':' in range_notation_clean:
                start_cell, end_cell = range_notation_clean.split(':')
            else:
                start_cell = end_cell = range_notation_clean

            # Parse start cell
            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            start_col, _ = parse_column_range(start_col_str)
            start_row = int(start_row_str) - 1 if start_row_str else 0

            # Parse end cell
            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            end_col, _ = parse_column_range(end_col_str)
            end_col += 1  # Make exclusive
            end_row = int(end_row_str) if end_row_str else start_row + 1

        except Exception as e:
            return {"error": f"Invalid range '{range_notation}': {e}"}

        request = {
            "mergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "mergeType": merge_type
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "merged_range": range_notation,
            "merge_type": merge_type,
            "message": f"Merged cells {range_notation}"
        }

    return _run_async(_merge())


def unmerge_cells_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str
) -> dict:
    """
    Unmerge previously merged cells.

    Args:
        bot_data: Bot configuration dict
        spreadsheet_id: Google Sheets ID
        range_notation: Range to unmerge in A1 notation (e.g., 'A1:C1')

    Returns:
        Dict with result or error
    """
    async def _unmerge():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin panel."}

        # Get sheet metadata
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        if not metadata.get("sheets"):
            return {"error": "No sheets found in spreadsheet"}

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse A1 notation range (same logic as merge)
        try:
            range_notation_clean = range_notation.upper().strip()
            if '!' in range_notation_clean:
                range_notation_clean = range_notation_clean.split('!')[1]

            if ':' in range_notation_clean:
                start_cell, end_cell = range_notation_clean.split(':')
            else:
                start_cell = end_cell = range_notation_clean

            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            start_col, _ = parse_column_range(start_col_str)
            start_row = int(start_row_str) - 1 if start_row_str else 0

            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            end_col, _ = parse_column_range(end_col_str)
            end_col += 1
            end_row = int(end_row_str) if end_row_str else start_row + 1

        except Exception as e:
            return {"error": f"Invalid range '{range_notation}': {e}"}

        request = {
            "unmergeCells": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "unmerged_range": range_notation,
            "message": f"Unmerged cells {range_notation}"
        }

    return _run_async(_unmerge())


# =============================================================================
# BATCH 4: Formatting & Validation Tools
# =============================================================================

def conditional_format_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str,
    rule_type: str,
    condition_value: str = None,
    format_type: str = "background",
    color: str = "red"
) -> dict:
    """
    Add conditional formatting rule to a range.

    Args:
        bot_data: Bot configuration with Google credentials
        spreadsheet_id: The spreadsheet ID
        range_notation: Range in A1 notation (e.g., "B2:B100")
        rule_type: Type of condition - "greater_than", "less_than", "equals",
                   "contains", "not_empty", "is_empty"
        condition_value: Value to compare against (not needed for not_empty/is_empty)
        format_type: "background" or "text" - what to color
        color: Color name - "red", "green", "yellow", "orange", "blue", "purple"
    """

    # Color mappings (RGB 0-1 scale)
    COLORS = {
        "red": {"red": 0.918, "green": 0.6, "blue": 0.6},
        "green": {"red": 0.714, "green": 0.843, "blue": 0.659},
        "yellow": {"red": 1.0, "green": 0.949, "blue": 0.6},
        "orange": {"red": 0.988, "green": 0.733, "blue": 0.518},
        "blue": {"red": 0.624, "green": 0.773, "blue": 0.910},
        "purple": {"red": 0.796, "green": 0.651, "blue": 0.839}
    }

    # Rule type to API condition type mapping
    CONDITION_TYPES = {
        "greater_than": "NUMBER_GREATER",
        "less_than": "NUMBER_LESS",
        "equals": "NUMBER_EQ",
        "contains": "TEXT_CONTAINS",
        "not_empty": "NOT_BLANK",
        "is_empty": "BLANK"
    }

    async def _format():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin UI."}

        # Get spreadsheet metadata for sheetId
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse range notation (e.g., "B2:B100" -> columns 1-2, rows 1-100)
        try:
            if ':' in range_notation:
                start_cell, end_cell = range_notation.split(':')
            else:
                start_cell = end_cell = range_notation

            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            start_col, _ = parse_column_range(start_col_str)
            start_row = int(start_row_str) - 1 if start_row_str else 0

            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            end_col, _ = parse_column_range(end_col_str)
            end_col += 1
            end_row = int(end_row_str) if end_row_str else start_row + 1

        except Exception as e:
            return {"error": f"Invalid range '{range_notation}': {e}"}

        # Build the condition
        condition_type = CONDITION_TYPES.get(rule_type)
        if not condition_type:
            return {"error": f"Unknown rule_type '{rule_type}'. Use: greater_than, less_than, equals, contains, not_empty, is_empty"}

        boolean_rule = {
            "condition": {
                "type": condition_type
            },
            "format": {}
        }

        # Add condition value if needed
        if rule_type not in ["not_empty", "is_empty"] and condition_value is not None:
            boolean_rule["condition"]["values"] = [{"userEnteredValue": str(condition_value)}]

        # Set format (background or text color)
        color_value = COLORS.get(color.lower(), COLORS["red"])
        if format_type == "background":
            boolean_rule["format"]["backgroundColor"] = color_value
        else:
            boolean_rule["format"]["textFormat"] = {"foregroundColor": color_value}

        request = {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col
                    }],
                    "booleanRule": boolean_rule
                },
                "index": 0
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "range": range_notation,
            "rule": f"{rule_type} {condition_value or ''}".strip(),
            "format": f"{color} {format_type}",
            "message": f"Added conditional formatting: {rule_type} → {color} {format_type}"
        }

    return _run_async(_format())


def data_validation_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str,
    validation_type: str,
    values: list = None,
    min_value: float = None,
    max_value: float = None,
    strict: bool = True
) -> dict:
    """
    Add data validation to a range.

    Args:
        bot_data: Bot configuration with Google credentials
        spreadsheet_id: The spreadsheet ID
        range_notation: Range in A1 notation (e.g., "C2:C100")
        validation_type: "dropdown", "number_range", "date", "checkbox"
        values: List of allowed values for dropdown (e.g., ["Yes", "No", "Maybe"])
        min_value: Minimum value for number_range
        max_value: Maximum value for number_range
        strict: If True, reject invalid input; if False, show warning only
    """

    async def _validate():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin UI."}

        # Get spreadsheet metadata for sheetId
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse range notation
        try:
            if ':' in range_notation:
                start_cell, end_cell = range_notation.split(':')
            else:
                start_cell = end_cell = range_notation

            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            start_col, _ = parse_column_range(start_col_str)
            start_row = int(start_row_str) - 1 if start_row_str else 0

            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            end_col, _ = parse_column_range(end_col_str)
            end_col += 1
            end_row = int(end_row_str) if end_row_str else start_row + 1

        except Exception as e:
            return {"error": f"Invalid range '{range_notation}': {e}"}

        # Build validation rule based on type
        condition = {}

        if validation_type == "dropdown":
            if not values:
                return {"error": "dropdown validation requires 'values' list"}
            condition = {
                "type": "ONE_OF_LIST",
                "values": [{"userEnteredValue": str(v)} for v in values]
            }
        elif validation_type == "number_range":
            if min_value is not None and max_value is not None:
                condition = {
                    "type": "NUMBER_BETWEEN",
                    "values": [
                        {"userEnteredValue": str(min_value)},
                        {"userEnteredValue": str(max_value)}
                    ]
                }
            elif min_value is not None:
                condition = {
                    "type": "NUMBER_GREATER_THAN_EQ",
                    "values": [{"userEnteredValue": str(min_value)}]
                }
            elif max_value is not None:
                condition = {
                    "type": "NUMBER_LESS_THAN_EQ",
                    "values": [{"userEnteredValue": str(max_value)}]
                }
            else:
                return {"error": "number_range validation requires min_value and/or max_value"}
        elif validation_type == "date":
            condition = {"type": "DATE_IS_VALID"}
        elif validation_type == "checkbox":
            condition = {"type": "BOOLEAN"}
        else:
            return {"error": f"Unknown validation_type '{validation_type}'. Use: dropdown, number_range, date, checkbox"}

        request = {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col
                },
                "rule": {
                    "condition": condition,
                    "strict": strict,
                    "showCustomUi": validation_type == "dropdown"
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        detail = ""
        if validation_type == "dropdown":
            detail = f" with options: {', '.join(str(v) for v in values)}"
        elif validation_type == "number_range":
            detail = f" ({min_value} to {max_value})"

        return {
            "success": True,
            "range": range_notation,
            "validation_type": validation_type,
            "message": f"Added {validation_type} validation to {range_notation}{detail}"
        }

    return _run_async(_validate())


def alternating_colors_sync(
    bot_data: dict,
    spreadsheet_id: str,
    range_notation: str,
    header_color: str = "blue",
    first_band_color: str = "white",
    second_band_color: str = "lightgray"
) -> dict:
    """
    Add alternating row colors (banded rows) to a range.

    Args:
        bot_data: Bot configuration with Google credentials
        spreadsheet_id: The spreadsheet ID
        range_notation: Range in A1 notation (e.g., "A1:E100")
        header_color: Color for header row - "blue", "green", "gray", "orange", "purple"
        first_band_color: Color for odd rows - "white", "lightgray", "lightblue", etc.
        second_band_color: Color for even rows
    """

    # Extended color mappings for banding
    COLORS = {
        "white": {"red": 1.0, "green": 1.0, "blue": 1.0},
        "lightgray": {"red": 0.937, "green": 0.937, "blue": 0.937},
        "lightblue": {"red": 0.851, "green": 0.918, "blue": 0.965},
        "lightgreen": {"red": 0.851, "green": 0.918, "blue": 0.851},
        "lightyellow": {"red": 1.0, "green": 0.973, "blue": 0.835},
        "lightpurple": {"red": 0.918, "green": 0.875, "blue": 0.941},
        "blue": {"red": 0.267, "green": 0.435, "blue": 0.659},
        "green": {"red": 0.263, "green": 0.545, "blue": 0.318},
        "gray": {"red": 0.4, "green": 0.4, "blue": 0.4},
        "orange": {"red": 0.906, "green": 0.490, "blue": 0.169},
        "purple": {"red": 0.502, "green": 0.298, "blue": 0.647},
        "red": {"red": 0.8, "green": 0.2, "blue": 0.2}
    }

    async def _band():
        access_token = await get_valid_access_token(bot_data)
        if not access_token:
            return {"error": "Not connected to Google. Please connect via admin UI."}

        # Get spreadsheet metadata for sheetId
        metadata = await get_spreadsheet_metadata(access_token, spreadsheet_id)
        if "error" in metadata:
            return metadata

        sheet_id = metadata["sheets"][0]["sheet_id"]

        # Parse range notation
        try:
            if ':' in range_notation:
                start_cell, end_cell = range_notation.split(':')
            else:
                start_cell = end_cell = range_notation

            start_col_str = ''.join(c for c in start_cell if c.isalpha())
            start_row_str = ''.join(c for c in start_cell if c.isdigit())
            start_col, _ = parse_column_range(start_col_str)
            start_row = int(start_row_str) - 1 if start_row_str else 0

            end_col_str = ''.join(c for c in end_cell if c.isalpha())
            end_row_str = ''.join(c for c in end_cell if c.isdigit())
            end_col, _ = parse_column_range(end_col_str)
            end_col += 1
            end_row = int(end_row_str) if end_row_str else start_row + 1

        except Exception as e:
            return {"error": f"Invalid range '{range_notation}': {e}"}

        # Get colors
        header_rgb = COLORS.get(header_color.lower(), COLORS["blue"])
        first_rgb = COLORS.get(first_band_color.lower(), COLORS["white"])
        second_rgb = COLORS.get(second_band_color.lower(), COLORS["lightgray"])

        request = {
            "addBanding": {
                "bandedRange": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col
                    },
                    "rowProperties": {
                        "headerColor": header_rgb,
                        "firstBandColor": first_rgb,
                        "secondBandColor": second_rgb
                    }
                }
            }
        }

        result = await batch_update(access_token, spreadsheet_id, [request])

        if "error" in result:
            return result

        return {
            "success": True,
            "range": range_notation,
            "header_color": header_color,
            "band_colors": [first_band_color, second_band_color],
            "message": f"Added alternating colors to {range_notation}"
        }

    return _run_async(_band())
