"""
Tool schemas package for OpenRouter native function calling.

This package contains tool definitions organized by category:
- agent_tools: GUI/multi-agent conversation tools
- basic_tools: Weather, time, Wikipedia, reaction, dice tools
- finance_tools: Stock/crypto financial data tools
- sheets_tools: Google Sheets operations (70+ tools)
- calendar_tools: Google Calendar operations
- memory_tools: Member memory management
- trigger_tools: Scheduled triggers
- dnd_tools: D&D Game Master tools
- helpers: Meta-tool generation and context selection
- constants: Model lists and capability patterns
"""

# Constants
from .constants import AVAILABLE_MODELS, TOOL_CAPABLE_MODEL_PATTERNS

# Agent/GUI tools
from .agent_tools import AGENT_TOOLS, SIGNAL_TOOLS

# Basic tools (weather, time, wikipedia, reaction, dice)
from .basic_tools import (
    WEATHER_TOOL,
    TIME_TOOLS,
    WIKIPEDIA_TOOLS,
    REACTION_TOOL,
    DICE_TOOLS,
)

# Finance tools
from .finance_tools import FINANCE_TOOLS, FINANCE_CATEGORIES

# Google Sheets tools
from .sheets_tools import SHEETS_TOOLS, SHEETS_CATEGORIES

# Google Calendar tools
from .calendar_tools import CALENDAR_TOOLS

# Member memory tools
from .memory_tools import MEMBER_MEMORY_TOOLS

# Scheduled trigger tools
from .trigger_tools import TRIGGER_TOOLS

# D&D Game Master tools
from .dnd_tools import DND_TOOLS

# Chat log search tools
from .chat_log_tools import CHAT_LOG_TOOLS

# Helper functions
from .helpers import (
    ALL_META_CATEGORIES,
    get_meta_tools_for_categories,
    get_finance_meta_tools,
    get_sheets_meta_tools,
    get_tools_for_category,
    get_finance_tools_for_category,
    get_sheets_tools_for_category,
    get_tools_for_context,
    model_supports_tools,
)

# Fast-path routing
from .routing import (
    route_tools_for_message,
    detect_tool_domains,
    get_fast_path_tools,
)

__all__ = [
    # Constants
    'AVAILABLE_MODELS',
    'TOOL_CAPABLE_MODEL_PATTERNS',
    # Tool definitions
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
    'CHAT_LOG_TOOLS',
    # Categories
    'FINANCE_CATEGORIES',
    'SHEETS_CATEGORIES',
    'ALL_META_CATEGORIES',
    # Functions
    'get_meta_tools_for_categories',
    'get_finance_meta_tools',
    'get_sheets_meta_tools',
    'get_tools_for_category',
    'get_finance_tools_for_category',
    'get_sheets_tools_for_category',
    'get_tools_for_context',
    'model_supports_tools',
    # Routing
    'route_tools_for_message',
    'detect_tool_domains',
    'get_fast_path_tools',
]
