"""
Tool executors package for OpenRouter native function calling.

This package contains tool execution classes organized by category:
- signal_executor: SignalToolExecutor for Signal bots
- base: Base classes and utility functions
- basic_tools: Weather, time, Wikipedia, dice, reaction mixins
- finance_executor: Stock/crypto financial data mixins
- sheets_core: Core Google Sheets operations mixins
- sheets_advanced: Advanced Google Sheets operations mixins
- calendar_executor: Google Calendar and trigger mixins
- dnd_executor: D&D Game Master tool mixins
- chat_log_executor: Chat log search tool mixins
"""

# Signal executor (main class combining all mixins)
from .signal_executor import SignalToolExecutor

# Utility functions
from .base import create_tool_executor_callback, process_tool_calls

__all__ = [
    'SignalToolExecutor',
    'create_tool_executor_callback',
    'process_tool_calls',
]
