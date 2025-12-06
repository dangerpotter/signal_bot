"""
Scheduled trigger tool schemas for Signal bots.

Tools for creating and managing scheduled reminders and AI tasks.
"""

# Scheduled trigger tools
TRIGGER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_trigger",
            "description": "Create a scheduled trigger for reminders or AI tasks. Reminders send a message directly at the scheduled time. AI tasks execute instructions (using your tools like weather, finance, sheets) at the scheduled time. Use when someone asks you to remind them about something, track something on a schedule, or perform recurring tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Short descriptive name for this trigger (e.g., 'Daily BTC Update', 'Trip Reminder')"
                    },
                    "trigger_type": {
                        "type": "string",
                        "enum": ["reminder", "task"],
                        "description": "'reminder' sends a message directly. 'task' makes the AI process instructions with access to all tools."
                    },
                    "content": {
                        "type": "string",
                        "description": "For reminders: the message to send. For tasks: detailed instructions for the AI (e.g., 'Check BTC price, add to our spreadsheet, and post a summary')"
                    },
                    "trigger_mode": {
                        "type": "string",
                        "enum": ["once", "recurring"],
                        "description": "'once' fires at a specific time then disables. 'recurring' repeats on a schedule."
                    },
                    "scheduled_time": {
                        "type": "string",
                        "description": "For one-time triggers: ISO 8601 datetime when to fire (e.g., '2025-03-05T14:00:00'). IMPORTANT: This time is in the timezone specified by the 'timezone' parameter. Always use get_datetime first to get the current time, then calculate the target time in that same timezone."
                    },
                    "recurrence_pattern": {
                        "type": "string",
                        "enum": ["daily", "weekly", "monthly", "custom"],
                        "description": "For recurring: 'daily', 'weekly' (specify day_of_week), 'monthly' (specify day_of_month), or 'custom' (interval in minutes)"
                    },
                    "recurrence_interval": {
                        "type": "integer",
                        "description": "Every N periods (e.g., every 2 days, every 1 week). For 'custom' pattern, this is minutes.",
                        "default": 1
                    },
                    "recurrence_time": {
                        "type": "string",
                        "description": "Time of day in HH:MM format (e.g., '08:00', '14:30'). Default: '09:00'",
                        "default": "09:00"
                    },
                    "recurrence_day_of_week": {
                        "type": "integer",
                        "description": "For weekly: day of week (0=Monday, 1=Tuesday, ..., 6=Sunday)"
                    },
                    "recurrence_day_of_month": {
                        "type": "integer",
                        "description": "For monthly: day of month (1-28 recommended to avoid month-end issues)"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone for the scheduled_time or recurrence_time (e.g., 'America/New_York', 'America/Chicago', 'UTC'). ALWAYS specify this to match the timezone used in get_datetime. Default: 'UTC'",
                        "default": "UTC"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional ISO 8601 datetime after which recurring triggers stop. Omit for 'run forever'."
                    }
                },
                "required": ["name", "trigger_type", "content", "trigger_mode"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_triggers",
            "description": "List all scheduled triggers for this group. Shows active triggers, their schedules, and when they'll fire next.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_disabled": {
                        "type": "boolean",
                        "description": "Include disabled/completed triggers in the list",
                        "default": False
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_trigger",
            "description": "Cancel (delete) a scheduled trigger. Use when someone wants to stop a reminder or scheduled task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger_id": {
                        "type": "integer",
                        "description": "The ID of the trigger to cancel (from list_triggers)"
                    },
                    "trigger_name": {
                        "type": "string",
                        "description": "Alternatively, the name of the trigger to cancel (case-insensitive partial match)"
                    }
                },
                "required": [],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_trigger",
            "description": "Update an existing trigger's schedule, content, or status. Use to modify reminder text, change timing, or pause/resume triggers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "trigger_id": {
                        "type": "integer",
                        "description": "The ID of the trigger to update (from list_triggers)"
                    },
                    "name": {
                        "type": "string",
                        "description": "New name for the trigger"
                    },
                    "content": {
                        "type": "string",
                        "description": "New message or instructions"
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable (true) or disable (false) the trigger"
                    },
                    "recurrence_time": {
                        "type": "string",
                        "description": "New time of day in HH:MM format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "New end date (ISO 8601) or empty string to clear"
                    }
                },
                "required": ["trigger_id"],
                "additionalProperties": False
            }
        }
    }
]
