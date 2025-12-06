"""
D&D Game Master tool schemas for Signal bots.

Tools for running D&D 5e campaigns in Signal group chats.
"""

# D&D Game Master tools
DND_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "start_dnd_campaign",
            "description": "Start a new D&D 5e campaign. Creates a structured campaign spreadsheet with sheets for Overview, Characters, NPCs, Locations, Items, Combat Log, and Session History. Use this when players want to begin a new campaign.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_name": {
                        "type": "string",
                        "description": "Name of the campaign (e.g., 'The Lost Mines', 'Dragon's Lair')"
                    },
                    "setting": {
                        "type": "string",
                        "description": "Campaign setting (e.g., 'Forgotten Realms', 'Eberron', 'homebrew medieval fantasy')"
                    },
                    "tone": {
                        "type": "string",
                        "enum": ["heroic", "gritty", "comedic", "horror", "political", "exploration"],
                        "description": "Overall tone of the campaign"
                    },
                    "starting_level": {
                        "type": "integer",
                        "description": "Starting level for characters (1-20, default 1)"
                    },
                    "campaign_size": {
                        "type": "string",
                        "enum": ["small", "medium", "large", "custom"],
                        "description": "Campaign size: small (3 locations), medium (6 locations), large (12 locations), or custom"
                    },
                    "custom_location_count": {
                        "type": "integer",
                        "description": "Number of locations if campaign_size is 'custom' (3-20)"
                    },
                    "template_spreadsheet_id": {
                        "type": "string",
                        "description": "Google Sheets ID of the campaign template to duplicate (optional, uses default if not provided)"
                    }
                },
                "required": ["campaign_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_campaign_state",
            "description": "Load the current state of a D&D campaign. Returns overview, active characters, current location, and recent events. Use when resuming a campaign or when you need context about the game state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_name": {
                        "type": "string",
                        "description": "Name of the campaign to load. If not specified, uses the most recently played campaign."
                    },
                    "include_characters": {
                        "type": "boolean",
                        "description": "Include full character sheets (default true)"
                    },
                    "include_npcs": {
                        "type": "boolean",
                        "description": "Include known NPCs (default true)"
                    },
                    "include_locations": {
                        "type": "boolean",
                        "description": "Include discovered locations (default false)"
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
            "name": "update_campaign_state",
            "description": "Update the campaign state after significant events. Use after combat, location changes, major story beats, or at session end. Records changes to Overview sheet and Session History.",
            "parameters": {
                "type": "object",
                "properties": {
                    "current_location": {
                        "type": "string",
                        "description": "Current location name"
                    },
                    "session_summary": {
                        "type": "string",
                        "description": "Brief summary of what happened this session"
                    },
                    "story_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Important story flags or quest states to track"
                    },
                    "next_session_hook": {
                        "type": "string",
                        "description": "Hook or cliffhanger for next session"
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
            "name": "create_character",
            "description": "Create a new player character with full D&D 5e mechanics. Records to the Characters sheet. Use after guiding the player through race, class, background, ability scores, and equipment selection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "Real name of the player"
                    },
                    "character_name": {
                        "type": "string",
                        "description": "Character's in-game name"
                    },
                    "race": {
                        "type": "string",
                        "description": "Character race (Human, Elf, Dwarf, Halfling, Dragonborn, Gnome, Half-Elf, Half-Orc, Tiefling, or subrace like High Elf, Hill Dwarf)"
                    },
                    "character_class": {
                        "type": "string",
                        "description": "Character class (Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, Wizard)"
                    },
                    "background": {
                        "type": "string",
                        "description": "Character background (Acolyte, Charlatan, Criminal, Entertainer, Folk Hero, Guild Artisan, Hermit, Noble, Outlander, Sage, Sailor, Soldier, Urchin)"
                    },
                    "ability_scores": {
                        "type": "object",
                        "properties": {
                            "strength": {"type": "integer"},
                            "dexterity": {"type": "integer"},
                            "constitution": {"type": "integer"},
                            "intelligence": {"type": "integer"},
                            "wisdom": {"type": "integer"},
                            "charisma": {"type": "integer"}
                        },
                        "description": "Base ability scores (3-18 each, before racial bonuses)"
                    },
                    "personality_traits": {
                        "type": "string",
                        "description": "Two personality traits"
                    },
                    "ideal": {
                        "type": "string",
                        "description": "Character's driving ideal"
                    },
                    "bond": {
                        "type": "string",
                        "description": "Character's important bond"
                    },
                    "flaw": {
                        "type": "string",
                        "description": "Character's flaw or weakness"
                    },
                    "player_number": {
                        "type": "integer",
                        "description": "Which player this character belongs to (1, 2, 3, etc.)"
                    }
                },
                "required": ["player_name", "character_name", "race", "character_class"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_character",
            "description": "Update a character's stats, HP, inventory, conditions, or other attributes. Use after level up, damage, healing, item acquisition, or condition changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "character_name": {
                        "type": "string",
                        "description": "Name of the character to update"
                    },
                    "current_hp": {
                        "type": "integer",
                        "description": "Current hit points"
                    },
                    "temp_hp": {
                        "type": "integer",
                        "description": "Temporary hit points"
                    },
                    "level": {
                        "type": "integer",
                        "description": "New level (if leveling up)"
                    },
                    "xp": {
                        "type": "integer",
                        "description": "Current XP total"
                    },
                    "gold": {
                        "type": "number",
                        "description": "Current gold pieces"
                    },
                    "add_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Items to add to inventory"
                    },
                    "remove_items": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Items to remove from inventory"
                    },
                    "conditions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Active conditions (poisoned, frightened, exhausted, etc.)"
                    },
                    "spell_slots_used": {
                        "type": "object",
                        "description": "Spell slots used per level (e.g., {\"1st\": 2, \"2nd\": 1})"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Additional notes to add to character"
                    }
                },
                "required": ["character_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_combat",
            "description": "Initialize a combat encounter. Rolls initiative for all participants, sets up combat order, and updates the campaign to combat mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "encounter_name": {
                        "type": "string",
                        "description": "Name for this encounter (e.g., 'Goblin Ambush', 'Dragon Boss Fight')"
                    },
                    "enemies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Enemy name"},
                                "hp": {"type": "integer", "description": "Hit points"},
                                "ac": {"type": "integer", "description": "Armor class"},
                                "initiative_mod": {"type": "integer", "description": "Initiative modifier"}
                            },
                            "required": ["name", "hp", "ac"]
                        },
                        "description": "List of enemies with their stats"
                    },
                    "surprise": {
                        "type": "string",
                        "enum": ["none", "players", "enemies"],
                        "description": "Who is surprised, if anyone (default: none)"
                    }
                },
                "required": ["encounter_name", "enemies"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_combat",
            "description": "End the current combat encounter. Records outcome to Combat Log, awards XP, and returns the campaign to exploration mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "outcome": {
                        "type": "string",
                        "enum": ["victory", "defeat", "fled", "negotiated"],
                        "description": "How the combat ended"
                    },
                    "xp_awarded": {
                        "type": "integer",
                        "description": "Total XP to distribute among the party"
                    },
                    "loot": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Items looted from the encounter"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Notable events from this combat"
                    }
                },
                "required": ["outcome"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_npc",
            "description": "Add a new NPC to the campaign. Records to the NPCs sheet for future reference.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "NPC's name"
                    },
                    "role": {
                        "type": "string",
                        "description": "NPC's role (shopkeeper, quest giver, villain, guard, innkeeper, etc.)"
                    },
                    "location": {
                        "type": "string",
                        "description": "Where this NPC can typically be found"
                    },
                    "description": {
                        "type": "string",
                        "description": "Physical description, personality, mannerisms"
                    },
                    "relationship": {
                        "type": "string",
                        "enum": ["friendly", "neutral", "hostile", "unknown"],
                        "description": "Relationship to the party"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Important information, secrets, or plot hooks for this NPC"
                    }
                },
                "required": ["name", "role"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_location",
            "description": "Add a new location to the campaign. Records to the Locations sheet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Location name"
                    },
                    "location_type": {
                        "type": "string",
                        "description": "Type of location (city, town, village, dungeon, wilderness, tavern, temple, castle, etc.)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the location - sights, sounds, atmosphere"
                    },
                    "connected_to": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Other locations this connects to"
                    },
                    "npcs_present": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "NPCs typically found here"
                    },
                    "discovered": {
                        "type": "boolean",
                        "description": "Whether players have discovered this location (default true)"
                    }
                },
                "required": ["name", "location_type"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_campaigns",
            "description": "List all D&D campaigns for this group. Use to find available campaigns when a player wants to continue playing.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False
            }
        }
    },
    # =========================================================================
    # NEW CAMPAIGN SETUP TOOLS
    # =========================================================================
    {
        "type": "function",
        "function": {
            "name": "generate_locations",
            "description": "Auto-generate locations for a campaign based on setting, tone, and size. Use after start_dnd_campaign to create the world's locations. Presents locations for user approval before saving.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_count": {
                        "type": "integer",
                        "description": "Number of locations to generate (typically 3, 6, or 12)"
                    },
                    "setting": {
                        "type": "string",
                        "description": "Campaign setting (e.g., 'high fantasy', 'dark fantasy')"
                    },
                    "tone": {
                        "type": "string",
                        "description": "Campaign tone (e.g., 'heroic', 'exploration', 'horror')"
                    },
                    "preferences": {
                        "type": "string",
                        "description": "Optional user preferences for location themes or specific locations to include"
                    }
                },
                "required": ["location_count"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_locations",
            "description": "Save generated locations to the campaign spreadsheet. Use after generate_locations when user approves the locations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "index": {"type": "integer"}
                            }
                        },
                        "description": "Array of location objects to save"
                    }
                },
                "required": ["locations"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "assign_route",
            "description": "Determine start and end locations via dice rolls and calculate difficulty tiers for all locations. Use after locations are saved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "manual_start": {
                        "type": "string",
                        "description": "Location name to use as starting point (optional - if not provided, rolls dice)"
                    },
                    "manual_end": {
                        "type": "string",
                        "description": "Location name to use as ending point (optional - if not provided, rolls dice)"
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
            "name": "generate_npcs_for_location",
            "description": "Auto-generate NPCs for a specific location based on its type and difficulty tier. Use during the NPC generation phase, one location at a time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location_name": {
                        "type": "string",
                        "description": "Name of the location to populate with NPCs"
                    },
                    "preferences": {
                        "type": "string",
                        "description": "Optional user preferences for this location's NPCs (e.g., 'include a grumpy blacksmith', 'the boss should be a werewolf')"
                    }
                },
                "required": ["location_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finalize_starting_items",
            "description": "Confirm all characters have starting equipment and optionally add special items. Use after character creation is complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "special_items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Item name"},
                                "type": {"type": "string", "description": "Item type (weapon, armor, potion, misc)"},
                                "description": {"type": "string", "description": "Item description"},
                                "owner": {"type": "string", "description": "Character name who owns this item"}
                            }
                        },
                        "description": "Array of special items to add to characters"
                    },
                    "confirm_ready": {
                        "type": "boolean",
                        "description": "Set to true to confirm setup is complete and move to ready_to_play phase"
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
            "name": "update_campaign_phase",
            "description": "Update the campaign's current phase. Use to track progress through setup workflow.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": ["world_building", "location_creation", "route_determination", "npc_generation", "character_creation", "item_setup", "ready_to_play", "in_progress"],
                        "description": "The new campaign phase"
                    }
                },
                "required": ["phase"],
                "additionalProperties": False
            }
        }
    }
]
