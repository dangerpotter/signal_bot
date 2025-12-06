"""
Constants for tool schemas.

Contains model lists and capability patterns.
"""

# Available AI models for the add_ai tool
AVAILABLE_MODELS = [
    "Claude Opus 4.5", "Claude 3 Opus", "Claude Sonnet 4.5", "Claude Haiku 4.5",
    "Claude Sonnet 4", "Claude 4 Opus", "Claude Opus 4.1", "Claude 3.7 Sonnet",
    "Gemini 3 Pro", "Gemini 2.5 Pro", "Gemini 2.5 Flash",
    "GPT 5.1", "GPT 5", "GPT 5 Pro", "GPT 4o", "GPT 4.1",
    "Grok 4", "Grok 3",
    "DeepSeek R1",
    "Kimi K2", "Kimi K2 Thinking",
    "Qwen 3 Max",
]

# Models known to support OpenAI-compatible function/tool calling via OpenRouter
TOOL_CAPABLE_MODEL_PATTERNS = [
    # Claude models (Anthropic)
    "claude-opus-4", "claude-sonnet-4", "claude-haiku-4",
    "claude-3-opus", "claude-3-sonnet", "claude-3.5-sonnet", "claude-3.5-haiku",
    "claude-3.7-sonnet",
    # OpenAI models
    "openai/gpt-5", "openai/gpt-4o", "openai/gpt-4.1", "openai/o1", "openai/o3",
    # Google models
    "google/gemini-3", "google/gemini-2.5", "google/gemini-2.0",
    # Grok
    "x-ai/grok-4", "x-ai/grok-3",
    # Others with tool support
    "anthropic/",  # Any anthropic model
]
