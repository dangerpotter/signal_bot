"""
Fast-path tool routing based on message content.

Routes obvious single-domain requests directly to focused tool sets,
bypassing meta-tool expansion for better accuracy and lower latency.
"""
import re
from typing import Optional, Set, Tuple

# HIGH-CONFIDENCE: Fast-path immediately (unambiguous)
HIGH_CONFIDENCE_KEYWORDS = {
    "calendar": {"calendar", "event", "appointment", "meeting"},
    "weather": {"weather", "forecast", "temperature", "humidity"},
    "time": {"timezone", "unix timestamp"},
    "wikipedia": {"wikipedia", "wiki article"},
    "dice": {"roll dice", "d20", "d6", "d4", "d8", "d10", "d12", "advantage", "disadvantage"},
    "chat_log": {"chat log", "chat history", "conversation history", "search history"},
}

# MEDIUM-CONFIDENCE: Only fast-path if no competing context
MEDIUM_CONFIDENCE_KEYWORDS = {
    "calendar": {"schedule", "remind me on", "when is"},
    "weather": {"rain", "sunny", "cloudy", "degrees"},
    "time": {"what time", "what day", "current date"},
    "triggers": {"every day at", "recurring", "cron"},
}

# FINANCE: Ticker pattern detection (aggressive fast-path)
TICKER_PATTERN = re.compile(r'\$[A-Z]{1,5}\b|[A-Z]{2,5}\s+(stock|price|shares)')
FINANCE_STRONG_SIGNALS = {"stock price", "market cap", "p/e ratio", "dividends", "nasdaq", "nyse"}

# SHEETS: Strong signals only (conservative)
SHEETS_STRONG_SIGNALS = {"spreadsheet", "google sheet", "add to sheet", "update the sheet"}

# D&D: Context signals that suppress finance fast-path
DND_CONTEXT_SIGNALS = {"campaign", "character", "inventory", "gold pieces", "dungeon"}


def detect_tool_domains(message: str, dnd_enabled: bool = False) -> Set[str]:
    """
    Detect which tool domains match the message.

    Returns set of domain names. Fast-path only triggers for exactly 1 match.
    - Empty set: no matches, use full system
    - Single item: fast-path candidate
    - Multiple items: use full system (ambiguous)
    """
    message_lower = message.lower()
    matched = set()

    # Check high-confidence keywords first
    for domain, keywords in HIGH_CONFIDENCE_KEYWORDS.items():
        if any(kw in message_lower for kw in keywords):
            matched.add(domain)

    # Finance: Use ticker pattern detection
    if TICKER_PATTERN.search(message):
        # Suppress if D&D context is strong (avoid "stock of arrows" confusion)
        if not (dnd_enabled and any(sig in message_lower for sig in DND_CONTEXT_SIGNALS)):
            matched.add("finance")
    elif any(sig in message_lower for sig in FINANCE_STRONG_SIGNALS):
        matched.add("finance")

    # Sheets: Strong signals only
    if any(sig in message_lower for sig in SHEETS_STRONG_SIGNALS):
        matched.add("sheets")

    # Medium-confidence: only add if no high-confidence matches yet
    if len(matched) == 0:
        for domain, keywords in MEDIUM_CONFIDENCE_KEYWORDS.items():
            if any(kw in message_lower for kw in keywords):
                matched.add(domain)

    return matched


