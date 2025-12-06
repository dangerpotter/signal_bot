"""
Tool schemas for OpenRouter native function calling.

This is a compatibility shim that re-exports from the tool_schemas package.
The actual implementations are in tool_schemas/*.py
"""

# Re-export everything from the package for backward compatibility
from tool_schemas import (
    # Constants
    AVAILABLE_MODELS,
    TOOL_CAPABLE_MODEL_PATTERNS,
    # Tool definitions
    AGENT_TOOLS,
    SIGNAL_TOOLS,
    WEATHER_TOOL,
    TIME_TOOLS,
    WIKIPEDIA_TOOLS,
    REACTION_TOOL,
    DICE_TOOLS,
    FINANCE_TOOLS,
    SHEETS_TOOLS,
    CALENDAR_TOOLS,
    MEMBER_MEMORY_TOOLS,
    TRIGGER_TOOLS,
    DND_TOOLS,
    # Categories
    FINANCE_CATEGORIES,
    SHEETS_CATEGORIES,
    ALL_META_CATEGORIES,
    # Functions
    get_meta_tools_for_categories,
    get_finance_meta_tools,
    get_sheets_meta_tools,
    get_tools_for_category,
    get_finance_tools_for_category,
    get_sheets_tools_for_category,
    get_tools_for_context,
    model_supports_tools,
)

__all__ = [
    'AVAILABLE_MODELS',
    'TOOL_CAPABLE_MODEL_PATTERNS',
    'AGENT_TOOLS',
    'SIGNAL_TOOLS',
    'WEATHER_TOOL',
    'TIME_TOOLS',
    'WIKIPEDIA_TOOLS',
    'REACTION_TOOL',
    'DICE_TOOLS',
    'FINANCE_TOOLS',
    'SHEETS_TOOLS',
    'CALENDAR_TOOLS',
    'MEMBER_MEMORY_TOOLS',
    'TRIGGER_TOOLS',
    'DND_TOOLS',
    'FINANCE_CATEGORIES',
    'SHEETS_CATEGORIES',
    'ALL_META_CATEGORIES',
    'get_meta_tools_for_categories',
    'get_finance_meta_tools',
    'get_sheets_meta_tools',
    'get_tools_for_category',
    'get_finance_tools_for_category',
    'get_sheets_tools_for_category',
    'get_tools_for_context',
    'model_supports_tools',
]
