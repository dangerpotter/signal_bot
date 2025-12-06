"""
Calendar and trigger tool executor mixin for Signal bots.

Contains Google Calendar and scheduled trigger tool methods.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CalendarTriggersMixin:
    """Mixin providing Google Calendar and trigger tool execution methods."""

    # Type hints for attributes provided by SignalToolExecutorBase
    bot_data: dict
    group_id: str
    sender_name: Optional[str]

    def _calendar_enabled(self) -> bool:
        """Check if Google Calendar is enabled and connected."""
        return (
            self.bot_data.get('google_calendar_enabled', False) and
            self.bot_data.get('google_connected', False)
        )

    def _execute_create_calendar(self, arguments: dict) -> dict:
        """Execute the create_calendar tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected. Connect via admin panel."}

        title = arguments.get("title", "")
        description = arguments.get("description", "")
        timezone = arguments.get("timezone", "UTC")
        make_public = arguments.get("make_public", True)

        if not title:
            return {"success": False, "message": "Title is required"}

        try:
            from signal_bot.google_calendar_client import create_calendar_sync

            result = create_calendar_sync(
                bot_data=self.bot_data,
                group_id=self.group_id,
                title=title,
                description=description,
                timezone=timezone,
                created_by=self.sender_name,
                make_public=make_public
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            # Build message based on public status
            url = result.get('share_link') or result.get('url', 'URL unavailable')
            if result.get('is_public'):
                msg = f"Created public calendar '{title}'. Anyone can view it here: {url}"
            else:
                warning = result.get('share_warning', '')
                if warning:
                    msg = f"Created calendar '{title}'. {warning}. URL: {url}"
                else:
                    msg = f"Created private calendar '{title}'. Only the owner can view it. URL: {url}"

            return {
                "success": True,
                "data": result,
                "message": msg
            }

        except Exception as e:
            logger.error(f"Error creating calendar: {e}")
            return {"success": False, "message": f"Error creating calendar: {str(e)}"}

    def _execute_list_calendars(self, arguments: dict) -> dict:
        """Execute the list_calendars tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        try:
            from signal_bot.google_calendar_client import list_calendars_sync

            result = list_calendars_sync(
                bot_data=self.bot_data,
                group_id=self.group_id
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} calendar(s) for this group"
            }

        except Exception as e:
            logger.error(f"Error listing calendars: {e}")
            return {"success": False, "message": f"Error listing calendars: {str(e)}"}

    def _execute_list_events(self, arguments: dict) -> dict:
        """Execute the list_events tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        time_min = arguments.get("time_min")
        time_max = arguments.get("time_max")
        max_results = arguments.get("max_results", 10)

        if not calendar_id:
            return {"success": False, "message": "calendar_id is required"}

        try:
            from signal_bot.google_calendar_client import list_events_sync

            result = list_events_sync(
                bot_data=self.bot_data,
                calendar_id=calendar_id,
                time_min=time_min,
                time_max=time_max,
                max_results=max_results
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": f"Found {result.get('count', 0)} event(s)"
            }

        except Exception as e:
            logger.error(f"Error listing events: {e}")
            return {"success": False, "message": f"Error listing events: {str(e)}"}

    def _execute_get_event(self, arguments: dict) -> dict:
        """Execute the get_event tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        event_id = arguments.get("event_id", "")

        if not calendar_id or not event_id:
            return {"success": False, "message": "calendar_id and event_id are required"}

        try:
            from signal_bot.google_calendar_client import get_event_sync

            result = get_event_sync(self.bot_data, calendar_id, event_id)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return {"success": False, "message": f"Error getting event: {str(e)}"}

    def _execute_create_event(self, arguments: dict) -> dict:
        """Execute the create_event tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        title = arguments.get("title", "")
        start_time = arguments.get("start_time", "")
        end_time = arguments.get("end_time", "")
        description = arguments.get("description", "")
        location = arguments.get("location", "")
        all_day = arguments.get("all_day", False)
        timezone = arguments.get("timezone", "UTC")
        attendees = arguments.get("attendees", [])
        send_notifications = arguments.get("send_notifications", True)

        if not calendar_id:
            return {"success": False, "message": "calendar_id is required"}
        if not title:
            return {"success": False, "message": "title is required"}
        if not start_time or not end_time:
            return {"success": False, "message": "start_time and end_time are required"}

        # Validate attendee emails (basic check)
        if attendees:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            invalid = [e for e in attendees if not re.match(email_pattern, e)]
            if invalid:
                return {"success": False, "message": f"Invalid email addresses: {', '.join(invalid)}"}

        try:
            from signal_bot.google_calendar_client import create_event_sync

            result = create_event_sync(
                bot_data=self.bot_data,
                calendar_id=calendar_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                description=description,
                location=location,
                all_day=all_day,
                timezone=timezone,
                attendees=attendees if attendees else None,
                send_notifications=send_notifications
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            event = result.get("event", {})
            html_link = event.get("html_link", "")
            link_msg = f" Event link: {html_link}" if html_link else ""

            # Add attendee info to message
            attendee_msg = ""
            if result.get("invitations_sent") and result.get("attendees"):
                attendee_msg = f" Invitations sent to: {', '.join(result['attendees'])}"

            return {
                "success": True,
                "data": result,
                "message": f"Created event '{title}' on {event.get('start', 'scheduled')}.{link_msg}{attendee_msg}"
            }

        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"success": False, "message": f"Error creating event: {str(e)}"}

    def _execute_update_event(self, arguments: dict) -> dict:
        """Execute the update_event tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        event_id = arguments.get("event_id", "")

        if not calendar_id or not event_id:
            return {"success": False, "message": "calendar_id and event_id are required"}

        # Build updates dict from provided arguments
        updates = {}
        for field in ["title", "start_time", "end_time", "description", "location", "timezone", "all_day"]:
            if field in arguments and arguments[field] is not None:
                updates[field] = arguments[field]

        if not updates:
            return {"success": False, "message": "No updates provided"}

        try:
            from signal_bot.google_calendar_client import update_event_sync

            result = update_event_sync(self.bot_data, calendar_id, event_id, updates)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {
                "success": True,
                "data": result,
                "message": "Event updated successfully"
            }

        except Exception as e:
            logger.error(f"Error updating event: {e}")
            return {"success": False, "message": f"Error updating event: {str(e)}"}

    def _execute_delete_event(self, arguments: dict) -> dict:
        """Execute the delete_event tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        event_id = arguments.get("event_id", "")

        if not calendar_id or not event_id:
            return {"success": False, "message": "calendar_id and event_id are required"}

        try:
            from signal_bot.google_calendar_client import delete_event_sync

            result = delete_event_sync(self.bot_data, calendar_id, event_id)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            return {"success": True, "message": "Event deleted successfully"}

        except Exception as e:
            logger.error(f"Error deleting event: {e}")
            return {"success": False, "message": f"Error deleting event: {str(e)}"}

    def _execute_quick_add_event(self, arguments: dict) -> dict:
        """Execute the quick_add_event tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        text = arguments.get("text", "")

        if not calendar_id:
            return {"success": False, "message": "calendar_id is required"}
        if not text:
            return {"success": False, "message": "text is required"}

        try:
            from signal_bot.google_calendar_client import quick_add_event_sync

            result = quick_add_event_sync(self.bot_data, calendar_id, text)

            if "error" in result:
                return {"success": False, "message": result["error"]}

            event = result.get("event", {})
            html_link = event.get("html_link", "")
            link_msg = f" Event link: {html_link}" if html_link else ""

            return {
                "success": True,
                "data": result,
                "message": f"Created event '{event.get('title', text)}'.{link_msg}"
            }

        except Exception as e:
            logger.error(f"Error quick adding event: {e}")
            return {"success": False, "message": f"Error quick adding event: {str(e)}"}

    def _execute_share_calendar(self, arguments: dict) -> dict:
        """Execute the share_calendar tool call."""
        if not self._calendar_enabled():
            return {"success": False, "message": "Google Calendar not enabled or not connected."}

        calendar_id = arguments.get("calendar_id", "")
        email = arguments.get("email")
        role = arguments.get("role", "reader")
        make_public = arguments.get("make_public", False)

        if not calendar_id:
            return {"success": False, "message": "calendar_id is required"}
        if not email and not make_public:
            return {"success": False, "message": "Provide email to share with, or set make_public=true"}

        try:
            from signal_bot.google_calendar_client import share_calendar_sync

            result = share_calendar_sync(
                bot_data=self.bot_data,
                calendar_id=calendar_id,
                email=email,
                role=role,
                make_public=make_public
            )

            if "error" in result:
                return {"success": False, "message": result["error"]}

            if make_public:
                return {
                    "success": True,
                    "data": result,
                    "message": f"Calendar is now public. Share link: {result.get('share_link', '')}"
                }
            else:
                return {
                    "success": True,
                    "data": result,
                    "message": f"Calendar shared with {email} as {role}"
                }

        except Exception as e:
            logger.error(f"Error sharing calendar: {e}")
            return {"success": False, "message": f"Error sharing calendar: {str(e)}"}

    # =========================================================================
    # Scheduled Trigger Tools
    # =========================================================================

    def _execute_create_trigger(self, arguments: dict) -> dict:
        """Execute the create_trigger tool call."""
        if not self.bot_data.get('triggers_enabled', True):
            return {"success": False, "message": "Scheduled triggers disabled for this bot"}

        try:
            from datetime import datetime, time
            from signal_bot.models import ScheduledTrigger, Bot, db
            from signal_bot.trigger_scheduler import TriggerScheduler

            bot_id = self.bot_data.get('id')
            bot = Bot.query.get(bot_id)

            if not bot:
                return {"success": False, "message": "Bot not found"}

            # Check trigger limit
            current_count = ScheduledTrigger.query.filter_by(bot_id=bot_id, enabled=True).count()
            if current_count >= bot.max_triggers:
                return {
                    "success": False,
                    "message": f"Trigger limit reached ({bot.max_triggers}). Cancel an existing trigger first."
                }

            # Required fields
            name = arguments.get("name")
            trigger_type = arguments.get("trigger_type")
            content = arguments.get("content")
            trigger_mode = arguments.get("trigger_mode")

            if not all([name, trigger_type, content, trigger_mode]):
                return {"success": False, "message": "Missing required fields: name, trigger_type, content, trigger_mode"}

            if trigger_type not in ["reminder", "task"]:
                return {"success": False, "message": "trigger_type must be 'reminder' or 'task'"}

            if trigger_mode not in ["once", "recurring"]:
                return {"success": False, "message": "trigger_mode must be 'once' or 'recurring'"}

            # Create trigger
            trigger = ScheduledTrigger(
                bot_id=bot_id,
                group_id=self.group_id,
                name=name,
                trigger_type=trigger_type,
                content=content,
                trigger_mode=trigger_mode,
                created_via="ai_tool",
                created_by=self.sender_name
            )

            # Handle one-time scheduling
            if trigger_mode == "once":
                scheduled_time_str = arguments.get("scheduled_time")
                if scheduled_time_str:
                    # Parse the datetime
                    naive_dt = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00').replace('+00:00', ''))

                    # Convert from specified timezone to UTC
                    timezone_str = arguments.get("timezone", "UTC")
                    trigger.timezone = timezone_str

                    if timezone_str and timezone_str != "UTC":
                        import pytz
                        try:
                            local_tz = pytz.timezone(timezone_str)
                            # Localize the naive datetime to the specified timezone
                            local_dt = local_tz.localize(naive_dt)
                            # Convert to UTC
                            utc_dt = local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
                            trigger.scheduled_time = utc_dt
                        except Exception as tz_err:
                            # Fall back to treating as UTC if timezone invalid
                            trigger.scheduled_time = naive_dt
                    else:
                        trigger.scheduled_time = naive_dt

            # Handle recurring scheduling
            else:
                trigger.recurrence_pattern = arguments.get("recurrence_pattern", "daily")
                trigger.recurrence_interval = arguments.get("recurrence_interval", 1)
                trigger.timezone = arguments.get("timezone", "UTC")

                recurrence_time_str = arguments.get("recurrence_time", "09:00")
                if recurrence_time_str:
                    h, m = map(int, recurrence_time_str.split(":"))
                    trigger.recurrence_time = time(h, m)

                if arguments.get("recurrence_day_of_week") is not None:
                    trigger.recurrence_day_of_week = arguments.get("recurrence_day_of_week")

                if arguments.get("recurrence_day_of_month") is not None:
                    trigger.recurrence_day_of_month = arguments.get("recurrence_day_of_month")

                end_date_str = arguments.get("end_date")
                if end_date_str:
                    trigger.end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00').replace('+00:00', ''))

            # Compute initial fire time
            trigger.next_fire_time = TriggerScheduler.compute_initial_fire_time(trigger)

            db.session.add(trigger)
            db.session.commit()

            # Format schedule description
            if trigger_mode == "once":
                fire_time_str = trigger.next_fire_time.strftime('%Y-%m-%d %H:%M') if trigger.next_fire_time else 'unknown'
                schedule_desc = f"at {fire_time_str} UTC"
            else:
                pattern = trigger.recurrence_pattern
                interval = trigger.recurrence_interval
                time_str = trigger.recurrence_time.strftime('%H:%M') if trigger.recurrence_time else '09:00'

                if pattern == "daily":
                    schedule_desc = f"every {interval} day(s) at {time_str}"
                elif pattern == "weekly":
                    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    day_name = days[trigger.recurrence_day_of_week] if trigger.recurrence_day_of_week is not None else "Monday"
                    schedule_desc = f"every {interval} week(s) on {day_name} at {time_str}"
                elif pattern == "monthly":
                    schedule_desc = f"every {interval} month(s) on day {trigger.recurrence_day_of_month or 1} at {time_str}"
                else:
                    schedule_desc = f"every {interval} minutes"

                if trigger.end_date:
                    schedule_desc += f" until {trigger.end_date.strftime('%Y-%m-%d')}"
                else:
                    schedule_desc += " (runs forever)"

            type_desc = "reminder" if trigger_type == "reminder" else "AI task"

            return {
                "success": True,
                "data": {
                    "trigger_id": trigger.id,
                    "name": name,
                    "trigger_type": trigger_type,
                    "schedule": schedule_desc,
                    "next_fire": trigger.next_fire_time.strftime('%Y-%m-%d %H:%M UTC') if trigger.next_fire_time else None
                },
                "message": f"Created {type_desc} '{name}'. Schedule: {schedule_desc}. Next fire: {trigger.next_fire_time.strftime('%Y-%m-%d %H:%M UTC') if trigger.next_fire_time else 'Not scheduled'}."
            }

        except Exception as e:
            logger.error(f"Error creating trigger: {e}", exc_info=True)
            return {"success": False, "message": f"Error creating trigger: {str(e)}"}

    def _execute_list_triggers(self, arguments: dict) -> dict:
        """Execute the list_triggers tool call."""
        try:
            from signal_bot.models import ScheduledTrigger

            bot_id = self.bot_data.get('id')
            include_disabled = arguments.get("include_disabled", False)

            query = ScheduledTrigger.query.filter_by(
                bot_id=bot_id,
                group_id=self.group_id
            )

            if not include_disabled:
                query = query.filter_by(enabled=True)

            triggers = query.order_by(ScheduledTrigger.next_fire_time.asc()).all()

            if not triggers:
                return {
                    "success": True,
                    "data": {"triggers": [], "count": 0},
                    "message": "No triggers found for this group"
                }

            trigger_list = []
            for t in triggers:
                trigger_info = {
                    "id": t.id,
                    "name": t.name,
                    "type": t.trigger_type,
                    "mode": t.trigger_mode,
                    "enabled": t.enabled,
                    "content_preview": t.content[:100] + "..." if len(t.content) > 100 else t.content,
                    "next_fire": t.next_fire_time.strftime('%Y-%m-%d %H:%M UTC') if t.next_fire_time else None,
                    "last_fired": t.last_fired_at.strftime('%Y-%m-%d %H:%M UTC') if t.last_fired_at else None,
                    "fire_count": t.fire_count
                }

                if t.trigger_mode == "recurring":
                    trigger_info["pattern"] = t.recurrence_pattern
                    trigger_info["interval"] = t.recurrence_interval
                    if t.recurrence_time:
                        trigger_info["time"] = t.recurrence_time.strftime('%H:%M')
                    if t.end_date:
                        trigger_info["end_date"] = t.end_date.strftime('%Y-%m-%d')

                trigger_list.append(trigger_info)

            return {
                "success": True,
                "data": {"triggers": trigger_list, "count": len(trigger_list)},
                "message": f"Found {len(trigger_list)} trigger(s)"
            }

        except Exception as e:
            logger.error(f"Error listing triggers: {e}")
            return {"success": False, "message": f"Error listing triggers: {str(e)}"}

    def _execute_cancel_trigger(self, arguments: dict) -> dict:
        """Execute the cancel_trigger tool call."""
        try:
            from signal_bot.models import ScheduledTrigger, db

            bot_id = self.bot_data.get('id')
            trigger_id = arguments.get("trigger_id")
            trigger_name = arguments.get("trigger_name")

            if not trigger_id and not trigger_name:
                return {"success": False, "message": "Provide either trigger_id or trigger_name"}

            # Find trigger
            trigger = None
            if trigger_id:
                trigger = ScheduledTrigger.query.filter_by(
                    id=trigger_id,
                    bot_id=bot_id,
                    group_id=self.group_id
                ).first()
            elif trigger_name:
                # Case-insensitive partial match
                trigger = ScheduledTrigger.query.filter(
                    ScheduledTrigger.bot_id == bot_id,
                    ScheduledTrigger.group_id == self.group_id,
                    ScheduledTrigger.name.ilike(f"%{trigger_name}%")
                ).first()

            if not trigger:
                return {"success": False, "message": f"Trigger not found"}

            name = trigger.name
            db.session.delete(trigger)
            db.session.commit()

            return {
                "success": True,
                "message": f"Cancelled trigger '{name}'"
            }

        except Exception as e:
            logger.error(f"Error cancelling trigger: {e}")
            return {"success": False, "message": f"Error cancelling trigger: {str(e)}"}

    def _execute_update_trigger(self, arguments: dict) -> dict:
        """Execute the update_trigger tool call."""
        try:
            from datetime import time
            from signal_bot.models import ScheduledTrigger, db
            from signal_bot.trigger_scheduler import TriggerScheduler

            bot_id = self.bot_data.get('id')
            trigger_id = arguments.get("trigger_id")

            if not trigger_id:
                return {"success": False, "message": "trigger_id is required"}

            trigger = ScheduledTrigger.query.filter_by(
                id=trigger_id,
                bot_id=bot_id,
                group_id=self.group_id
            ).first()

            if not trigger:
                return {"success": False, "message": f"Trigger {trigger_id} not found"}

            # Update fields if provided
            updates = []

            if "name" in arguments:
                trigger.name = arguments["name"]
                updates.append("name")

            if "content" in arguments:
                trigger.content = arguments["content"]
                updates.append("content")

            if "enabled" in arguments:
                trigger.enabled = arguments["enabled"]
                if trigger.enabled:
                    # Recompute next fire time when re-enabling
                    trigger.next_fire_time = TriggerScheduler.compute_initial_fire_time(trigger)
                updates.append("enabled" if trigger.enabled else "disabled")

            if "recurrence_time" in arguments:
                h, m = map(int, arguments["recurrence_time"].split(":"))
                trigger.recurrence_time = time(h, m)
                trigger.next_fire_time = TriggerScheduler.compute_initial_fire_time(trigger)
                updates.append("time")

            if "end_date" in arguments:
                if arguments["end_date"]:
                    from datetime import datetime
                    trigger.end_date = datetime.fromisoformat(arguments["end_date"].replace('Z', '+00:00').replace('+00:00', ''))
                else:
                    trigger.end_date = None
                updates.append("end_date")

            if not updates:
                return {"success": False, "message": "No updates provided"}

            db.session.commit()

            return {
                "success": True,
                "data": {
                    "trigger_id": trigger.id,
                    "name": trigger.name,
                    "enabled": trigger.enabled,
                    "next_fire": trigger.next_fire_time.strftime('%Y-%m-%d %H:%M UTC') if trigger.next_fire_time else None
                },
                "message": f"Updated trigger '{trigger.name}': {', '.join(updates)}"
            }

        except Exception as e:
            logger.error(f"Error updating trigger: {e}")
            return {"success": False, "message": f"Error updating trigger: {str(e)}"}