def get_fast_path_tools(domain: str, bot_data: dict) -> Optional[list]:
    """
    Return focused tool set for a single domain.

    Returns None if the domain is not enabled in bot_data.
    Always includes DICE_TOOLS (always-on).
    Includes REACTION_TOOL if enabled (cross-cutting feature).
    """
    from .basic_tools import WEATHER_TOOL, TIME_TOOLS, WIKIPEDIA_TOOLS, DICE_TOOLS, REACTION_TOOL
    from .calendar_tools import CALENDAR_TOOLS
    from .trigger_tools import TRIGGER_TOOLS
    from .finance_tools import FINANCE_TOOLS
    from .chat_log_tools import CHAT_LOG_TOOLS

    # Check if domain is enabled
    enabled_map = {
        "calendar": bot_data.get("google_calendar_enabled") and bot_data.get("google_connected"),
        "weather": bot_data.get("weather_enabled"),
        "time": bot_data.get("time_enabled"),
        "wikipedia": bot_data.get("wikipedia_enabled"),
        "dice": True,  # Always enabled
        "finance": bot_data.get("finance_enabled"),
        "sheets": bot_data.get("google_sheets_enabled") and bot_data.get("google_connected"),
        "triggers": bot_data.get("triggers_enabled"),
        "chat_log": bot_data.get("chat_log_enabled"),
    }

    if not enabled_map.get(domain, False):
        return None

    # Map domain to tool set
    tool_map = {
        "calendar": list(CALENDAR_TOOLS),
        "weather": [WEATHER_TOOL],
        "time": list(TIME_TOOLS),
        "wikipedia": list(WIKIPEDIA_TOOLS),
        "dice": list(DICE_TOOLS),
        "triggers": list(TRIGGER_TOOLS),
        "finance": list(FINANCE_TOOLS),  # All 11 tools - skip meta expansion!
        "chat_log": list(CHAT_LOG_TOOLS),
    }

    # Sheets: conservative fast-path - pre-expand sheets_core only
    if domain == "sheets":
        from .helpers import get_sheets_tools_for_category, get_sheets_meta_tools
        core_tools = get_sheets_tools_for_category("sheets_core")
        other_metas = [m for m in get_sheets_meta_tools() if m["function"]["name"] != "sheets_core"]
        tools = core_tools + other_metas + list(DICE_TOOLS)
        if bot_data.get("reaction_tool_enabled"):
            tools.append(REACTION_TOOL)
        return tools

    # Get base tools for domain
    base_tools = tool_map.get(domain, [])

    # Always include dice (unless domain IS dice)
    if domain != "dice":
        base_tools = base_tools + list(DICE_TOOLS)

    # Include reaction tool if enabled (cross-cutting feature)
    if bot_data.get("reaction_tool_enabled"):
        base_tools = base_tools + [REACTION_TOOL]

    return base_tools


def route_tools_for_message(
    message: str,
    bot_data: dict,
    expanded_categories: Optional[dict] = None
) -> Tuple[list, bool, Optional[str]]:
    """
    Route to appropriate tools based on message content.

    Implements fast-path routing for obvious single-domain requests.
    Falls back to full meta-tool system for ambiguous or multi-domain requests.

    Args:
        message: The user's message text
        bot_data: Bot configuration dictionary with feature flags
        expanded_categories: Current meta-tool expansion state (for fallback)

    Returns:
        Tuple of (tools_list, fast_path_used, matched_domain)
        - tools_list: List of tool definitions
        - fast_path_used: True if fast-path was used
        - matched_domain: Domain name if fast-path, None otherwise
    """
    from .helpers import get_tools_for_context

    dnd_enabled = bot_data.get("dnd_enabled") and bot_data.get("google_connected")
    domains = detect_tool_domains(message, dnd_enabled=dnd_enabled)

    # Only fast-path for exactly 1 domain match
    if len(domains) == 1:
        domain = next(iter(domains))
        tools = get_fast_path_tools(domain, bot_data)
        if tools:
            return tools, True, domain

    # Fallback: full meta-tool system (0 matches or 2+ matches)
    tools = get_tools_for_context(
        context="signal",
        image_enabled=bot_data.get("image_generation_enabled", False),
        weather_enabled=bot_data.get("weather_enabled", False),
        finance_enabled=bot_data.get("finance_enabled", False),
        time_enabled=bot_data.get("time_enabled", False),
        wikipedia_enabled=bot_data.get("wikipedia_enabled", False),
        reaction_enabled=bot_data.get("reaction_tool_enabled", False),
        sheets_enabled=bot_data.get("google_sheets_enabled", False) and bot_data.get("google_connected", False),
        calendar_enabled=bot_data.get("google_calendar_enabled", False) and bot_data.get("google_connected", False),
        member_memory_enabled=bot_data.get("member_memory_tools_enabled", False),
        triggers_enabled=bot_data.get("triggers_enabled", True),
        dnd_enabled=dnd_enabled,
        chat_log_enabled=bot_data.get("chat_log_enabled", False),
        expanded_categories=expanded_categories
    )
    return tools, False, None
