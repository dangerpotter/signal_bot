"""
D&D Game Master tool executor mixin for Signal bots.

Contains D&D campaign management tool methods.
"""

import logging

logger = logging.getLogger(__name__)


class DndToolsMixin:
    """Mixin providing D&D Game Master tool execution methods."""

    # Type hints for attributes provided by SignalToolExecutorBase
    bot_data: dict
    group_id: str

    # =========================================================================
    # D&D GAME MASTER TOOL HANDLERS
    # =========================================================================

    def _execute_start_dnd_campaign(self, arguments: dict) -> dict:
        """Start a new D&D campaign with a structured spreadsheet."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            if not self.bot_data.get('google_sheets_enabled') or not self.bot_data.get('google_connected'):
                return {"success": False, "message": "Google Sheets must be connected to use D&D campaign tools"}

            from signal_bot.google_sheets_client import (
                create_spreadsheet_sync, add_sheet_sync, write_sheet_sync,
                freeze_rows_sync, format_columns_sync, duplicate_spreadsheet_sync,
                _flask_app
            )
            from signal_bot.dnd_client import (
                get_campaign_sheet_headers, get_campaign_sheet_headers_v2,
                get_overview_initial_data, get_overview_initial_data_v2,
                CAMPAIGN_SIZES
            )
            from signal_bot.models import DndCampaignRegistry, db
            from datetime import datetime

            campaign_name = arguments.get("campaign_name", "Untitled Campaign")
            setting = arguments.get("setting", "Fantasy")
            tone = arguments.get("tone", "heroic")
            starting_level = arguments.get("starting_level", 1)
            campaign_size = arguments.get("campaign_size", "medium")
            custom_location_count = arguments.get("custom_location_count")
            # Use bot's configured template if none provided in arguments
            template_spreadsheet_id = arguments.get("template_spreadsheet_id") or self.bot_data.get("dnd_template_spreadsheet_id")

            # Calculate location count
            if campaign_size == "custom" and custom_location_count:
                location_count = min(max(custom_location_count, 3), 20)
            else:
                location_count = CAMPAIGN_SIZES.get(campaign_size, 6)

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Check for existing campaign with same name
            with _flask_app.app_context():
                existing = DndCampaignRegistry.find_campaign_by_name(
                    self.bot_data['id'], self.group_id, campaign_name
                )
            if existing:
                return {
                    "success": False,
                    "message": f"A campaign named '{campaign_name}' already exists. Choose a different name or continue the existing campaign."
                }

            title = f"[D&D] {campaign_name}"

            # Try template duplication first if template ID provided
            if template_spreadsheet_id:
                result = duplicate_spreadsheet_sync(
                    self.bot_data, self.group_id, template_spreadsheet_id, title,
                    description=f"D&D 5e Campaign: {campaign_name}",
                    created_by="D&D GM"
                )
                if result.get("success"):
                    spreadsheet_id = result["spreadsheet_id"]
                    # Update the Overview sheet with campaign-specific data
                    overview_data = get_overview_initial_data_v2(
                        campaign_name, setting, tone, starting_level,
                        campaign_size, location_count
                    )
                    write_sheet_sync(
                        self.bot_data, spreadsheet_id,
                        "'Overview'!A2",
                        overview_data
                    )
                else:
                    logger.warning(f"Template duplication failed, falling back to manual creation: {result.get('message')}")
                    template_spreadsheet_id = None  # Fall through to manual creation

            # Manual creation (no template or template failed)
            if not template_spreadsheet_id:
                result = create_spreadsheet_sync(
                    self.bot_data, self.group_id, title,
                    description=f"D&D 5e Campaign: {campaign_name}",
                    created_by="D&D GM"
                )

                if "error" in result:
                    return {"success": False, "message": f"Failed to create spreadsheet: {result['error']}"}

                spreadsheet_id = result["spreadsheet_id"]
                headers = get_campaign_sheet_headers_v2()

                # Add additional sheets (first sheet "Sheet1" already exists)
                sheet_names = ["Quick Reference", "Overview", "Characters", "NPCs", "Locations", "Items", "Combat Log", "Session History"]

                # Add sheets
                for sheet_name in sheet_names:
                    add_result = add_sheet_sync(self.bot_data, spreadsheet_id, sheet_name)
                    if not add_result.get("success"):
                        logger.warning(f"Failed to add sheet {sheet_name}: {add_result.get('message')}")

                # Write headers to each sheet
                for sheet_name in sheet_names:
                    if sheet_name in headers:
                        header_row = headers[sheet_name]
                        write_sheet_sync(
                            self.bot_data, spreadsheet_id,
                            f"'{sheet_name}'!A1",
                            [header_row]
                        )
                        # Freeze header row
                        freeze_rows_sync(self.bot_data, spreadsheet_id, 1, sheet_name)

                # Write initial overview data with new v2 format
                overview_data = get_overview_initial_data_v2(
                    campaign_name, setting, tone, starting_level,
                    campaign_size, location_count
                )
                write_sheet_sync(
                    self.bot_data, spreadsheet_id,
                    "'Overview'!A2",
                    overview_data
                )

            # Register the campaign (needs Flask app context for database)
            with _flask_app.app_context():
                campaign = DndCampaignRegistry(
                    bot_id=self.bot_data['id'],
                    group_id=self.group_id,
                    spreadsheet_id=spreadsheet_id,
                    campaign_name=campaign_name,
                    setting=setting,
                    tone=tone,
                    starting_level=starting_level,
                    is_active=True,
                    created_by="D&D GM",
                    created_at=datetime.utcnow(),
                    last_played=datetime.utcnow()
                )

                # Deactivate other campaigns for this group
                existing_campaigns = DndCampaignRegistry.get_campaigns_for_group(
                    self.bot_data['id'], self.group_id
                )
                for c in existing_campaigns:
                    c.is_active = False

                db.session.add(campaign)
                db.session.commit()

            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            size_text = f"{campaign_size} ({location_count} locations)" if campaign_size != "custom" else f"custom ({location_count} locations)"
            return {
                "success": True,
                "data": {
                    "campaign_name": campaign_name,
                    "spreadsheet_id": spreadsheet_id,
                    "url": url,
                    "setting": setting,
                    "tone": tone,
                    "starting_level": starting_level,
                    "campaign_size": campaign_size,
                    "location_count": location_count,
                    "campaign_phase": "world_building"
                },
                "message": f"Campaign '{campaign_name}' created! Spreadsheet: {url}\n\nThe campaign is set in {setting} with a {tone} tone. Characters will start at level {starting_level}. Campaign size: {size_text}.\n\n**Next Steps:**\n1. Generate locations for the world\n2. Roll dice to determine the route (start/end points)\n3. Populate each location with NPCs\n4. Create characters for the players\n5. Finalize starting equipment\n\nShall I generate the locations for your {setting} world?"
            }

        except Exception as e:
            logger.error(f"Error starting D&D campaign: {e}")
            return {"success": False, "message": f"Error starting campaign: {str(e)}"}

    def _execute_get_campaign_state(self, arguments: dict) -> dict:
        """Load the current state of a D&D campaign."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, _flask_app
            from signal_bot.dnd_client import row_to_character, CAMPAIGN_PHASES
            from signal_bot.models import DndCampaignRegistry, db
            from datetime import datetime
            import json

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            campaign_name = arguments.get("campaign_name")
            include_characters = arguments.get("include_characters", True)
            include_npcs = arguments.get("include_npcs", True)
            include_locations = arguments.get("include_locations", False)

            # Find the campaign (needs Flask app context)
            with _flask_app.app_context():
                if campaign_name:
                    campaign = DndCampaignRegistry.find_campaign_by_name(
                        self.bot_data['id'], self.group_id, campaign_name
                    )
                else:
                    campaign = DndCampaignRegistry.get_active_campaign(
                        self.bot_data['id'], self.group_id
                    )

                if not campaign:
                    campaigns = DndCampaignRegistry.get_campaigns_for_group(
                        self.bot_data['id'], self.group_id
                    )
                    if campaigns:
                        campaign_list = ", ".join([c.campaign_name for c in campaigns])
                        return {
                            "success": False,
                            "message": f"Campaign not found. Available campaigns: {campaign_list}"
                        }
                    return {"success": False, "message": "No D&D campaigns found for this group. Use start_dnd_campaign to create one."}

                # Copy data needed outside context
                spreadsheet_id = campaign.spreadsheet_id
                campaign_data = {
                    "campaign_name": campaign.campaign_name,
                    "setting": campaign.setting,
                    "tone": campaign.tone,
                }

            # Read Overview sheet
            overview_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]

            # Get campaign phase
            campaign_phase = overview.get("Campaign Phase", "in_progress")

            # During setup phases, always include locations for context
            if campaign_phase not in ["ready_to_play", "in_progress"]:
                include_locations = True

            state = {
                "campaign_name": campaign_data["campaign_name"],
                "setting": campaign_data["setting"],
                "tone": campaign_data["tone"],
                "campaign_phase": campaign_phase,
                "current_location": overview.get("Current Location", "Unknown"),
                "starting_location": overview.get("Starting Location", ""),
                "ending_location": overview.get("Ending Location", ""),
                "party_gold": overview.get("Party Gold", "0"),
                "story_flags": overview.get("Story Flags", ""),
                "session_count": overview.get("Session Count", "0"),
                "active_combat": overview.get("Active Combat", "No"),
                "combat_initiative": overview.get("Combat Initiative Order", ""),
                "total_locations": overview.get("Total Locations", "0"),
                "campaign_size": overview.get("Campaign Size", "medium"),
            }

            # Read Characters
            if include_characters:
                chars_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Characters'!A2:AF100")
                characters = []
                if chars_result.get("success") and chars_result.get("data", {}).get("values"):
                    for row in chars_result["data"]["values"]:
                        if row and row[0]:  # Has player name
                            char = row_to_character(row)
                            characters.append({
                                "player_name": char.get("player_name"),
                                "character_name": char.get("character_name"),
                                "race": char.get("race"),
                                "class": char.get("class"),
                                "level": char.get("level"),
                                "current_hp": char.get("current_hp"),
                                "max_hp": char.get("max_hp"),
                                "ac": char.get("ac"),
                                "conditions": char.get("conditions", []),
                                "player_number": char.get("player_number", 0),
                            })
                state["characters"] = characters

            # Read NPCs
            if include_npcs:
                npcs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'NPCs'!A2:K100")
                npcs = []
                if npcs_result.get("success") and npcs_result.get("data", {}).get("values"):
                    for row in npcs_result["data"]["values"]:
                        if row and row[0]:  # Has name
                            npcs.append({
                                "name": row[0] if len(row) > 0 else "",
                                "role": row[1] if len(row) > 1 else "",
                                "location": row[2] if len(row) > 2 else "",
                                "relationship": row[4] if len(row) > 4 else "unknown",
                                "npc_type": row[5] if len(row) > 5 else "",
                                "difficulty_tier": row[6] if len(row) > 6 else "",
                                "status": row[10] if len(row) > 10 else "alive",
                            })
                state["npcs"] = npcs

            # Read Locations
            if include_locations:
                locs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Locations'!A2:L100")
                locations = []
                if locs_result.get("success") and locs_result.get("data", {}).get("values"):
                    for row in locs_result["data"]["values"]:
                        if row and row[0]:  # Has name
                            locations.append({
                                "name": row[0] if len(row) > 0 else "",
                                "type": row[1] if len(row) > 1 else "",
                                "description": row[2] if len(row) > 2 else "",
                                "location_index": row[5] if len(row) > 5 else "",
                                "difficulty_tier": row[6] if len(row) > 6 else "",
                                "is_starting": row[7] if len(row) > 7 else "No",
                                "is_ending": row[8] if len(row) > 8 else "No",
                                "discovered": row[9] if len(row) > 9 else "Yes",
                            })
                state["locations"] = locations

            # Update last_played
            with _flask_app.app_context():
                campaign_obj = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if campaign_obj:
                    campaign_obj.last_played = datetime.utcnow()
                    db.session.commit()

            # Build summary message
            char_summary = ""
            if include_characters and state.get("characters"):
                char_lines = []
                for c in state["characters"]:
                    conditions = f" [{', '.join(c['conditions'])}]" if c.get("conditions") else ""
                    char_lines.append(f"  - {c['character_name']} ({c['race']} {c['class']} L{c['level']}): {c['current_hp']}/{c['max_hp']} HP, AC {c['ac']}{conditions}")
                char_summary = "\n**Characters:**\n" + "\n".join(char_lines)

            message = f"**Campaign: {campaign_data['campaign_name']}**\n"
            message += f"Setting: {campaign_data['setting']} | Tone: {campaign_data['tone']}\n"
            message += f"Phase: **{campaign_phase}**\n"

            # Add phase-specific guidance
            if campaign_phase not in ["ready_to_play", "in_progress"]:
                phase_guidance = {
                    "world_building": "Setup in progress. Next: Generate locations for the world.",
                    "location_creation": "Locations created. Next: Roll dice to assign the route (start/end points).",
                    "route_determination": "Route assigned. Next: Populate locations with NPCs.",
                    "npc_generation": "Populating NPCs. Continue with remaining locations.",
                    "character_creation": "Creating player characters. Guide each player through character creation.",
                    "item_setup": "Finalizing equipment. Add any special starting items.",
                }
                message += f"\n**⚠️ {phase_guidance.get(campaign_phase, 'Continue setup...')}**\n"
            else:
                message += f"Current Location: {state['current_location']}\n"
                message += f"Session #{state['session_count']} | Party Gold: {state['party_gold']} gp"
                if state['active_combat'] == "Yes":
                    message += "\n**COMBAT ACTIVE**"

            message += char_summary

            # Add location summary during setup
            if include_locations and state.get("locations"):
                loc_count = len(state["locations"])
                message += f"\n\n**Locations ({loc_count}):**"
                for loc in state["locations"][:5]:  # Show first 5
                    tier = f" [Tier {loc['difficulty_tier']}]" if loc.get('difficulty_tier') else ""
                    start = " ★START" if loc.get('is_starting') == "Yes" else ""
                    end = " ★END" if loc.get('is_ending') == "Yes" else ""
                    message += f"\n  - {loc['name']} ({loc['type']}){tier}{start}{end}"
                if loc_count > 5:
                    message += f"\n  ... and {loc_count - 5} more"

            return {
                "success": True,
                "data": state,
                "message": message
            }

        except Exception as e:
            logger.error(f"Error getting campaign state: {e}")
            return {"success": False, "message": f"Error loading campaign: {str(e)}"}

    def _execute_update_campaign_state(self, arguments: dict) -> dict:
        """Update the campaign state after significant events."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync, _flask_app
            from signal_bot.models import DndCampaignRegistry, db
            from datetime import datetime

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Get active campaign (needs Flask app context)
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign. Use start_dnd_campaign or get_campaign_state to load one."}
                spreadsheet_id = campaign.spreadsheet_id

            # Read current overview
            overview_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            overview_rows = []
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]
                    overview_rows.append(row)

            # Update fields
            current_location = arguments.get("current_location")
            session_summary = arguments.get("session_summary")
            story_flags = arguments.get("story_flags")
            next_session_hook = arguments.get("next_session_hook")

            updates = []
            if current_location:
                overview["Current Location"] = current_location
                updates.append(f"Location: {current_location}")
            if story_flags:
                existing_flags = overview.get("Story Flags", "")
                new_flags = ", ".join(story_flags)
                if existing_flags:
                    overview["Story Flags"] = existing_flags + ", " + new_flags
                else:
                    overview["Story Flags"] = new_flags
                updates.append(f"Story flags updated")

            # Rebuild overview data
            overview_data = [
                ["Campaign Name", overview.get("Campaign Name", campaign.campaign_name)],
                ["Setting", overview.get("Setting", campaign.setting or "Fantasy")],
                ["Tone", overview.get("Tone", campaign.tone or "heroic")],
                ["Starting Level", overview.get("Starting Level", str(campaign.starting_level))],
                ["Current Date (In-Game)", overview.get("Current Date (In-Game)", "Day 1")],
                ["Current Location", overview.get("Current Location", "TBD")],
                ["Party Gold", overview.get("Party Gold", "0")],
                ["Story Flags", overview.get("Story Flags", "")],
                ["Session Count", overview.get("Session Count", "0")],
                ["Last Played", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
                ["Active Combat", overview.get("Active Combat", "No")],
                ["Combat Initiative Order", overview.get("Combat Initiative Order", "")],
            ]

            write_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2", overview_data)

            # Add to session history if we have a summary
            if session_summary:
                session_num = int(overview.get("Session Count", "0")) + 1
                overview["Session Count"] = str(session_num)

                # Update session count in overview
                overview_data[8] = ["Session Count", str(session_num)]
                write_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2", overview_data)

                # Append to Session History
                from signal_bot.google_sheets_client import append_to_sheet_sync
                history_row = [
                    str(session_num),
                    datetime.utcnow().strftime("%Y-%m-%d"),
                    session_summary,
                    "",  # Key events
                    "",  # NPCs met
                    current_location or "",
                    "",  # XP earned
                    next_session_hook or ""
                ]
                append_to_sheet_sync(
                    self.bot_data, spreadsheet_id, history_row,
                    added_by="D&D GM", include_metadata=False,
                    sheet_name="Session History"
                )
                updates.append(f"Session {session_num} logged")

            campaign.last_played = datetime.utcnow()
            db.session.commit()

            return {
                "success": True,
                "data": {"updates": updates},
                "message": f"Campaign state updated: {', '.join(updates)}" if updates else "Campaign state checked (no changes)"
            }

        except Exception as e:
            logger.error(f"Error updating campaign state: {e}")
            return {"success": False, "message": f"Error updating campaign: {str(e)}"}

    def _execute_create_character(self, arguments: dict) -> dict:
        """Create a new player character."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import append_to_sheet_sync, _flask_app
            from signal_bot.dnd_client import (
                build_character_stats, character_to_row, get_spell_slots,
                format_modifier, CLASSES
            )
            from signal_bot.models import DndCampaignRegistry, db
            from datetime import datetime

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Get active campaign (needs Flask app context)
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign. Start a campaign first with start_dnd_campaign."}
                # Copy campaign data we need outside the context
                spreadsheet_id = campaign.spreadsheet_id
                starting_level = campaign.starting_level or 1

            player_name = arguments.get("player_name", "Unknown Player")
            character_name = arguments.get("character_name", "Unknown Character")
            race = arguments.get("race", "Human")
            character_class = arguments.get("character_class", "Fighter")
            background = arguments.get("background", "Soldier")
            ability_scores = arguments.get("ability_scores", {
                "strength": 10, "dexterity": 10, "constitution": 10,
                "intelligence": 10, "wisdom": 10, "charisma": 10
            })
            personality_traits = arguments.get("personality_traits", "")
            ideal = arguments.get("ideal", "")
            bond = arguments.get("bond", "")
            flaw = arguments.get("flaw", "")
            player_number = arguments.get("player_number", 1)

            # Build character stats
            level = starting_level
            stats = build_character_stats(race, character_class, background, ability_scores, level)

            # Add personality
            stats["personality_traits"] = personality_traits
            stats["ideal"] = ideal
            stats["bond"] = bond
            stats["flaw"] = flaw
            stats["player_name"] = player_name
            stats["character_name"] = character_name
            stats["player_number"] = player_number

            # Get spell slots if spellcaster
            spell_slots = get_spell_slots(character_class, level)
            stats["spell_slots"] = spell_slots
            stats["spells_known"] = []

            # Convert to row and append
            row = character_to_row(stats)
            result = append_to_sheet_sync(
                self.bot_data, spreadsheet_id, row,
                added_by=player_name, include_metadata=False,
                sheet_name="Characters"
            )

            if not result.get("success"):
                return {"success": False, "message": f"Failed to save character: {result.get('message')}"}

            # Build response message
            mods = stats["modifiers"]
            mod_str = f"STR {format_modifier(mods['strength'])} | DEX {format_modifier(mods['dexterity'])} | CON {format_modifier(mods['constitution'])} | INT {format_modifier(mods['intelligence'])} | WIS {format_modifier(mods['wisdom'])} | CHA {format_modifier(mods['charisma'])}"

            class_info = CLASSES.get(character_class, {})
            features = stats.get("class_features", [])
            features_str = ", ".join(features[:5]) if features else "None yet"

            message = f"**{character_name}** created for {player_name}!\n\n"
            message += f"**{race} {character_class}** (Level {level})\n"
            message += f"Background: {background}\n"
            message += f"HP: {stats['max_hp']} | AC: {stats['ac']} | Speed: {stats['speed']} ft\n"
            message += f"Hit Die: {stats['hit_die']} | Proficiency: +{stats['proficiency_bonus']}\n\n"
            message += f"**Abilities:** {mod_str}\n"
            message += f"**Skills:** {', '.join(stats['skill_proficiencies'])}\n"
            message += f"**Features:** {features_str}\n"
            message += f"**Equipment:** {', '.join(stats['equipment'][:5])}..."

            if spell_slots:
                slots_str = ", ".join([f"{k}: {v}" for k, v in spell_slots.items() if v > 0])
                if slots_str:
                    message += f"\n**Spell Slots:** {slots_str}"

            return {
                "success": True,
                "data": stats,
                "message": message
            }

        except Exception as e:
            logger.error(f"Error creating character: {e}")
            return {"success": False, "message": f"Error creating character: {str(e)}"}

    def _execute_update_character(self, arguments: dict) -> dict:
        """Update a character's stats."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync
            from signal_bot.dnd_client import row_to_character, character_to_row
            from signal_bot.models import DndCampaignRegistry
            import json

            campaign = DndCampaignRegistry.get_active_campaign(
                self.bot_data['id'], self.group_id
            )
            if not campaign:
                return {"success": False, "message": "No active campaign."}

            character_name = arguments.get("character_name")
            if not character_name:
                return {"success": False, "message": "Character name is required"}

            # Read all characters
            result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Characters'!A2:AE100")
            if not result.get("success"):
                return {"success": False, "message": "Failed to read characters"}

            rows = result.get("data", {}).get("values", [])
            found_row = None
            row_index = None

            for i, row in enumerate(rows):
                if len(row) > 1 and row[1].lower() == character_name.lower():
                    found_row = row
                    row_index = i + 2  # +2 because sheet is 1-indexed and row 1 is header
                    break

            if not found_row:
                return {"success": False, "message": f"Character '{character_name}' not found"}

            # Parse character
            char = row_to_character(found_row)
            updates = []

            # Apply updates
            if "current_hp" in arguments:
                char["current_hp"] = arguments["current_hp"]
                updates.append(f"HP: {arguments['current_hp']}")
            if "temp_hp" in arguments:
                char["temp_hp"] = arguments["temp_hp"]
                updates.append(f"Temp HP: {arguments['temp_hp']}")
            if "level" in arguments:
                char["level"] = arguments["level"]
                updates.append(f"Level: {arguments['level']}")
            if "xp" in arguments:
                char["xp"] = arguments["xp"]
                updates.append(f"XP: {arguments['xp']}")
            if "gold" in arguments:
                char["gold"] = arguments["gold"]
                updates.append(f"Gold: {arguments['gold']}")
            if "conditions" in arguments:
                char["conditions"] = arguments["conditions"]
                updates.append(f"Conditions: {', '.join(arguments['conditions']) or 'None'}")
            if "add_items" in arguments:
                char["equipment"].extend(arguments["add_items"])
                updates.append(f"Added items: {', '.join(arguments['add_items'])}")
            if "remove_items" in arguments:
                for item in arguments["remove_items"]:
                    if item in char["equipment"]:
                        char["equipment"].remove(item)
                updates.append(f"Removed items: {', '.join(arguments['remove_items'])}")
            if "spell_slots_used" in arguments:
                char["spell_slots"] = arguments["spell_slots_used"]
                updates.append("Spell slots updated")
            if "notes" in arguments:
                existing = char.get("notes", "")
                char["notes"] = existing + " | " + arguments["notes"] if existing else arguments["notes"]
                updates.append("Notes updated")

            # Write back
            new_row = character_to_row(char)
            write_result = write_sheet_sync(
                self.bot_data, campaign.spreadsheet_id,
                f"'Characters'!A{row_index}",
                [new_row]
            )

            if not write_result.get("success"):
                return {"success": False, "message": f"Failed to save updates: {write_result.get('message')}"}

            return {
                "success": True,
                "data": {"character_name": character_name, "updates": updates},
                "message": f"**{character_name}** updated: {', '.join(updates)}"
            }

        except Exception as e:
            logger.error(f"Error updating character: {e}")
            return {"success": False, "message": f"Error updating character: {str(e)}"}

    def _execute_start_combat(self, arguments: dict) -> dict:
        """Initialize a combat encounter."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync
            from signal_bot.dnd_client import row_to_character, calculate_modifier
            from signal_bot.dice_client import roll_dice
            from signal_bot.models import DndCampaignRegistry
            import json

            campaign = DndCampaignRegistry.get_active_campaign(
                self.bot_data['id'], self.group_id
            )
            if not campaign:
                return {"success": False, "message": "No active campaign."}

            encounter_name = arguments.get("encounter_name", "Combat")
            enemies = arguments.get("enemies", [])
            surprise = arguments.get("surprise", "none")

            if not enemies:
                return {"success": False, "message": "At least one enemy is required"}

            # Read player characters
            result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Characters'!A2:AE100")
            characters = []
            if result.get("success") and result.get("data", {}).get("values"):
                for row in result["data"]["values"]:
                    if row and row[0]:
                        char = row_to_character(row)
                        characters.append(char)

            # Roll initiative for everyone
            initiative_order = []

            # Player characters
            for char in characters:
                dex_mod = calculate_modifier(char["ability_scores"]["dexterity"])
                roll_result = roll_dice(f"1d20+{dex_mod}", f"{char['character_name']} initiative")
                initiative_order.append({
                    "name": char["character_name"],
                    "initiative": roll_result.get("total", 10),
                    "roll": roll_result.get("rolls", []),
                    "is_player": True,
                    "hp": char["current_hp"],
                    "max_hp": char["max_hp"],
                    "ac": char["ac"],
                    "surprised": surprise == "players"
                })

            # Enemies
            for enemy in enemies:
                init_mod = enemy.get("initiative_mod", 0)
                roll_result = roll_dice(f"1d20+{init_mod}", f"{enemy['name']} initiative")
                initiative_order.append({
                    "name": enemy["name"],
                    "initiative": roll_result.get("total", 10),
                    "roll": roll_result.get("rolls", []),
                    "is_player": False,
                    "hp": enemy.get("hp", 10),
                    "max_hp": enemy.get("hp", 10),
                    "ac": enemy.get("ac", 10),
                    "surprised": surprise == "enemies"
                })

            # Sort by initiative (highest first)
            initiative_order.sort(key=lambda x: x["initiative"], reverse=True)

            # Build combat state in new format
            from signal_bot.dnd_client import combat_state_to_json
            combat_state = {
                "round": 1,
                "current_turn_index": 0,
                "encounter_name": encounter_name,
                "combatants": initiative_order
            }

            # Update campaign state
            overview_result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]

            from datetime import datetime
            overview_data = [
                ["Campaign Name", overview.get("Campaign Name", campaign.campaign_name)],
                ["Setting", overview.get("Setting", campaign.setting or "Fantasy")],
                ["Tone", overview.get("Tone", campaign.tone or "heroic")],
                ["Starting Level", overview.get("Starting Level", str(campaign.starting_level))],
                ["Current Date (In-Game)", overview.get("Current Date (In-Game)", "Day 1")],
                ["Current Location", overview.get("Current Location", "TBD")],
                ["Party Gold", overview.get("Party Gold", "0")],
                ["Story Flags", overview.get("Story Flags", "")],
                ["Session Count", overview.get("Session Count", "0")],
                ["Last Played", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
                ["Active Combat", "Yes"],
                ["Combat Initiative Order", combat_state_to_json(combat_state)],
            ]
            write_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2", overview_data)

            # Build initiative display
            init_lines = []
            for i, combatant in enumerate(initiative_order):
                surprised = " (SURPRISED)" if combatant.get("surprised") else ""
                player_tag = " [PC]" if combatant["is_player"] else " [Enemy]"
                init_lines.append(f"{i+1}. **{combatant['name']}**{player_tag}: {combatant['initiative']}{surprised} (HP: {combatant['hp']}/{combatant['max_hp']}, AC: {combatant['ac']})")

            message = f"**COMBAT STARTED: {encounter_name}**\n\n"
            message += f"**Round 1 - Initiative Order:**\n" + "\n".join(init_lines)
            if surprise != "none":
                message += f"\n\n*{surprise.capitalize()} are surprised and cannot act in round 1!*"
            message += f"\n\n**{initiative_order[0]['name']}** is up first!"
            message += "\n\n*Use `complete_turn` after each combatant's action to track HP, advance initiative, and log the turn.*"

            return {
                "success": True,
                "data": {
                    "encounter_name": encounter_name,
                    "initiative_order": initiative_order,
                    "surprise": surprise,
                    "round": 1,
                    "current_turn_index": 0
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error starting combat: {e}")
            return {"success": False, "message": f"Error starting combat: {str(e)}"}

    def _execute_end_combat(self, arguments: dict) -> dict:
        """End a combat encounter."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync, append_to_sheet_sync
            from signal_bot.models import DndCampaignRegistry
            from datetime import datetime
            import json

            campaign = DndCampaignRegistry.get_active_campaign(
                self.bot_data['id'], self.group_id
            )
            if not campaign:
                return {"success": False, "message": "No active campaign."}

            outcome = arguments.get("outcome", "victory")
            xp_awarded = arguments.get("xp_awarded", 0)
            loot = arguments.get("loot", [])
            notes = arguments.get("notes", "")

            # Read current overview
            overview_result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]

            # Get encounter info before clearing (handle both old and new formats)
            from signal_bot.dnd_client import parse_combat_state

            initiative_data = overview.get("Combat Initiative Order", "")
            combat_state = parse_combat_state(initiative_data)

            if combat_state:
                initiative_order = combat_state.get("combatants", [])
                encounter_name = combat_state.get("encounter_name", "Combat Encounter")
            else:
                initiative_order = []
                encounter_name = "Combat Encounter"

            enemies = []
            for combatant in initiative_order:
                if not combatant.get("is_player"):
                    enemies.append(combatant["name"])
            # Only generate encounter name from enemies if we don't have one
            if enemies and encounter_name == "Combat Encounter":
                encounter_name = f"vs {', '.join(enemies[:3])}"

            # Clear combat state
            overview_data = [
                ["Campaign Name", overview.get("Campaign Name", campaign.campaign_name)],
                ["Setting", overview.get("Setting", campaign.setting or "Fantasy")],
                ["Tone", overview.get("Tone", campaign.tone or "heroic")],
                ["Starting Level", overview.get("Starting Level", str(campaign.starting_level))],
                ["Current Date (In-Game)", overview.get("Current Date (In-Game)", "Day 1")],
                ["Current Location", overview.get("Current Location", "TBD")],
                ["Party Gold", overview.get("Party Gold", "0")],
                ["Story Flags", overview.get("Story Flags", "")],
                ["Session Count", overview.get("Session Count", "0")],
                ["Last Played", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")],
                ["Active Combat", "No"],
                ["Combat Initiative Order", ""],
            ]
            write_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2", overview_data)

            # Log to Combat Log
            combat_log_row = [
                overview.get("Session Count", "1"),
                encounter_name,
                ", ".join(enemies),
                outcome,
                str(xp_awarded),
                ", ".join(loot),
                notes,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            ]
            append_to_sheet_sync(
                self.bot_data, campaign.spreadsheet_id, combat_log_row,
                added_by="D&D GM", include_metadata=False,
                sheet_name="Combat Log"
            )

            # Build message
            outcome_text = {
                "victory": "The party is victorious!",
                "defeat": "The party has fallen...",
                "fled": "The party escaped!",
                "negotiated": "Combat resolved through negotiation."
            }.get(outcome, outcome)

            message = f"**COMBAT ENDED**\n\n{outcome_text}\n"
            if xp_awarded > 0:
                message += f"\n**XP Awarded:** {xp_awarded}"
            if loot:
                message += f"\n**Loot:** {', '.join(loot)}"
            if notes:
                message += f"\n\n*{notes}*"

            return {
                "success": True,
                "data": {
                    "outcome": outcome,
                    "xp_awarded": xp_awarded,
                    "loot": loot
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error ending combat: {e}")
            return {"success": False, "message": f"Error ending combat: {str(e)}"}

    def _execute_add_npc(self, arguments: dict) -> dict:
        """Add a new NPC to the campaign."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, append_to_sheet_sync
            from signal_bot.models import DndCampaignRegistry

            campaign = DndCampaignRegistry.get_active_campaign(
                self.bot_data['id'], self.group_id
            )
            if not campaign:
                return {"success": False, "message": "No active campaign."}

            name = arguments.get("name", "Unknown NPC")
            role = arguments.get("role", "Unknown")
            location = arguments.get("location", "")
            description = arguments.get("description", "")
            relationship = arguments.get("relationship", "neutral")
            notes = arguments.get("notes", "")

            # Get current session number
            overview_result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2:B20")
            session_num = "1"
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2 and row[0] == "Session Count":
                        session_num = row[1]

            npc_row = [
                name,
                role,
                location,
                description,
                relationship,
                session_num,
                notes,
                "alive"
            ]

            result = append_to_sheet_sync(
                self.bot_data, campaign.spreadsheet_id, npc_row,
                added_by="D&D GM", include_metadata=False,
                sheet_name="NPCs"
            )

            if not result.get("success"):
                return {"success": False, "message": f"Failed to add NPC: {result.get('message')}"}

            message = f"**NPC Added: {name}**\n"
            message += f"Role: {role}\n"
            if location:
                message += f"Location: {location}\n"
            message += f"Relationship: {relationship}\n"
            if description:
                message += f"\n*{description}*"

            return {
                "success": True,
                "data": {"name": name, "role": role, "relationship": relationship},
                "message": message
            }

        except Exception as e:
            logger.error(f"Error adding NPC: {e}")
            return {"success": False, "message": f"Error adding NPC: {str(e)}"}

    def _execute_add_location(self, arguments: dict) -> dict:
        """Add a new location to the campaign."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, append_to_sheet_sync
            from signal_bot.models import DndCampaignRegistry

            campaign = DndCampaignRegistry.get_active_campaign(
                self.bot_data['id'], self.group_id
            )
            if not campaign:
                return {"success": False, "message": "No active campaign."}

            name = arguments.get("name", "Unknown Location")
            location_type = arguments.get("location_type", "Unknown")
            description = arguments.get("description", "")
            connected_to = arguments.get("connected_to", [])
            npcs_present = arguments.get("npcs_present", [])
            discovered = arguments.get("discovered", True)

            # Get current session number
            overview_result = read_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2:B20")
            session_num = "1"
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2 and row[0] == "Session Count":
                        session_num = row[1]

            location_row = [
                name,
                location_type,
                description,
                ", ".join(connected_to) if connected_to else "",
                ", ".join(npcs_present) if npcs_present else "",
                "Yes" if discovered else "No",
                session_num,
                ""  # Notes
            ]

            result = append_to_sheet_sync(
                self.bot_data, campaign.spreadsheet_id, location_row,
                added_by="D&D GM", include_metadata=False,
                sheet_name="Locations"
            )

            if not result.get("success"):
                return {"success": False, "message": f"Failed to add location: {result.get('message')}"}

            message = f"**Location Added: {name}** ({location_type})\n"
            if description:
                message += f"\n*{description}*\n"
            if connected_to:
                message += f"\nConnects to: {', '.join(connected_to)}"
            if npcs_present:
                message += f"\nNPCs: {', '.join(npcs_present)}"

            return {
                "success": True,
                "data": {"name": name, "type": location_type, "discovered": discovered},
                "message": message
            }

        except Exception as e:
            logger.error(f"Error adding location: {e}")
            return {"success": False, "message": f"Error adding location: {str(e)}"}

    def _execute_list_campaigns(self, arguments: dict) -> dict:
        """List all D&D campaigns for this group."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.models import DndCampaignRegistry

            campaigns = DndCampaignRegistry.get_campaigns_for_group(
                self.bot_data['id'], self.group_id
            )

            if not campaigns:
                return {
                    "success": True,
                    "data": {"campaigns": []},
                    "message": "No D&D campaigns found for this group. Use start_dnd_campaign to create one!"
                }

            campaign_list = []
            lines = []
            for c in campaigns:
                campaign_list.append({
                    "name": c.campaign_name,
                    "setting": c.setting,
                    "tone": c.tone,
                    "is_active": c.is_active,
                    "last_played": c.last_played.isoformat() if c.last_played else None
                })
                active_tag = " **(ACTIVE)**" if c.is_active else ""
                last_played = c.last_played.strftime("%Y-%m-%d") if c.last_played else "Never"
                lines.append(f"- **{c.campaign_name}**{active_tag}: {c.setting or 'Fantasy'}, {c.tone or 'heroic'} tone. Last played: {last_played}")

            message = "**D&D Campaigns:**\n\n" + "\n".join(lines)
            message += "\n\nTo continue a campaign, ask me to 'continue [campaign name]' or use get_campaign_state."

            return {
                "success": True,
                "data": {"campaigns": campaign_list},
                "message": message
            }

        except Exception as e:
            logger.error(f"Error listing campaigns: {e}")
            return {"success": False, "message": f"Error listing campaigns: {str(e)}"}

    # =========================================================================
    # NEW CAMPAIGN SETUP TOOL HANDLERS
    # =========================================================================

    def _execute_generate_locations(self, arguments: dict) -> dict:
        """Generate locations for a campaign based on setting and size."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.dnd_client import generate_location_list

            location_count = arguments.get("location_count", 6)
            setting = arguments.get("setting", "high fantasy")
            tone = arguments.get("tone", "heroic")
            preferences = arguments.get("preferences", "")

            # Generate locations
            locations = generate_location_list(location_count, setting, tone)

            # Build preview message
            location_lines = []
            for loc in locations:
                location_lines.append(f"  {loc['index']}. **{loc['name']}** ({loc['type']})")
                location_lines.append(f"     {loc['description']}")

            message = f"**Generated {len(locations)} locations for your campaign:**\n\n"
            message += "\n".join(location_lines)
            message += "\n\n*Review these locations. If you approve, I'll save them and we'll roll dice to determine your start and end points.*"

            return {
                "success": True,
                "data": {"locations": locations, "count": len(locations)},
                "message": message
            }

        except Exception as e:
            logger.error(f"Error generating locations: {e}")
            return {"success": False, "message": f"Error generating locations: {str(e)}"}

    def _execute_save_locations(self, arguments: dict) -> dict:
        """Save generated locations to the campaign spreadsheet."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import append_to_sheet_sync, write_sheet_sync, read_sheet_sync, _flask_app
            from signal_bot.dnd_client import location_to_row
            from signal_bot.models import DndCampaignRegistry

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            locations = arguments.get("locations", [])
            if not locations:
                return {"success": False, "message": "No locations provided to save"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign. Start a campaign first."}
                spreadsheet_id = campaign.spreadsheet_id

            # Save each location
            saved_count = 0
            for loc in locations:
                row = location_to_row(loc, "0")
                result = append_to_sheet_sync(
                    self.bot_data, spreadsheet_id, row,
                    added_by="D&D GM", include_metadata=False,
                    sheet_name="Locations"
                )
                if result.get("success"):
                    saved_count += 1

            # Update campaign phase
            self._update_overview_field(spreadsheet_id, "Campaign Phase", "location_creation")
            self._update_overview_field(spreadsheet_id, "Total Locations", str(len(locations)))

            return {
                "success": True,
                "data": {"saved_count": saved_count, "total": len(locations)},
                "message": f"Saved {saved_count} locations to campaign. Ready to roll for start/end points!"
            }

        except Exception as e:
            logger.error(f"Error saving locations: {e}")
            return {"success": False, "message": f"Error saving locations: {str(e)}"}

    def _execute_assign_route(self, arguments: dict) -> dict:
        """Determine start and end locations via dice rolls."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync, _flask_app
            from signal_bot.dnd_client import calculate_difficulty_tiers
            from signal_bot.dice_client import roll_dice
            from signal_bot.models import DndCampaignRegistry

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            # Read locations
            locs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Locations'!A2:L100")
            if not locs_result.get("success"):
                return {"success": False, "message": "Failed to read locations"}

            rows = locs_result.get("data", {}).get("values", [])
            if not rows:
                return {"success": False, "message": "No locations found. Generate locations first."}

            # Parse locations
            locations = []
            for row in rows:
                if row and row[0]:
                    locations.append({
                        "name": row[0],
                        "type": row[1] if len(row) > 1 else "",
                        "description": row[2] if len(row) > 2 else "",
                        "index": int(row[5]) if len(row) > 5 and row[5] else len(locations) + 1,
                        "difficulty_tier": 1,
                        "is_starting": False,
                        "is_ending": False,
                    })

            total_locations = len(locations)
            manual_start = arguments.get("manual_start")
            manual_end = arguments.get("manual_end")

            # Roll for starting location
            start_index = None
            start_name = None
            if manual_start:
                for loc in locations:
                    if loc["name"].lower() == manual_start.lower():
                        start_index = loc["index"]
                        start_name = loc["name"]
                        break

            if start_index is None:
                roll_result = roll_dice(f"1d{total_locations}", "Starting location roll")
                start_index = roll_result.get("total", 1)
                for loc in locations:
                    if loc["index"] == start_index:
                        start_name = loc["name"]
                        break

            # Roll for ending location
            end_index = None
            end_name = None
            if manual_end:
                for loc in locations:
                    if loc["name"].lower() == manual_end.lower():
                        end_index = loc["index"]
                        end_name = loc["name"]
                        break

            if end_index is None:
                # Keep rolling until we get something different from start
                attempts = 0
                while end_index is None or end_index == start_index:
                    roll_result = roll_dice(f"1d{total_locations}", "Ending location roll")
                    end_index = roll_result.get("total", total_locations)
                    attempts += 1
                    if attempts > 10:  # Safety valve
                        end_index = (start_index % total_locations) + 1
                        break
                for loc in locations:
                    if loc["index"] == end_index:
                        end_name = loc["name"]
                        break

            # Calculate difficulty tiers
            locations = calculate_difficulty_tiers(locations, start_index, end_index)

            # Update locations in spreadsheet
            for i, loc in enumerate(locations):
                row_num = i + 2  # +2 for header and 1-indexing
                # Update Difficulty Tier, Is Starting, Is Ending columns (G, H, I)
                update_range = f"'Locations'!G{row_num}:I{row_num}"
                write_sheet_sync(
                    self.bot_data, spreadsheet_id, update_range,
                    [[str(loc["difficulty_tier"]), "Yes" if loc["is_starting"] else "No", "Yes" if loc["is_ending"] else "No"]]
                )

            # Update Overview
            self._update_overview_field(spreadsheet_id, "Starting Location", start_name)
            self._update_overview_field(spreadsheet_id, "Ending Location", end_name)
            self._update_overview_field(spreadsheet_id, "Campaign Phase", "npc_generation")

            # Build message
            tier_summary = []
            for tier in range(1, 6):
                tier_locs = [loc["name"] for loc in locations if loc["difficulty_tier"] == tier]
                if tier_locs:
                    tier_summary.append(f"Tier {tier}: {', '.join(tier_locs)}")

            message = f"**Route Determined!**\n\n"
            message += f"**Starting Point:** {start_name} (rolled {start_index})\n"
            message += f"**Final Destination:** {end_name} (rolled {end_index})\n\n"
            message += "**Difficulty Scaling:**\n" + "\n".join(tier_summary)
            message += f"\n\n*The starting location has easier enemies (Tier 1), while the final location has the toughest challenges (Tier 5).*"
            message += "\n\n*Ready to populate each location with NPCs!*"

            return {
                "success": True,
                "data": {
                    "start_location": start_name,
                    "end_location": end_name,
                    "start_index": start_index,
                    "end_index": end_index,
                    "locations": locations
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error assigning route: {e}")
            return {"success": False, "message": f"Error assigning route: {str(e)}"}

    def _execute_generate_npcs_for_location(self, arguments: dict) -> dict:
        """Auto-generate NPCs for a specific location."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, append_to_sheet_sync, _flask_app
            from signal_bot.dnd_client import generate_npcs_for_location, npc_to_row
            from signal_bot.models import DndCampaignRegistry

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            location_name = arguments.get("location_name")
            if not location_name:
                return {"success": False, "message": "Location name is required"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            # Find the location
            locs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Locations'!A2:L100")
            if not locs_result.get("success"):
                return {"success": False, "message": "Failed to read locations"}

            location = None
            for row in locs_result.get("data", {}).get("values", []):
                if row and row[0].lower() == location_name.lower():
                    location = {
                        "name": row[0],
                        "type": row[1] if len(row) > 1 else "default",
                        "description": row[2] if len(row) > 2 else "",
                        "difficulty_tier": int(row[6]) if len(row) > 6 and row[6] else 1,
                    }
                    break

            if not location:
                return {"success": False, "message": f"Location '{location_name}' not found"}

            # Generate NPCs
            npcs = generate_npcs_for_location(location, location["difficulty_tier"])

            # Save NPCs
            saved_count = 0
            for npc in npcs:
                row = npc_to_row(npc, "0")
                result = append_to_sheet_sync(
                    self.bot_data, spreadsheet_id, row,
                    added_by="D&D GM", include_metadata=False,
                    sheet_name="NPCs"
                )
                if result.get("success"):
                    saved_count += 1

            # Build message
            npc_by_type = {"friendly": [], "neutral": [], "hostile": [], "quest_giver": [], "boss": [], "general": []}
            for npc in npcs:
                rel = npc.get("relationship", "neutral")
                if rel in npc_by_type:
                    combat_info = ""
                    if npc.get("combat_stats"):
                        stats = npc["combat_stats"]
                        combat_info = f" (HP: {stats['hp']}, AC: {stats['ac']}, +{stats['attack_bonus']} to hit)"
                    npc_by_type[rel].append(f"{npc['name']} - {npc['role']}{combat_info}")
                else:
                    npc_by_type["neutral"].append(f"{npc['name']} - {npc['role']}")

            message = f"**NPCs Generated for {location_name}:**\n\n"
            if npc_by_type["friendly"]:
                message += "**Friendly:**\n" + "\n".join([f"  - {n}" for n in npc_by_type["friendly"]]) + "\n\n"
            if npc_by_type["quest_giver"]:
                message += "**Quest Givers:**\n" + "\n".join([f"  - {n}" for n in npc_by_type["quest_giver"]]) + "\n\n"
            if npc_by_type["neutral"]:
                message += "**Neutral:**\n" + "\n".join([f"  - {n}" for n in npc_by_type["neutral"]]) + "\n\n"
            if npc_by_type["hostile"]:
                message += "**Hostile (Combat Stats):**\n" + "\n".join([f"  - {n}" for n in npc_by_type["hostile"]]) + "\n\n"
            if npc_by_type["boss"]:
                message += "**Boss:**\n" + "\n".join([f"  - {n}" for n in npc_by_type["boss"]]) + "\n\n"
            if npc_by_type["general"]:
                message += "**Background:**\n" + "\n".join([f"  - {n}" for n in npc_by_type["general"]]) + "\n"

            message += f"\n*{saved_count} NPCs saved to campaign.*"

            return {
                "success": True,
                "data": {"npcs": npcs, "saved_count": saved_count, "location": location_name},
                "message": message
            }

        except Exception as e:
            logger.error(f"Error generating NPCs: {e}")
            return {"success": False, "message": f"Error generating NPCs: {str(e)}"}

    def _execute_finalize_starting_items(self, arguments: dict) -> dict:
        """Confirm starting equipment and add special items."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import read_sheet_sync, append_to_sheet_sync, _flask_app
            from signal_bot.models import DndCampaignRegistry

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            special_items = arguments.get("special_items", [])
            confirm_ready = arguments.get("confirm_ready", False)

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            # Read characters to get their equipment
            chars_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Characters'!A2:AE100")
            characters = []
            if chars_result.get("success") and chars_result.get("data", {}).get("values"):
                for row in chars_result["data"]["values"]:
                    if row and row[0]:
                        import json
                        try:
                            equipment = json.loads(row[21]) if len(row) > 21 and row[21] else []
                        except:
                            equipment = []
                        characters.append({
                            "player_name": row[0],
                            "character_name": row[1] if len(row) > 1 else "",
                            "equipment": equipment
                        })

            # Add character equipment to Items sheet if not already there
            items_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Items'!A2:G100")
            existing_items = set()
            if items_result.get("success") and items_result.get("data", {}).get("values"):
                for row in items_result["data"]["values"]:
                    if row and row[0]:
                        owner = row[3] if len(row) > 3 else ""
                        existing_items.add(f"{row[0]}|{owner}")

            items_added = 0
            for char in characters:
                for item in char.get("equipment", []):
                    item_key = f"{item}|{char['character_name']}"
                    if item_key not in existing_items:
                        item_row = [
                            item,  # Name
                            "Equipment",  # Type
                            "",  # Description
                            char["character_name"],  # Owner
                            "Yes",  # Is Starting Gear
                            "0",  # Acquired (Session)
                            ""  # Notes
                        ]
                        append_to_sheet_sync(
                            self.bot_data, spreadsheet_id, item_row,
                            added_by="D&D GM", include_metadata=False,
                            sheet_name="Items"
                        )
                        items_added += 1

            # Add special items
            special_added = 0
            for item in special_items:
                item_row = [
                    item.get("name", "Unknown Item"),
                    item.get("type", "Special"),
                    item.get("description", ""),
                    item.get("owner", "Party"),
                    "Yes",
                    "0",
                    "Special starting item"
                ]
                append_to_sheet_sync(
                    self.bot_data, spreadsheet_id, item_row,
                    added_by="D&D GM", include_metadata=False,
                    sheet_name="Items"
                )
                special_added += 1

            # Update phase if confirmed ready
            if confirm_ready:
                self._update_overview_field(spreadsheet_id, "Campaign Phase", "ready_to_play")

            message = f"**Starting Items Finalized!**\n\n"
            message += f"- Added {items_added} equipment items from characters\n"
            if special_added > 0:
                message += f"- Added {special_added} special items\n"
            message += f"\n**Party Members:**\n"
            for char in characters:
                message += f"  - {char['character_name']} ({char['player_name']})\n"

            if confirm_ready:
                message += "\n**Campaign setup complete! Ready to begin the adventure!**"
            else:
                message += "\n*Add any special items or confirm ready to begin.*"

            return {
                "success": True,
                "data": {
                    "items_added": items_added,
                    "special_added": special_added,
                    "ready": confirm_ready
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error finalizing items: {e}")
            return {"success": False, "message": f"Error finalizing items: {str(e)}"}

    def _execute_update_campaign_phase(self, arguments: dict) -> dict:
        """Update the campaign's current phase."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import _flask_app
            from signal_bot.models import DndCampaignRegistry
            from signal_bot.dnd_client import CAMPAIGN_PHASES

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            phase = arguments.get("phase")
            if not phase or phase not in CAMPAIGN_PHASES:
                return {"success": False, "message": f"Invalid phase. Must be one of: {', '.join(CAMPAIGN_PHASES)}"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            # Update phase
            self._update_overview_field(spreadsheet_id, "Campaign Phase", phase)

            phase_messages = {
                "world_building": "Setting up campaign world...",
                "location_creation": "Creating locations for the campaign...",
                "route_determination": "Determining adventure route...",
                "npc_generation": "Populating locations with NPCs...",
                "character_creation": "Creating player characters...",
                "item_setup": "Finalizing starting equipment...",
                "ready_to_play": "Campaign setup complete! Ready to begin!",
                "in_progress": "Adventure in progress!",
            }

            return {
                "success": True,
                "data": {"phase": phase},
                "message": f"Campaign phase updated to: **{phase}**\n{phase_messages.get(phase, '')}"
            }

        except Exception as e:
            logger.error(f"Error updating phase: {e}")
            return {"success": False, "message": f"Error updating phase: {str(e)}"}

    def _update_overview_field(self, spreadsheet_id: str, field: str, value: str) -> bool:
        """Helper to update a single field in the Overview sheet."""
        try:
            from signal_bot.google_sheets_client import read_sheet_sync, write_sheet_sync

            # Read current overview
            result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2:B20")
            if not result.get("success"):
                return False

            rows = result.get("data", {}).get("values", [])
            row_index = None
            for i, row in enumerate(rows):
                if row and row[0] == field:
                    row_index = i + 2  # +2 for header and 1-indexing
                    break

            if row_index:
                write_sheet_sync(
                    self.bot_data, spreadsheet_id,
                    f"'Overview'!B{row_index}",
                    [[value]]
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating overview field: {e}")
            return False

    # =========================================================================
    # TURN & EVENT LOGGING TOOL HANDLERS
    # =========================================================================

    def _execute_complete_turn(self, arguments: dict) -> dict:
        """Complete a combat turn with HP updates, conditions, and initiative advancement."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import (
                read_sheet_sync, write_sheet_sync, append_to_sheet_sync, _flask_app
            )
            from signal_bot.dnd_client import (
                parse_combat_state, combat_state_to_json, event_to_row,
                row_to_character, character_to_row
            )
            from signal_bot.models import DndCampaignRegistry
            from datetime import datetime
            import json

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            # Read Overview to get combat state
            overview_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]

            # Check if combat is active
            if overview.get("Active Combat") != "Yes":
                return {"success": False, "message": "No active combat. Use start_combat first."}

            # Parse combat state (handles both old and new formats)
            combat_data = overview.get("Combat Initiative Order", "")
            combat_state = parse_combat_state(combat_data)
            if not combat_state:
                return {"success": False, "message": "Invalid combat state. Start a new combat encounter."}

            combatants = combat_state.get("combatants", [])
            current_round = combat_state.get("round", 1)
            current_turn_index = combat_state.get("current_turn_index", 0)

            if not combatants:
                return {"success": False, "message": "No combatants in combat."}

            # Get current combatant
            current_combatant = combatants[current_turn_index]
            action_summary = arguments.get("action_summary", "Action taken")
            combatant_updates = arguments.get("combatant_updates", [])
            damage_dealt = arguments.get("damage_dealt", 0)
            healing_done = arguments.get("healing_done", 0)
            spell_slots_used = arguments.get("spell_slots_used", {})
            advance_turn = arguments.get("advance_turn", True)

            # Apply combatant updates
            player_characters_updated = []
            for update in combatant_updates:
                target_name = update.get("name")
                if not target_name:
                    continue

                # Find the combatant
                for combatant in combatants:
                    if combatant["name"].lower() == target_name.lower():
                        # Apply HP change
                        if "hp_change" in update:
                            new_hp = combatant.get("hp", 0) + update["hp_change"]
                            new_hp = max(0, min(new_hp, combatant.get("max_hp", new_hp)))
                            combatant["hp"] = new_hp

                        # Add conditions
                        if "conditions_add" in update:
                            conditions = combatant.get("conditions", [])
                            for cond in update["conditions_add"]:
                                if cond not in conditions:
                                    conditions.append(cond)
                            combatant["conditions"] = conditions

                        # Remove conditions
                        if "conditions_remove" in update:
                            conditions = combatant.get("conditions", [])
                            for cond in update["conditions_remove"]:
                                if cond in conditions:
                                    conditions.remove(cond)
                            combatant["conditions"] = conditions

                        # Mark as dead
                        if update.get("is_dead") or combatant.get("hp", 0) <= 0:
                            combatant["is_dead"] = True

                        # Track player character updates for syncing
                        if combatant.get("is_player"):
                            player_characters_updated.append(combatant)

                        break

            # Handle spell slots for current combatant (if player)
            if spell_slots_used and current_combatant.get("is_player"):
                player_characters_updated.append({
                    "name": current_combatant["name"],
                    "spell_slots_used": spell_slots_used
                })

            # Advance turn
            next_combatant = None
            new_round = current_round
            new_turn_index = current_turn_index

            if advance_turn:
                # Find next living combatant
                attempts = 0
                while attempts < len(combatants):
                    new_turn_index = (new_turn_index + 1) % len(combatants)
                    if new_turn_index == 0:
                        new_round += 1  # New round when we wrap around

                    candidate = combatants[new_turn_index]
                    if not candidate.get("is_dead") and candidate.get("hp", 0) > 0:
                        next_combatant = candidate
                        break
                    attempts += 1

                if not next_combatant:
                    # No living combatants (shouldn't happen normally)
                    next_combatant = combatants[0]

            # Check if combat is over (all enemies dead)
            enemies_alive = [c for c in combatants if not c.get("is_player") and not c.get("is_dead") and c.get("hp", 0) > 0]
            players_alive = [c for c in combatants if c.get("is_player") and not c.get("is_dead") and c.get("hp", 0) > 0]

            combat_over = False
            combat_outcome = None
            if not enemies_alive:
                combat_over = True
                combat_outcome = "victory"
            elif not players_alive:
                combat_over = True
                combat_outcome = "defeat"

            # Update combat state
            combat_state["round"] = new_round
            combat_state["current_turn_index"] = new_turn_index
            combat_state["combatants"] = combatants

            # Write updated combat state to Overview
            self._update_overview_field(spreadsheet_id, "Combat Initiative Order", combat_state_to_json(combat_state))
            self._update_overview_field(spreadsheet_id, "Last Played", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

            # Log to Event Log
            session_num = overview.get("Session Count", "1")
            current_location = overview.get("Current Location", "")

            event_row = event_to_row(
                session_num=session_num,
                event_type="combat",
                actor=current_combatant["name"],
                summary=action_summary,
                location=current_location,
                damage=damage_dealt,
                healing=healing_done,
                outcome="",
                round_num=current_round
            )
            append_to_sheet_sync(
                self.bot_data, spreadsheet_id, event_row,
                added_by="D&D GM", include_metadata=False,
                sheet_name="Event Log"
            )

            # Sync player character HP to Characters sheet
            if player_characters_updated:
                chars_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Characters'!A2:AF100")
                if chars_result.get("success") and chars_result.get("data", {}).get("values"):
                    rows = chars_result["data"]["values"]
                    for pc_update in player_characters_updated:
                        for i, row in enumerate(rows):
                            if len(row) > 1 and row[1].lower() == pc_update["name"].lower():
                                char = row_to_character(row)

                                # Update HP
                                if "hp" in pc_update:
                                    char["current_hp"] = pc_update["hp"]
                                else:
                                    # Find HP from combatant data
                                    for c in combatants:
                                        if c["name"].lower() == pc_update["name"].lower():
                                            char["current_hp"] = c.get("hp", char["current_hp"])
                                            char["conditions"] = c.get("conditions", [])
                                            break

                                # Update spell slots if provided
                                if "spell_slots_used" in pc_update:
                                    current_slots = char.get("spell_slots", {})
                                    for level, used in pc_update["spell_slots_used"].items():
                                        if level in current_slots:
                                            current_slots[level] = max(0, current_slots[level] - used)
                                    char["spell_slots"] = current_slots

                                # Write back
                                new_row = character_to_row(char)
                                row_num = i + 2
                                write_sheet_sync(
                                    self.bot_data, spreadsheet_id,
                                    f"'Characters'!A{row_num}",
                                    [new_row]
                                )
                                break

            # If combat is over, auto-end it
            if combat_over:
                # Calculate XP (simplified - 50 XP per enemy)
                enemy_count = len([c for c in combatants if not c.get("is_player")])
                xp_awarded = enemy_count * 50

                # Call end_combat internally
                end_result = self._execute_end_combat({
                    "outcome": combat_outcome,
                    "xp_awarded": xp_awarded,
                    "notes": f"Combat ended after {current_round} rounds"
                })

                return {
                    "success": True,
                    "data": {
                        "turn_completed": True,
                        "combat_over": True,
                        "outcome": combat_outcome,
                        "round": current_round,
                        "actor": current_combatant["name"]
                    },
                    "message": f"**Turn Complete:** {current_combatant['name']} - {action_summary}\n\n**COMBAT ENDED - {combat_outcome.upper()}!**\n{end_result.get('message', '')}"
                }

            # Build response message
            message = f"**Turn Complete (Round {current_round}):** {current_combatant['name']}\n"
            message += f"{action_summary}\n\n"

            if damage_dealt:
                message += f"Damage dealt: {damage_dealt}\n"
            if healing_done:
                message += f"Healing done: {healing_done}\n"

            # Show updated combatant status
            message += "\n**Combatant Status:**\n"
            for i, c in enumerate(combatants):
                status = "DEAD" if c.get("is_dead") or c.get("hp", 0) <= 0 else f"{c.get('hp', 0)}/{c.get('max_hp', 0)} HP"
                conditions = f" [{', '.join(c.get('conditions', []))}]" if c.get('conditions') else ""
                turn_marker = " ← UP NEXT" if advance_turn and i == new_turn_index else ""
                player_tag = "[PC]" if c.get("is_player") else "[Enemy]"
                message += f"  {c['name']} {player_tag}: {status}{conditions}{turn_marker}\n"

            if next_combatant:
                message += f"\n**{next_combatant['name']}** is up!"

            return {
                "success": True,
                "data": {
                    "turn_completed": True,
                    "combat_over": False,
                    "round": new_round,
                    "actor": current_combatant["name"],
                    "next_combatant": next_combatant["name"] if next_combatant else None
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error completing turn: {e}")
            return {"success": False, "message": f"Error completing turn: {str(e)}"}

    def _execute_log_event(self, arguments: dict) -> dict:
        """Log an exploration or story event."""
        try:
            if not self.bot_data.get('dnd_enabled'):
                return {"success": False, "message": "D&D tools are not enabled for this bot"}

            from signal_bot.google_sheets_client import (
                read_sheet_sync, append_to_sheet_sync, _flask_app
            )
            from signal_bot.dnd_client import event_to_row
            from signal_bot.models import DndCampaignRegistry
            from datetime import datetime

            if not _flask_app:
                return {"success": False, "message": "Flask app not initialized for database access"}

            # Get active campaign
            with _flask_app.app_context():
                campaign = DndCampaignRegistry.get_active_campaign(
                    self.bot_data['id'], self.group_id
                )
                if not campaign:
                    return {"success": False, "message": "No active campaign."}
                spreadsheet_id = campaign.spreadsheet_id

            event_type = arguments.get("event_type", "story")
            summary = arguments.get("summary", "")
            location = arguments.get("location", "")
            npcs_involved = arguments.get("npcs_involved", [])
            outcome = arguments.get("outcome", "")
            characters_involved = arguments.get("characters_involved", [])

            if not summary:
                return {"success": False, "message": "Event summary is required"}

            # Read Overview to get session number and current location
            overview_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Overview'!A2:B20")
            overview = {}
            if overview_result.get("success") and overview_result.get("data", {}).get("values"):
                for row in overview_result["data"]["values"]:
                    if len(row) >= 2:
                        overview[row[0]] = row[1]

            session_num = overview.get("Session Count", "1")
            current_location = location or overview.get("Current Location", "")

            # Update Current Location if this is a travel event
            if event_type == "travel" and location:
                self._update_overview_field(spreadsheet_id, "Current Location", location)
                self._update_overview_field(spreadsheet_id, "Last Played", datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

            # Build actor string from characters involved
            actor = ", ".join(characters_involved) if characters_involved else "Party"

            # Log to Event Log
            event_row = event_to_row(
                session_num=session_num,
                event_type=event_type,
                actor=actor,
                summary=summary,
                location=current_location,
                npcs_involved=npcs_involved,
                outcome=outcome
            )
            append_to_sheet_sync(
                self.bot_data, spreadsheet_id, event_row,
                added_by="D&D GM", include_metadata=False,
                sheet_name="Event Log"
            )

            # Build response message
            event_icons = {
                "travel": "🚶",
                "conversation": "💬",
                "skill_check": "🎲",
                "story": "📜",
                "rest": "🏕️"
            }
            icon = event_icons.get(event_type, "📝")

            message = f"{icon} **Event Logged:** {event_type.replace('_', ' ').title()}\n"
            message += f"{summary}\n"

            if event_type == "travel" and location:
                message += f"\n*Party location updated to: {location}*"
            if npcs_involved:
                message += f"\nNPCs: {', '.join(npcs_involved)}"
            if outcome:
                message += f"\nOutcome: {outcome}"

            return {
                "success": True,
                "data": {
                    "event_type": event_type,
                    "summary": summary,
                    "location": current_location
                },
                "message": message
            }

        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return {"success": False, "message": f"Error logging event: {str(e)}"}

