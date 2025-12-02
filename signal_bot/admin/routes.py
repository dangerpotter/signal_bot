"""Flask routes for the admin interface."""

import uuid
from flask import render_template, request, jsonify, redirect, url_for, flash

from signal_bot.models import (
    db, Bot, GroupConnection, BotGroupAssignment,
    SystemPromptTemplate, ActivityLog, MemorySnippet, GroupMemberMemory, MessageLog
)


def register_routes(app):
    """Register all routes with the Flask app."""

    @app.route("/")
    def dashboard():
        """Main dashboard view."""
        bots = Bot.query.all()
        groups = GroupConnection.query.all()
        recent_activity = ActivityLog.query.order_by(
            ActivityLog.timestamp.desc()
        ).limit(20).all()

        return render_template("dashboard.html",
                               bots=bots,
                               groups=groups,
                               activity=recent_activity)

    @app.route("/bots")
    def bots_list():
        """Bot management page."""
        bots = Bot.query.all()
        prompts = SystemPromptTemplate.query.all()

        # Get available models from config
        try:
            from config import AI_MODELS
            models = list(AI_MODELS.keys())
        except ImportError:
            models = ["Claude Sonnet 4.5", "GPT-4o", "Gemini 2.5 Pro"]

        return render_template("bots.html",
                               bots=bots,
                               prompts=prompts,
                               models=models)

    @app.route("/bots/add", methods=["POST"])
    def add_bot():
        """Add a new bot."""
        name = request.form.get("name", "").strip()
        model = request.form.get("model", "").strip()
        phone_number = request.form.get("phone_number", "").strip() or None
        signal_api_port = int(request.form.get("signal_api_port", 8080))

        if not name or not model:
            flash("Name and model are required", "error")
            return redirect(url_for("bots_list"))

        bot_id = str(uuid.uuid4())[:8]
        bot = Bot(
            id=bot_id,
            name=name,
            model=model,
            phone_number=phone_number,
            signal_api_port=signal_api_port,
            enabled=False
        )
        db.session.add(bot)
        db.session.commit()

        _log_activity("bot_created", bot_id, None, f"Bot '{name}' created")
        flash(f"Bot '{name}' created successfully", "success")
        return redirect(url_for("bots_list"))

    @app.route("/bots/<bot_id>/toggle", methods=["POST"])
    def toggle_bot(bot_id):
        """Toggle bot enabled/disabled."""
        bot = Bot.query.get_or_404(bot_id)
        bot.enabled = not bot.enabled
        db.session.commit()

        status = "enabled" if bot.enabled else "disabled"
        _log_activity("bot_toggled", bot_id, None, f"Bot '{bot.name}' {status}")

        if request.headers.get("HX-Request"):
            return render_template("partials/bot_card.html", bot=bot)
        return redirect(url_for("bots_list"))

    @app.route("/bots/<bot_id>/edit", methods=["GET", "POST"])
    def edit_bot(bot_id):
        """Edit bot settings."""
        bot = Bot.query.get_or_404(bot_id)

        if request.method == "POST":
            bot.name = request.form.get("name", bot.name).strip()
            bot.model = request.form.get("model", bot.model).strip()
            bot.phone_number = request.form.get("phone_number", "").strip() or None
            bot.signal_api_port = int(request.form.get("signal_api_port", bot.signal_api_port))
            bot.system_prompt = request.form.get("system_prompt", "").strip() or None
            bot.respond_on_mention = request.form.get("respond_on_mention") == "on"
            bot.random_chance_percent = int(request.form.get("random_chance_percent", 15))
            bot.image_generation_enabled = request.form.get("image_generation_enabled") == "on"
            bot.web_search_enabled = request.form.get("web_search_enabled") == "on"
            bot.reaction_enabled = request.form.get("reaction_enabled") == "on"
            bot.reaction_chance_percent = int(request.form.get("reaction_chance_percent", 5))
            bot.llm_reaction_enabled = request.form.get("llm_reaction_enabled") == "on"

            db.session.commit()
            _log_activity("bot_updated", bot_id, None, f"Bot '{bot.name}' settings updated")
            flash(f"Bot '{bot.name}' updated successfully", "success")
            return redirect(url_for("bots_list"))

        prompts = SystemPromptTemplate.query.all()
        try:
            from config import AI_MODELS
            models = list(AI_MODELS.keys())
        except ImportError:
            models = ["Claude Sonnet 4.5", "GPT-4o", "Gemini 2.5 Pro"]

        return render_template("edit_bot.html", bot=bot, prompts=prompts, models=models)

    @app.route("/bots/<bot_id>/delete", methods=["POST"])
    def delete_bot(bot_id):
        """Delete a bot."""
        bot = Bot.query.get_or_404(bot_id)
        name = bot.name
        db.session.delete(bot)
        db.session.commit()

        _log_activity("bot_deleted", None, None, f"Bot '{name}' deleted")
        flash(f"Bot '{name}' deleted", "success")
        return redirect(url_for("bots_list"))

    @app.route("/groups")
    def groups_list():
        """Group management page."""
        groups = GroupConnection.query.all()
        bots = Bot.query.all()

        # Get members for each group from message logs
        group_members = {}
        for group in groups:
            members = db.session.query(
                MessageLog.sender_name,
                MessageLog.sender_id
            ).filter(
                MessageLog.group_id == group.id,
                MessageLog.is_bot == False
            ).distinct().all()
            group_members[group.id] = [
                {"name": m.sender_name, "id": m.sender_id}
                for m in members if m.sender_name
            ]

        return render_template("groups.html", groups=groups, bots=bots, group_members=group_members)

    @app.route("/groups/add", methods=["POST"])
    def add_group():
        """Add a new group connection."""
        group_id = request.form.get("group_id", "").strip()
        name = request.form.get("name", "").strip()

        if not group_id or not name:
            flash("Group ID and name are required", "error")
            return redirect(url_for("groups_list"))

        group = GroupConnection(id=group_id, name=name, enabled=True)
        db.session.add(group)
        db.session.commit()

        _log_activity("group_added", None, group_id, f"Group '{name}' added")
        flash(f"Group '{name}' added successfully", "success")
        return redirect(url_for("groups_list"))

    @app.route("/groups/<group_id>/assign", methods=["POST"])
    def assign_bot_to_group(group_id):
        """Assign a bot to a group."""
        group = GroupConnection.query.get_or_404(group_id)
        bot_id = request.form.get("bot_id")
        bot = Bot.query.get_or_404(bot_id)

        # Check if already assigned
        existing = BotGroupAssignment.query.filter_by(
            bot_id=bot_id, group_id=group_id
        ).first()

        if not existing:
            assignment = BotGroupAssignment(bot_id=bot_id, group_id=group_id)
            db.session.add(assignment)
            db.session.commit()
            _log_activity("bot_assigned", bot_id, group_id,
                          f"Bot '{bot.name}' assigned to '{group.name}'")

        return redirect(url_for("groups_list"))

    @app.route("/groups/<group_id>/unassign/<bot_id>", methods=["POST"])
    def unassign_bot_from_group(group_id, bot_id):
        """Remove a bot from a group."""
        assignment = BotGroupAssignment.query.filter_by(
            bot_id=bot_id, group_id=group_id
        ).first()

        if assignment:
            db.session.delete(assignment)
            db.session.commit()

        return redirect(url_for("groups_list"))

    @app.route("/groups/<group_id>/toggle", methods=["POST"])
    def toggle_group(group_id):
        """Toggle group enabled/disabled."""
        group = GroupConnection.query.get_or_404(group_id)
        group.enabled = not group.enabled
        db.session.commit()
        return redirect(url_for("groups_list"))

    @app.route("/groups/<group_id>/edit", methods=["GET", "POST"])
    def edit_group(group_id):
        """Edit group settings."""
        group = GroupConnection.query.get_or_404(group_id)

        if request.method == "POST":
            group.name = request.form.get("name", group.name).strip()
            new_group_id = request.form.get("group_id", group.id).strip()

            # If the group ID changed, we need to update the primary key
            if new_group_id != group.id:
                # Update all related assignments
                for assignment in group.bot_assignments:
                    assignment.group_id = new_group_id
                # Update group ID
                old_id = group.id
                db.session.execute(
                    db.text("UPDATE group_connections SET id = :new_id WHERE id = :old_id"),
                    {"new_id": new_group_id, "old_id": old_id}
                )
                db.session.commit()
                _log_activity("group_updated", None, new_group_id, f"Group '{group.name}' updated")
            else:
                db.session.commit()
                _log_activity("group_updated", None, group_id, f"Group '{group.name}' updated")

            flash(f"Group '{group.name}' updated successfully", "success")
            return redirect(url_for("groups_list"))

        bots = Bot.query.all()

        # Get members for this group from message logs
        members = db.session.query(
            MessageLog.sender_name,
            MessageLog.sender_id
        ).filter(
            MessageLog.group_id == group_id,
            MessageLog.is_bot == False
        ).distinct().all()
        group_members = [
            {"name": m.sender_name, "id": m.sender_id}
            for m in members if m.sender_name
        ]

        return render_template("edit_group.html", group=group, bots=bots, members=group_members)

    @app.route("/groups/<group_id>/delete", methods=["POST"])
    def delete_group(group_id):
        """Delete a group and its assignments."""
        group = GroupConnection.query.get_or_404(group_id)
        name = group.name

        # Delete all bot assignments for this group
        BotGroupAssignment.query.filter_by(group_id=group_id).delete()

        # Delete the group
        db.session.delete(group)
        db.session.commit()

        _log_activity("group_deleted", None, None, f"Group '{name}' deleted")
        flash(f"Group '{name}' deleted", "success")
        return redirect(url_for("groups_list"))

    @app.route("/prompts")
    def prompts_list():
        """System prompt templates page."""
        prompts = SystemPromptTemplate.query.all()
        return render_template("prompts.html", prompts=prompts)

    @app.route("/prompts/add", methods=["POST"])
    def add_prompt():
        """Add a new prompt template."""
        name = request.form.get("name", "").strip()
        prompt_text = request.form.get("prompt_text", "").strip()

        if not name or not prompt_text:
            flash("Name and prompt text are required", "error")
            return redirect(url_for("prompts_list"))

        prompt_id = str(uuid.uuid4())[:8]
        prompt = SystemPromptTemplate(
            id=prompt_id,
            name=name,
            prompt_text=prompt_text
        )
        db.session.add(prompt)
        db.session.commit()

        flash(f"Prompt '{name}' created successfully", "success")
        return redirect(url_for("prompts_list"))

    @app.route("/prompts/<prompt_id>/edit", methods=["GET", "POST"])
    def edit_prompt(prompt_id):
        """Edit a prompt template."""
        prompt = SystemPromptTemplate.query.get_or_404(prompt_id)

        if request.method == "POST":
            prompt.name = request.form.get("name", prompt.name).strip()
            prompt.prompt_text = request.form.get("prompt_text", prompt.prompt_text).strip()
            db.session.commit()
            flash(f"Prompt '{prompt.name}' updated successfully", "success")
            return redirect(url_for("prompts_list"))

        return render_template("edit_prompt.html", prompt=prompt)

    @app.route("/prompts/<prompt_id>/delete", methods=["POST"])
    def delete_prompt(prompt_id):
        """Delete a prompt template."""
        prompt = SystemPromptTemplate.query.get_or_404(prompt_id)
        name = prompt.name
        db.session.delete(prompt)
        db.session.commit()
        flash(f"Prompt '{name}' deleted", "success")
        return redirect(url_for("prompts_list"))

    @app.route("/memories")
    def memories_list():
        """View long-term memory snippets."""
        memories = MemorySnippet.query.order_by(
            MemorySnippet.timestamp.desc()
        ).limit(50).all()
        return render_template("memories.html", memories=memories)

    @app.route("/memories/<int:memory_id>/delete", methods=["POST"])
    def delete_memory(memory_id):
        """Delete a memory snippet."""
        memory = MemorySnippet.query.get_or_404(memory_id)
        db.session.delete(memory)
        db.session.commit()
        flash("Memory deleted", "success")
        return redirect(url_for("memories_list"))

    # Member Memories (location-aware personal info)
    @app.route("/member-memories")
    def member_memories_list():
        """View member memories organized by group."""
        groups = GroupConnection.query.all()
        memories_by_group = {}

        for group in groups:
            memories = GroupMemberMemory.query.filter_by(group_id=group.id).all()
            if memories:
                # Organize by member
                by_member = {}
                for mem in memories:
                    if mem.member_name not in by_member:
                        by_member[mem.member_name] = []
                    by_member[mem.member_name].append(mem)
                memories_by_group[group] = by_member

        # Slot types for the add form
        slot_types = [
            ("home_location", "Home Location"),
            ("travel_location", "Travel Location"),
            ("interests", "Interests"),
            ("media_prefs", "Media Preferences"),
            ("life_events", "Life Events"),
            ("work_info", "Work Info"),
            ("social_notes", "Social Notes"),
            ("response_prefs", "Response Preferences"),
        ]

        return render_template("member_memories.html",
                               memories_by_group=memories_by_group,
                               all_groups=groups,
                               slot_types=slot_types)

    @app.route("/member-memories/<int:memory_id>/delete", methods=["POST"])
    def delete_member_memory(memory_id):
        """Delete a member memory."""
        memory = GroupMemberMemory.query.get_or_404(memory_id)
        db.session.delete(memory)
        db.session.commit()
        flash("Member memory deleted", "success")
        return redirect(url_for("member_memories_list"))

    @app.route("/member-memories/<int:memory_id>/edit", methods=["POST"])
    def edit_member_memory(memory_id):
        """Edit a member memory."""
        memory = GroupMemberMemory.query.get_or_404(memory_id)

        memory.content = request.form.get("content", "").strip()
        memory.slot_type = request.form.get("slot_type", memory.slot_type)

        # Parse dates if provided
        valid_from = request.form.get("valid_from", "").strip()
        valid_until = request.form.get("valid_until", "").strip()

        from datetime import datetime
        memory.valid_from = datetime.fromisoformat(valid_from) if valid_from else None
        memory.valid_until = datetime.fromisoformat(valid_until) if valid_until else None

        db.session.commit()
        flash("Member memory updated", "success")
        return redirect(url_for("member_memories_list"))

    @app.route("/member-memories/add", methods=["POST"])
    def add_member_memory():
        """Add a new member memory manually."""
        import hashlib

        group_id = request.form.get("group_id", "").strip()
        member_name = request.form.get("member_name", "").strip()
        slot_type = request.form.get("slot_type", "").strip()
        content = request.form.get("content", "").strip()

        if not group_id or not member_name or not slot_type or not content:
            flash("All fields are required", "error")
            return redirect(url_for("member_memories_list"))

        # Generate a stable member_id from the name (for manual entries)
        member_id = "manual_" + hashlib.md5(member_name.lower().encode()).hexdigest()[:12]

        # Check if this slot already exists for this member (using the unique constraint fields)
        existing = GroupMemberMemory.query.filter_by(
            group_id=group_id,
            member_id=member_id,
            slot_type=slot_type
        ).first()

        # Also check for old-style "manual" member_id entries (for backwards compatibility)
        if not existing:
            existing = GroupMemberMemory.query.filter_by(
                group_id=group_id,
                member_id="manual",
                member_name=member_name,
                slot_type=slot_type
            ).first()
            if existing:
                # Migrate old entry to new member_id format
                existing.member_id = member_id

        from datetime import datetime
        valid_from = request.form.get("valid_from", "").strip()
        valid_until = request.form.get("valid_until", "").strip()

        if existing:
            # Update existing
            existing.content = content
            existing.member_name = member_name  # Update name in case capitalization changed
            existing.valid_from = datetime.fromisoformat(valid_from) if valid_from else None
            existing.valid_until = datetime.fromisoformat(valid_until) if valid_until else None
            flash(f"Updated {slot_type} for {member_name}", "success")
        else:
            # Create new
            memory = GroupMemberMemory(
                group_id=group_id,
                member_id=member_id,
                member_name=member_name,
                slot_type=slot_type,
                content=content,
                valid_from=datetime.fromisoformat(valid_from) if valid_from else None,
                valid_until=datetime.fromisoformat(valid_until) if valid_until else None
            )
            db.session.add(memory)
            flash(f"Added {slot_type} for {member_name}", "success")

        db.session.commit()
        return redirect(url_for("member_memories_list"))

    @app.route("/member-memories/force-scan/<group_id>", methods=["POST"])
    def force_memory_scan(group_id):
        """Force a memory scan for a group (admin action)."""
        import asyncio
        from signal_bot.member_memory_scanner import get_memory_scanner

        group = GroupConnection.query.get_or_404(group_id)

        try:
            scanner = get_memory_scanner()
            # Run the scan in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(scanner.force_scan_group(group_id))
            loop.close()

            flash(f"Memory scan completed for '{group.name}'", "success")
        except Exception as e:
            flash(f"Memory scan failed: {e}", "error")

        return redirect(url_for("member_memories_list"))

    # API endpoints for HTMX/AJAX
    @app.route("/api/status")
    def api_status():
        """Get current system status."""
        bots = Bot.query.filter_by(enabled=True).all()
        groups = GroupConnection.query.filter_by(enabled=True).all()

        return jsonify({
            "active_bots": len(bots),
            "active_groups": len(groups),
            "bots": [b.to_dict() for b in bots],
            "groups": [g.to_dict() for g in groups]
        })

    @app.route("/api/activity")
    def api_activity():
        """Get recent activity."""
        activity = ActivityLog.query.order_by(
            ActivityLog.timestamp.desc()
        ).limit(20).all()
        return jsonify([a.to_dict() for a in activity])

    @app.route("/api/groups/<group_id>/members")
    def api_group_members(group_id):
        """Get members for a specific group from message logs."""
        members = db.session.query(
            MessageLog.sender_name,
            MessageLog.sender_id
        ).filter(
            MessageLog.group_id == group_id,
            MessageLog.is_bot == False
        ).distinct().all()

        return jsonify([
            {"name": m.sender_name, "id": m.sender_id}
            for m in members if m.sender_name
        ])


def _log_activity(event_type: str, bot_id: str | None, group_id: str | None, description: str):
    """Log an activity event."""
    log = ActivityLog(
        event_type=event_type,
        bot_id=bot_id,
        group_id=group_id,
        description=description
    )
    db.session.add(log)
    db.session.commit()
