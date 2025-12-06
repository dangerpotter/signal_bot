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
    }
]
