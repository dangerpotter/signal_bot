"""
Helper functions for tool schemas.

Contains meta-tool generation, tool selection, and model capability detection.
"""

from typing import Optional

from .constants import TOOL_CAPABLE_MODEL_PATTERNS
from .agent_tools import AGENT_TOOLS, SIGNAL_TOOLS
from .basic_tools import WEATHER_TOOL, TIME_TOOLS, WIKIPEDIA_TOOLS, REACTION_TOOL, DICE_TOOLS
from .finance_tools import FINANCE_TOOLS, FINANCE_CATEGORIES
from .sheets_tools import SHEETS_TOOLS, SHEETS_CATEGORIES
from .calendar_tools import CALENDAR_TOOLS
from .memory_tools import MEMBER_MEMORY_TOOLS
from .trigger_tools import TRIGGER_TOOLS
from .dnd_tools import DND_TOOLS
from .chat_log_tools import CHAT_LOG_TOOLS

# Combined lookup for all meta-tool categories
ALL_META_CATEGORIES = {**FINANCE_CATEGORIES, **SHEETS_CATEGORIES}


def get_meta_tools_for_categories(categories: dict) -> list:
    """Generate meta-tool definitions from a categories dict."""
    meta_tools = []
    for name, info in categories.items():
        meta_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"] + f". Available tools: {', '.join(info['sub_tools'])}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {
                            "type": "string",
                            "description": "Brief description of what you want to accomplish"
                        }
                    },
                    "required": ["intent"],
                    "additionalProperties": False
                }
            }
        })
    return meta_tools


def get_finance_meta_tools() -> list:
    """Get the 3 finance meta-tools for Phase 1."""
    return get_meta_tools_for_categories(FINANCE_CATEGORIES)


def get_sheets_meta_tools() -> list:
    """Get the 12 sheets meta-tools for Phase 1."""
    return get_meta_tools_for_categories(SHEETS_CATEGORIES)


def get_tools_for_category(category: str, source_tools: list, categories: dict) -> list:
    """Get actual tool definitions for a category (Phase 2 expansion)."""
    if category not in categories:
        return []
    sub_tool_names = set(categories[category]["sub_tools"])
    return [t for t in source_tools if t["function"]["name"] in sub_tool_names]


def get_finance_tools_for_category(category: str) -> list:
    """Get finance tools for a specific category."""
    return get_tools_for_category(category, FINANCE_TOOLS, FINANCE_CATEGORIES)


def get_sheets_tools_for_category(category: str) -> list:
    """Get sheets tools for a specific category."""
    return get_tools_for_category(category, SHEETS_TOOLS, SHEETS_CATEGORIES)


def get_tools_for_context(
    context: str = "gui",
    image_enabled: bool = False,
    weather_enabled: bool = False,
    finance_enabled: bool = False,
    time_enabled: bool = False,
    wikipedia_enabled: bool = False,
    reaction_enabled: bool = False,
    sheets_enabled: bool = False,
    calendar_enabled: bool = False,
    member_memory_enabled: bool = False,
    triggers_enabled: bool = False,
    dnd_enabled: bool = False,
    chat_log_enabled: bool = False,
    expanded_categories: Optional[dict] = None
) -> list:
    """
    Return appropriate tools based on context and enabled features.

    Uses two-phase meta-tool expansion for large tool groups (>5 tools):
    - Phase 1: Returns meta-tools (category selectors) instead of all tools
    - Phase 2: When expanded_categories specifies a category, returns that
               category's actual tools plus remaining meta-tools

    Args:
        context: "gui" for main app (all tools), "signal" for Signal bot
        image_enabled: Include image generation tool (Signal bot only)
        weather_enabled: Include weather tool (Signal bot only)
        finance_enabled: Include finance tools (Signal bot only)
        time_enabled: Include time/date tools (Signal bot only)
        wikipedia_enabled: Include Wikipedia tools (Signal bot only)
        reaction_enabled: Include emoji reaction tool (Signal bot only)
        sheets_enabled: Include Google Sheets tools (Signal bot only)
        calendar_enabled: Include Google Calendar tools (Signal bot only)
        member_memory_enabled: Include member memory tools (Signal bot only)
        triggers_enabled: Include scheduled trigger tools (Signal bot only)
        dnd_enabled: Include D&D Game Master tools (Signal bot only)
        chat_log_enabled: Include chat log search tools (Signal bot only)
        expanded_categories: Dict mapping tool group to expanded category name
                            e.g. {"finance": "finance_quotes", "sheets": "sheets_core"}

    Returns:
        List of tool definitions appropriate for the context
    """
    expanded_categories = expanded_categories or {}

    if context == "signal":
        tools = []
        if image_enabled:
            tools.extend(SIGNAL_TOOLS)
        if weather_enabled:
            tools.append(WEATHER_TOOL)

        # Finance tools - use two-phase expansion
        if finance_enabled:
            finance_expanded = expanded_categories.get("finance", set())
            if finance_expanded:
                # Phase 2: Show expanded categories' tools + remaining meta-tools
                for category in finance_expanded:
                    tools.extend(get_finance_tools_for_category(category))
                tools.extend([m for m in get_finance_meta_tools()
                             if m["function"]["name"] not in finance_expanded])
            else:
                # Phase 1: Show only meta-tools
                tools.extend(get_finance_meta_tools())

        if time_enabled:
            tools.extend(TIME_TOOLS)
        if wikipedia_enabled:
            tools.extend(WIKIPEDIA_TOOLS)
        if reaction_enabled:
            tools.append(REACTION_TOOL)

        # Sheets tools - use two-phase expansion
        if sheets_enabled:
            sheets_expanded = expanded_categories.get("sheets", set())
            if sheets_expanded:
                # Phase 2: Show expanded categories' tools + remaining meta-tools
                for category in sheets_expanded:
                    tools.extend(get_sheets_tools_for_category(category))
                tools.extend([m for m in get_sheets_meta_tools()
                             if m["function"]["name"] not in sheets_expanded])
            else:
                # Phase 1: Show only meta-tools
                tools.extend(get_sheets_meta_tools())

        # Calendar tools - simple list (9 tools, no meta-expansion needed)
        if calendar_enabled:
            tools.extend(CALENDAR_TOOLS)

        if member_memory_enabled:
            tools.extend(MEMBER_MEMORY_TOOLS)

        # Trigger tools - simple list (4 tools)
        if triggers_enabled:
            tools.extend(TRIGGER_TOOLS)

        # D&D Game Master tools - for running campaigns (10 tools)
        if dnd_enabled:
            tools.extend(DND_TOOLS)

        # Chat log search tools (2 tools)
        if chat_log_enabled:
            tools.extend(CHAT_LOG_TOOLS)

        # Dice tools - always available (no toggle needed)
        tools.extend(DICE_TOOLS)

        return tools
    return AGENT_TOOLS


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
