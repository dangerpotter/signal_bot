"""
Tool executor for bridging OpenRouter tool calls to existing command execution.

This is a compatibility shim that re-exports from the tool_executors package.
The actual implementations are in tool_executors/*.py
"""

# Re-export everything from the package for backward compatibility
from tool_executors import (
    ToolExecutor,
    SignalToolExecutor,
    create_tool_executor_callback,
    process_tool_calls,
)

__all__ = [
    'ToolExecutor',
    'SignalToolExecutor',
    'create_tool_executor_callback',
    'process_tool_calls',
]
