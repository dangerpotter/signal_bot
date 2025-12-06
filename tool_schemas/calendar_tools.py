"""
Google Calendar tool schemas for Signal bots.

Tools for creating and managing calendars and events.
"""

# Google Calendar tools
CALENDAR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_calendar",
            "description": "Create a new Google Calendar for the group. By default, calendars are PUBLIC so everyone can view them via the share link. Use when someone wants to track events, schedule meetings, or coordinate activities. Share the returned URL with the group.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title for the calendar (e.g., 'Group Events 2025', 'Book Club Meetings')"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this calendar is for",
                        "default": ""
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone (e.g., 'America/New_York', 'Europe/London', 'UTC')",
                        "default": "UTC"
                    },
                    "make_public": {
                        "type": "boolean",
                        "description": "If true (default), calendar is publicly viewable via the share link. Set to false for private calendars only the owner can see.",
                        "default": True
                    }
                },
                "required": ["title"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_calendars",
            "description": "List all calendars created for this group. Returns titles, URLs, and creation info.",
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
            "name": "list_events",
            "description": "List upcoming events from a calendar. Use when someone asks what's coming up, what events are scheduled, or wants to see the calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID (from list_calendars or create_calendar)"
                    },
                    "time_min": {
                        "type": "string",
                        "description": "Start of time range in ISO 8601 format (e.g., '2025-01-01T00:00:00Z'). Defaults to now."
                    },
                    "time_max": {
                        "type": "string",
                        "description": "End of time range in ISO 8601 format. Defaults to unlimited."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of events to return (1-100)",
                        "default": 10
                    }
                },
                "required": ["calendar_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_event",
            "description": "Get details of a specific event by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "The event ID to retrieve"
                    }
                },
                "required": ["calendar_id", "event_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Create a new event on a calendar. Use when someone wants to add an event, schedule something, or create a meeting. Can invite attendees via email. Returns the event link that can be shared.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title/name"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in ISO 8601 format (e.g., '2025-01-15T14:00:00') or date for all-day events ('2025-01-15')"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "End time in ISO 8601 format or date for all-day events"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional event description/notes",
                        "default": ""
                    },
                    "location": {
                        "type": "string",
                        "description": "Optional location (address or place name)",
                        "default": ""
                    },
                    "all_day": {
                        "type": "boolean",
                        "description": "If true, creates an all-day event (use date format for start/end)",
                        "default": False
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone for the event times (e.g., 'America/New_York')",
                        "default": "UTC"
                    },
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of email addresses to invite. They will receive calendar invitations via email.",
                        "default": []
                    },
                    "send_notifications": {
                        "type": "boolean",
                        "description": "If true (default), send email invitations to attendees",
                        "default": True
                    }
                },
                "required": ["calendar_id", "title", "start_time", "end_time"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Update an existing event. Use when someone wants to change event details, reschedule, or modify an event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "The event ID to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New title (optional)"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "New start time in ISO 8601 format (optional)"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "New end time in ISO 8601 format (optional)"
                    },
                    "description": {
                        "type": "string",
                        "description": "New description (optional)"
                    },
                    "location": {
                        "type": "string",
                        "description": "New location (optional)"
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for new times",
                        "default": "UTC"
                    }
                },
                "required": ["calendar_id", "event_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": "Delete an event from a calendar. Use when someone wants to cancel or remove an event.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "event_id": {
                        "type": "string",
                        "description": "The event ID to delete"
                    }
                },
                "required": ["calendar_id", "event_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "quick_add_event",
            "description": "Create an event using natural language. Google parses the text to extract date, time, and details. Use for quick, informal event creation like 'Dinner tomorrow at 7pm at Mario's'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "text": {
                        "type": "string",
                        "description": "Natural language event description (e.g., 'Dinner with John at 7pm tomorrow at Olive Garden')"
                    }
                },
                "required": ["calendar_id", "text"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "share_calendar",
            "description": "Share a calendar with someone via email or make it publicly viewable. Use when someone wants to share the calendar link or invite others.",
            "parameters": {
                "type": "object",
                "properties": {
                    "calendar_id": {
                        "type": "string",
                        "description": "The Google Calendar ID"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address to share with (omit if making public)"
                    },
                    "role": {
                        "type": "string",
                        "enum": ["reader", "writer"],
                        "description": "Access level: 'reader' (view only) or 'writer' (can edit)",
                        "default": "reader"
                    },
                    "make_public": {
                        "type": "boolean",
                        "description": "If true, makes the calendar publicly viewable and returns a share link",
                        "default": False
                    }
                },
                "required": ["calendar_id"],
                "additionalProperties": False
            }
        }
    }
]
