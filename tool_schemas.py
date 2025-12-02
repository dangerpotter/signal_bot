"""
Tool schemas for OpenRouter native function calling.

Defines OpenAI-compatible tool specifications for agent commands.
These replace the regex-parsed !command syntax with structured function calls.
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

# Tool definitions in OpenAI function calling format
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text description. Use when you want to create visual content to share with the group. Be specific and detailed in your prompt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed description of the image to generate. Be specific about style, composition, lighting, subject matter, mood, and artistic direction."
                    }
                },
                "required": ["prompt"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_video",
            "description": "Generate a short video clip using Sora. Use for cinematic scenes or dynamic visual content. Write prompts in film direction style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Film-direction style prompt describing shot type, subject, action, setting, lighting, camera motion, and mood. Be cinematic and specific."
                    }
                },
                "required": ["prompt"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_ai",
            "description": "Invite another AI model to join the conversation. Use to add different perspectives or specialized capabilities. Maximum 5 AIs can participate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": f"The model name to add. Available: {', '.join(AVAILABLE_MODELS[:10])}... and more."
                    },
                    "persona": {
                        "type": "string",
                        "description": "Optional persona or role for the new AI participant (e.g., 'the skeptic', 'chaos agent', 'voice of reason')"
                    }
                },
                "required": ["model"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_ai",
            "description": "Remove an AI participant from the conversation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The AI identifier to remove (e.g., 'AI-3', 'AI-2')"
                    }
                },
                "required": ["target"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mute_self",
            "description": "Skip your next turn to listen and observe the conversation without contributing. Use when you want to let others speak.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_models",
            "description": "Query the list of available AI models that can be invited to the conversation.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    }
]

# Signal bot only supports image generation
SIGNAL_TOOLS = [
    tool for tool in AGENT_TOOLS
    if tool["function"]["name"] == "generate_image"
]


def get_tools_for_context(context: str = "gui") -> list:
    """
    Return appropriate tools based on context.

    Args:
        context: "gui" for main app (all tools), "signal" for Signal bot (image only)

    Returns:
        List of tool definitions appropriate for the context
    """
    if context == "signal":
        return SIGNAL_TOOLS
    return AGENT_TOOLS


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
