"""
D&D Game Master tool executor mixin for Signal bots.

Contains D&D campaign management tool methods.
"""

import logging

logger = logging.getLogger(__name__)


class DndToolsMixin:
    """Mixin providing D&D Game Master tool execution methods."""

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
                freeze_rows_sync, format_columns_sync
            )
            from signal_bot.dnd_client import (
                get_campaign_sheet_headers, get_overview_initial_data
            )
            from signal_bot.models import DndCampaignRegistry, db
            from datetime import datetime

            campaign_name = arguments.get("campaign_name", "Untitled Campaign")
            setting = arguments.get("setting", "Fantasy")
            tone = arguments.get("tone", "heroic")
            starting_level = arguments.get("starting_level", 1)

            # Import Flask app for database context
            from signal_bot.google_sheets_client import _flask_app
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

            # Create the spreadsheet
            title = f"[D&D] {campaign_name}"
            result = create_spreadsheet_sync(
                self.bot_data, self.group_id, title,
                description=f"D&D 5e Campaign: {campaign_name}",
                created_by="D&D GM"
            )

            if "error" in result:
                return {"success": False, "message": f"Failed to create spreadsheet: {result['error']}"}

            spreadsheet_id = result["spreadsheet_id"]
            headers = get_campaign_sheet_headers()

            # Add additional sheets (first sheet "Sheet1" already exists)
            sheet_names = ["Overview", "Characters", "NPCs", "Locations", "Items", "Combat Log", "Session History"]

            # Rename Sheet1 to Overview and add others
            for i, sheet_name in enumerate(sheet_names[1:], start=1):  # Skip Overview, it's created first
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

            # Write initial overview data
            overview_data = get_overview_initial_data(campaign_name, setting, tone, starting_level)
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
            return {
                "success": True,
                "data": {
                    "campaign_name": campaign_name,
                    "spreadsheet_id": spreadsheet_id,
                    "url": url,
                    "setting": setting,
                    "tone": tone,
                    "starting_level": starting_level
                },
                "message": f"Campaign '{campaign_name}' created! Spreadsheet: {url}\n\nThe campaign is set in {setting} with a {tone} tone. Characters will start at level {starting_level}.\n\nNext: Guide the players through world-building and character creation!"
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
            from signal_bot.dnd_client import row_to_character
            from signal_bot.models import DndCampaignRegistry
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

            state = {
                "campaign_name": campaign_data["campaign_name"],
                "setting": campaign_data["setting"],
                "tone": campaign_data["tone"],
                "current_location": overview.get("Current Location", "Unknown"),
                "party_gold": overview.get("Party Gold", "0"),
                "story_flags": overview.get("Story Flags", ""),
                "session_count": overview.get("Session Count", "0"),
                "active_combat": overview.get("Active Combat", "No"),
                "combat_initiative": overview.get("Combat Initiative Order", ""),
            }

            # Read Characters
            if include_characters:
                chars_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Characters'!A2:AE100")
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
                            })
                state["characters"] = characters

            # Read NPCs
            if include_npcs:
                npcs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'NPCs'!A2:H100")
                npcs = []
                if npcs_result.get("success") and npcs_result.get("data", {}).get("values"):
                    for row in npcs_result["data"]["values"]:
                        if row and row[0]:  # Has name
                            npcs.append({
                                "name": row[0] if len(row) > 0 else "",
                                "role": row[1] if len(row) > 1 else "",
                                "location": row[2] if len(row) > 2 else "",
                                "relationship": row[4] if len(row) > 4 else "unknown",
                            })
                state["npcs"] = npcs

            # Read Locations
            if include_locations:
                locs_result = read_sheet_sync(self.bot_data, spreadsheet_id, "'Locations'!A2:H100")
                locations = []
                if locs_result.get("success") and locs_result.get("data", {}).get("values"):
                    for row in locs_result["data"]["values"]:
                        if row and row[0]:  # Has name
                            locations.append({
                                "name": row[0] if len(row) > 0 else "",
                                "type": row[1] if len(row) > 1 else "",
                                "discovered": row[5] if len(row) > 5 else "Yes",
                            })
                state["locations"] = locations

            # Update last_played
            campaign.last_played = datetime.utcnow()
            from signal_bot.models import db
            db.session.commit()

            # Build summary message
            char_summary = ""
            if include_characters and state.get("characters"):
                char_lines = []
                for c in state["characters"]:
                    conditions = f" [{', '.join(c['conditions'])}]" if c.get("conditions") else ""
                    char_lines.append(f"  - {c['character_name']} ({c['race']} {c['class']} L{c['level']}): {c['current_hp']}/{c['max_hp']} HP, AC {c['ac']}{conditions}")
                char_summary = "\n**Characters:**\n" + "\n".join(char_lines)

            message = f"**Campaign: {campaign.campaign_name}**\n"
            message += f"Setting: {campaign.setting} | Tone: {campaign.tone}\n"
            message += f"Current Location: {state['current_location']}\n"
            message += f"Session #{state['session_count']} | Party Gold: {state['party_gold']} gp"
            if state['active_combat'] == "Yes":
                message += "\n**COMBAT ACTIVE**"
            message += char_summary

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
                    added_by="D&D GM", include_metadata=False
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

            # Get spell slots if spellcaster
            spell_slots = get_spell_slots(character_class, level)
            stats["spell_slots"] = spell_slots
            stats["spells_known"] = []

            # Convert to row and append
            row = character_to_row(stats)
            result = append_to_sheet_sync(
                self.bot_data, spreadsheet_id, row,
                added_by=player_name, include_metadata=False
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
                ["Combat Initiative Order", json.dumps(initiative_order)],
            ]
            write_sheet_sync(self.bot_data, campaign.spreadsheet_id, "'Overview'!A2", overview_data)

            # Build initiative display
            init_lines = []
            for i, combatant in enumerate(initiative_order):
                surprised = " (SURPRISED)" if combatant.get("surprised") else ""
                player_tag = " [PC]" if combatant["is_player"] else " [Enemy]"
                init_lines.append(f"{i+1}. **{combatant['name']}**{player_tag}: {combatant['initiative']}{surprised} (HP: {combatant['hp']}/{combatant['max_hp']}, AC: {combatant['ac']})")

            message = f"**COMBAT STARTED: {encounter_name}**\n\n"
            message += "**Initiative Order:**\n" + "\n".join(init_lines)
            if surprise != "none":
                message += f"\n\n*{surprise.capitalize()} are surprised and cannot act in round 1!*"
            message += f"\n\n**{initiative_order[0]['name']}** is up first!"

            return {
                "success": True,
                "data": {
                    "encounter_name": encounter_name,
                    "initiative_order": initiative_order,
                    "surprise": surprise
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

            # Get encounter info before clearing
            initiative_data = overview.get("Combat Initiative Order", "[]")
            try:
                initiative_order = json.loads(initiative_data)
            except:
                initiative_order = []

            encounter_name = "Combat Encounter"
            enemies = []
            for combatant in initiative_order:
                if not combatant.get("is_player"):
                    enemies.append(combatant["name"])
            if enemies:
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
                added_by="D&D GM", include_metadata=False
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
                added_by="D&D GM", include_metadata=False
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
                added_by="D&D GM", include_metadata=False
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

