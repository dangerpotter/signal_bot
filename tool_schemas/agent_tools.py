"""
Agent/GUI tool schemas.

Tools for the main GUI application and basic Signal bot functionality.
"""

from .constants import AVAILABLE_MODELS

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
