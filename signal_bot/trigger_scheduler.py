"""
Trigger scheduler for managing scheduled bot triggers.

Runs as a background task alongside the bot manager.
Checks for due triggers every 60 seconds and executes them.
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Optional, TYPE_CHECKING

from flask import Flask

if TYPE_CHECKING:
    from signal_bot.bot_manager import SignalBotManager

logger = logging.getLogger(__name__)

# Flask app reference for database context
_flask_app: Optional[Flask] = None


def set_flask_app(app: Flask):
    """Set Flask app for database context."""
    global _flask_app
    _flask_app = app


class TriggerScheduler:
    """
    Manages scheduled trigger execution.

    Design principles:
    - Checks every 60 seconds for due triggers
    - Skips missed triggers (doesn't queue them)
    - Automatically computes next_fire_time after each execution
    - Respects per-bot max_triggers limit
    """

    def __init__(self, bot_manager: "SignalBotManager"):
        """
        Args:
            bot_manager: Reference to SignalBotManager for sending messages
        """
        self.bot_manager = bot_manager
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler background task."""
        if self.running:
            return

        self.running = True
        self._task = asyncio.create_task(
            self._scheduler_loop(),
            name="trigger-scheduler"
        )
        logger.info("Trigger scheduler started")

    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Trigger scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop - runs every 60 seconds."""
        while self.running:
            try:
                await self._check_and_execute_triggers()
            except Exception as e:
                logger.error(f"Error in trigger scheduler: {e}", exc_info=True)

            await asyncio.sleep(60)  # Check every minute

    async def _check_and_execute_triggers(self):
        """Check for due triggers and execute them."""
        if not _flask_app:
            logger.warning("Flask app not set, skipping trigger check")
            return

        with _flask_app.app_context():
            from signal_bot.models import ScheduledTrigger, db

            # Find all triggers due for execution
            due_triggers = ScheduledTrigger.get_due_triggers()

            if due_triggers:
                logger.info(f"Found {len(due_triggers)} due trigger(s)")

            for trigger in due_triggers:
                try:
                    await self._execute_trigger(trigger)
                except Exception as e:
                    logger.error(f"Failed to execute trigger {trigger.id} ({trigger.name}): {e}", exc_info=True)

                # Update schedule after execution (whether successful or not)
                self._update_trigger_schedule(trigger, db)

    async def _execute_trigger(self, trigger):
        """Execute a single trigger."""
        from signal_bot.models import Bot, GroupConnection, ActivityLog, db

        bot = Bot.query.get(trigger.bot_id)
        group = GroupConnection.query.get(trigger.group_id)

        if not bot or not group:
            logger.warning(f"Trigger {trigger.id}: bot or group not found, disabling")
            trigger.enabled = False
            db.session.commit()
            return

        if not bot.enabled:
            logger.info(f"Trigger {trigger.id}: bot '{bot.name}' disabled, skipping")
            return

        if not group.enabled:
            logger.info(f"Trigger {trigger.id}: group '{group.name}' disabled, skipping")
            return

        logger.info(f"Executing trigger {trigger.id} ({trigger.trigger_type}): {trigger.name}")

        if trigger.trigger_type == "reminder":
            # Simple message - send directly
            await self._send_reminder(trigger, bot)

        elif trigger.trigger_type == "task":
            # AI task - invoke message handler with is_mentioned=True
            await self._execute_task(trigger, bot)

        # Update stats
        trigger.last_fired_at = datetime.utcnow()
        trigger.fire_count += 1

        # Log activity
        log = ActivityLog(
            event_type="trigger_fired",
            bot_id=trigger.bot_id,
            group_id=trigger.group_id,
            description=f"Trigger '{trigger.name}' ({trigger.trigger_type}) executed"
        )
        db.session.add(log)
        db.session.commit()

    async def _send_reminder(self, trigger, bot):
        """Send a reminder message directly to the group."""
        try:
            await self.bot_manager.send_message(
                phone_number=bot.phone_number,
                group_id=trigger.group_id,
                message=trigger.content,
                port=bot.signal_api_port
            )
            logger.info(f"Reminder sent for trigger {trigger.id}")
        except Exception as e:
            logger.error(f"Failed to send reminder for trigger {trigger.id}: {e}")

    async def _execute_task(self, trigger, bot):
        """Execute an AI task - the AI processes instructions and can use tools."""
        try:
            # Build bot_data dict from bot model
            bot_data = bot.to_dict()
            bot_data['phone_number'] = bot.phone_number
            bot_data['signal_api_port'] = bot.signal_api_port
            # Add Google credentials if needed
            bot_data['google_client_secret'] = bot.google_client_secret

            # Create callbacks for sending messages/images
            async def send_text(text, quote_timestamp=None, quote_author=None, mentions=None, text_styles=None):
                await self.bot_manager.send_message(
                    phone_number=bot.phone_number,
                    group_id=trigger.group_id,
                    message=text,
                    port=bot.signal_api_port,
                    quote_timestamp=quote_timestamp,
                    quote_author=quote_author,
                    mentions=mentions,
                    text_styles=text_styles
                )

            async def send_image(path):
                await self.bot_manager.send_image(
                    phone_number=bot.phone_number,
                    group_id=trigger.group_id,
                    image_path=path,
                    port=bot.signal_api_port
                )

            # Call message handler as if this were a @mention
            # The instructions become the "message" that triggers the AI
            await self.bot_manager.message_handler.handle_incoming_message(
                group_id=trigger.group_id,
                sender_name=f"[Scheduled: {trigger.name}]",
                sender_id="scheduled_trigger",
                message_text=trigger.content,
                bot_data=bot_data,
                is_mentioned=True,  # Force response
                send_callback=lambda t, *a, **k: asyncio.create_task(send_text(t, *a, **k)),
                send_image_callback=lambda p: asyncio.create_task(send_image(p))
            )

            logger.info(f"Task executed for trigger {trigger.id}")
        except Exception as e:
            logger.error(f"Failed to execute task for trigger {trigger.id}: {e}", exc_info=True)

    def _update_trigger_schedule(self, trigger, db):
        """Update trigger's next_fire_time or disable if complete."""
        if trigger.trigger_mode == "once":
            # One-time trigger - disable after execution
            trigger.enabled = False
            trigger.next_fire_time = None
            logger.info(f"One-time trigger {trigger.id} completed and disabled")

        elif trigger.trigger_mode == "recurring":
            # Compute next fire time
            next_time = self._compute_next_fire_time(trigger)

            # Check if we've passed the end date
            if trigger.end_date and next_time and next_time > trigger.end_date:
                trigger.enabled = False
                trigger.next_fire_time = None
                logger.info(f"Recurring trigger {trigger.id} reached end date and disabled")
            else:
                trigger.next_fire_time = next_time
                logger.info(f"Trigger {trigger.id} rescheduled for {next_time}")

        db.session.commit()

    def _compute_next_fire_time(self, trigger) -> Optional[datetime]:
        """
        Compute the next fire time for a recurring trigger.

        Handles: daily, weekly, monthly, custom interval patterns.
        """
        now = datetime.utcnow()

        # Get the time of day for the trigger
        trigger_time = trigger.recurrence_time or time(9, 0)  # Default 9:00 AM
        interval = trigger.recurrence_interval or 1

        if trigger.recurrence_pattern == "daily":
            # Next occurrence: today at trigger_time, or tomorrow if already passed
            today = now.date()
            candidate = datetime.combine(today, trigger_time)
            if candidate <= now:
                candidate += timedelta(days=interval)
            return candidate

        elif trigger.recurrence_pattern == "weekly":
            # Find next occurrence of the target day of week
            target_dow = trigger.recurrence_day_of_week if trigger.recurrence_day_of_week is not None else 0
            days_ahead = target_dow - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and datetime.combine(now.date(), trigger_time) <= now):
                # Target day already passed this week or is today but time passed
                days_ahead += 7 * interval
            next_date = now.date() + timedelta(days=days_ahead)
            return datetime.combine(next_date, trigger_time)

        elif trigger.recurrence_pattern == "monthly":
            # Next occurrence of target day of month
            target_day = trigger.recurrence_day_of_month or 1
            # Start with current month
            year = now.year
            month = now.month

            # Try to create date with target day
            while True:
                try:
                    # Handle months with fewer days
                    import calendar
                    last_day = calendar.monthrange(year, month)[1]
                    day = min(target_day, last_day)
                    candidate = datetime(year, month, day, trigger_time.hour, trigger_time.minute)

                    if candidate > now:
                        return candidate

                    # Move to next interval
                    month += interval
                    while month > 12:
                        month -= 12
                        year += 1
                except ValueError:
                    # Invalid date, move to next month
                    month += 1
                    if month > 12:
                        month = 1
                        year += 1

                # Safety limit
                if year > now.year + 10:
                    logger.error(f"Could not compute next fire time for trigger {trigger.id}")
                    return None

        elif trigger.recurrence_pattern == "custom":
            # Custom interval in minutes
            interval_minutes = interval
            last_fire = trigger.last_fired_at or trigger.created_at or now
            return last_fire + timedelta(minutes=interval_minutes)

        return None

    @staticmethod
    def compute_initial_fire_time(trigger) -> Optional[datetime]:
        """
        Compute the initial next_fire_time when a trigger is created.
        Called from admin UI or AI tool when creating a new trigger.
        """
        if trigger.trigger_mode == "once":
            return trigger.scheduled_time

        # For recurring, compute next occurrence
        now = datetime.utcnow()
        trigger_time = trigger.recurrence_time or time(9, 0)
        interval = trigger.recurrence_interval or 1

        if trigger.recurrence_pattern == "daily":
            today = now.date()
            candidate = datetime.combine(today, trigger_time)
            if candidate <= now:
                candidate += timedelta(days=interval)
            return candidate

        elif trigger.recurrence_pattern == "weekly":
            target_dow = trigger.recurrence_day_of_week if trigger.recurrence_day_of_week is not None else 0
            days_ahead = target_dow - now.weekday()
            if days_ahead < 0 or (days_ahead == 0 and datetime.combine(now.date(), trigger_time) <= now):
                days_ahead += 7
            next_date = now.date() + timedelta(days=days_ahead)
            return datetime.combine(next_date, trigger_time)

        elif trigger.recurrence_pattern == "monthly":
            target_day = trigger.recurrence_day_of_month or 1
            year = now.year
            month = now.month

            import calendar
            while True:
                last_day = calendar.monthrange(year, month)[1]
                day = min(target_day, last_day)
                candidate = datetime(year, month, day, trigger_time.hour, trigger_time.minute)

                if candidate > now:
                    return candidate

                month += 1
                if month > 12:
                    month = 1
                    year += 1

                if year > now.year + 2:
                    return None

        elif trigger.recurrence_pattern == "custom":
            # Custom interval starts from now
            return now + timedelta(minutes=interval)

        return None


# Singleton instance
_scheduler: Optional[TriggerScheduler] = None


def get_trigger_scheduler() -> Optional[TriggerScheduler]:
    """Get the global trigger scheduler instance."""
    return _scheduler


def create_trigger_scheduler(bot_manager: "SignalBotManager") -> TriggerScheduler:
    """Create the global trigger scheduler instance."""
    global _scheduler
    _scheduler = TriggerScheduler(bot_manager)
    return _scheduler
