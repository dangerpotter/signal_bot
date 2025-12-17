"""
D&D 5e client for Signal bot GM system.

Provides helper functions and data constants for running D&D 5e campaigns.
"""

import json
from typing import Optional

# =============================================================================
# CORE CALCULATION FUNCTIONS
# =============================================================================

def calculate_modifier(score: int) -> int:
    """Calculate ability modifier from score. (score - 10) // 2"""
    return (score - 10) // 2


def calculate_proficiency_bonus(level: int) -> int:
    """Calculate proficiency bonus from character level."""
    return 2 + (level - 1) // 4


def calculate_hp(class_name: str, level: int, con_mod: int) -> int:
    """
    Calculate max HP for a character.
    Level 1: Max hit die + CON mod
    Level 2+: Average roll (die/2 + 1) + CON mod per level
    """
    hit_die = CLASS_HIT_DICE.get(class_name, 8)
    if level == 1:
        return hit_die + con_mod
    return hit_die + con_mod + (level - 1) * (hit_die // 2 + 1 + con_mod)


def calculate_ac(dex_mod: int, armor_type: Optional[str] = None, shield: bool = False) -> int:
    """
    Calculate Armor Class.
    No armor: 10 + DEX
    Light armor: 11-12 + DEX
    Medium armor: 12-15 + DEX (max 2)
    Heavy armor: 14-18 (no DEX)
    """
    base_ac = 10 + dex_mod  # Unarmored

    if armor_type:
        armor_type = armor_type.lower()
        if armor_type in ARMOR_AC:
            armor_info = ARMOR_AC[armor_type]
            base_ac = armor_info["ac"]
            if armor_info["type"] == "light":
                base_ac += dex_mod
            elif armor_info["type"] == "medium":
                base_ac += min(dex_mod, 2)
            # Heavy armor gets no DEX bonus

    if shield:
        base_ac += 2

    return base_ac


def get_speed(race: str) -> int:
    """Get base walking speed for a race."""
    race_data = RACES.get(race, {})
    return race_data.get("speed", 30)


def format_modifier(mod: int) -> str:
    """Format modifier with + or - sign."""
    return f"+{mod}" if mod >= 0 else str(mod)


# =============================================================================
# CHARACTER SHEET HELPERS
# =============================================================================

def build_character_stats(
    race: str,
    class_name: str,
    background: str,
    base_scores: dict,
    level: int = 1
) -> dict:
    """
    Build complete character stats from base info.

    Args:
        race: Character race (e.g., "Human", "Elf")
        class_name: Character class (e.g., "Fighter", "Wizard")
        background: Character background (e.g., "Soldier", "Sage")
        base_scores: Dict with STR, DEX, CON, INT, WIS, CHA scores
        level: Character level (default 1)

    Returns:
        Complete character stats dict
    """
    # Apply racial ability bonuses
    race_data = RACES.get(race, {})
    ability_bonuses = race_data.get("ability_bonus", {})

    final_scores = {
        "strength": base_scores.get("strength", 10) + ability_bonuses.get("strength", 0),
        "dexterity": base_scores.get("dexterity", 10) + ability_bonuses.get("dexterity", 0),
        "constitution": base_scores.get("constitution", 10) + ability_bonuses.get("constitution", 0),
        "intelligence": base_scores.get("intelligence", 10) + ability_bonuses.get("intelligence", 0),
        "wisdom": base_scores.get("wisdom", 10) + ability_bonuses.get("wisdom", 0),
        "charisma": base_scores.get("charisma", 10) + ability_bonuses.get("charisma", 0),
    }

    # Calculate modifiers
    modifiers = {k: calculate_modifier(v) for k, v in final_scores.items()}

    # Get class and background info
    class_data = CLASSES.get(class_name, {})
    bg_data = BACKGROUNDS.get(background, {})

    # Calculate derived stats
    con_mod = modifiers["constitution"]
    dex_mod = modifiers["dexterity"]
    proficiency = calculate_proficiency_bonus(level)

    # Determine starting equipment and calculate AC
    starting_armor = None
    has_shield = False
    equipment = get_starting_equipment(class_name, background)

    for item in equipment:
        item_lower = item.lower()
        if "shield" in item_lower:
            has_shield = True
        for armor_name in ARMOR_AC.keys():
            if armor_name in item_lower:
                starting_armor = armor_name
                break

    # Build skill proficiencies
    skill_profs = get_skill_proficiencies(class_name, background)

    # Build saving throw proficiencies
    saving_throws = class_data.get("saving_throws", [])

    return {
        "level": level,
        "race": race,
        "class": class_name,
        "background": background,
        "proficiency_bonus": proficiency,
        "speed": get_speed(race),
        "hit_die": f"d{class_data.get('hit_die', 8)}",
        "max_hp": calculate_hp(class_name, level, con_mod),
        "current_hp": calculate_hp(class_name, level, con_mod),
        "temp_hp": 0,
        "ac": calculate_ac(dex_mod, starting_armor, has_shield),
        "ability_scores": final_scores,
        "modifiers": modifiers,
        "skill_proficiencies": skill_profs,
        "saving_throw_proficiencies": saving_throws,
        "equipment": equipment,
        "gold": bg_data.get("starting_gold", 0),
        "racial_traits": race_data.get("traits", []),
        "class_features": get_class_features(class_name, level),
    }


def get_starting_equipment(class_name: str, background: str) -> list:
    """Get starting equipment for a class and background combo."""
    class_data = CLASSES.get(class_name, {})
    bg_data = BACKGROUNDS.get(background, {})

    equipment = []
    equipment.extend(class_data.get("starting_equipment", []))
    equipment.extend(bg_data.get("equipment", []))

    return equipment


def get_skill_proficiencies(class_name: str, background: str) -> list:
    """Get skill proficiencies from class and background."""
    bg_data = BACKGROUNDS.get(background, {})

    # Background skills are fixed
    skills = list(bg_data.get("skills", []))

    # Note: In actual play, class skills are chosen from a list
    # For simplicity, we'll return default recommendations
    class_data = CLASSES.get(class_name, {})
    default_skills = class_data.get("default_skills", [])

    for skill in default_skills:
        if skill not in skills:
            skills.append(skill)

    return skills


def get_class_features(class_name: str, level: int) -> list:
    """Get class features for a class at a given level."""
    class_data = CLASSES.get(class_name, {})
    all_features = class_data.get("features", {})

    features = []
    for lvl, feature_list in all_features.items():
        if int(lvl) <= level:
            features.extend(feature_list)

    return features


# =============================================================================
# SPELL SLOT TABLE (5e Standard)
# =============================================================================

SPELL_SLOTS = {
    # level: [1st, 2nd, 3rd, 4th, 5th, 6th, 7th, 8th, 9th]
    1: [2, 0, 0, 0, 0, 0, 0, 0, 0],
    2: [3, 0, 0, 0, 0, 0, 0, 0, 0],
    3: [4, 2, 0, 0, 0, 0, 0, 0, 0],
    4: [4, 3, 0, 0, 0, 0, 0, 0, 0],
    5: [4, 3, 2, 0, 0, 0, 0, 0, 0],
    6: [4, 3, 3, 0, 0, 0, 0, 0, 0],
    7: [4, 3, 3, 1, 0, 0, 0, 0, 0],
    8: [4, 3, 3, 2, 0, 0, 0, 0, 0],
    9: [4, 3, 3, 3, 1, 0, 0, 0, 0],
    10: [4, 3, 3, 3, 2, 0, 0, 0, 0],
    11: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    12: [4, 3, 3, 3, 2, 1, 0, 0, 0],
    13: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    14: [4, 3, 3, 3, 2, 1, 1, 0, 0],
    15: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    16: [4, 3, 3, 3, 2, 1, 1, 1, 0],
    17: [4, 3, 3, 3, 2, 1, 1, 1, 1],
    18: [4, 3, 3, 3, 3, 1, 1, 1, 1],
    19: [4, 3, 3, 3, 3, 2, 1, 1, 1],
    20: [4, 3, 3, 3, 3, 2, 2, 1, 1],
}


def get_spell_slots(class_name: str, level: int) -> dict:
    """Get spell slots for a spellcasting class at a given level."""
    class_data = CLASSES.get(class_name, {})

    if not class_data.get("spellcasting"):
        return {}

    caster_type = class_data.get("caster_type", "full")

    # Calculate effective caster level
    if caster_type == "full":
        caster_level = level
    elif caster_type == "half":
        caster_level = level // 2
    elif caster_type == "third":
        caster_level = level // 3
    else:
        return {}

    if caster_level < 1:
        return {}

    slots = SPELL_SLOTS.get(min(caster_level, 20), [0] * 9)

    return {
        "1st": slots[0],
        "2nd": slots[1],
        "3rd": slots[2],
        "4th": slots[3],
        "5th": slots[4],
        "6th": slots[5],
        "7th": slots[6],
        "8th": slots[7],
        "9th": slots[8],
    }


# =============================================================================
# HIT DICE BY CLASS
# =============================================================================

CLASS_HIT_DICE = {
    "Barbarian": 12,
    "Fighter": 10,
    "Paladin": 10,
    "Ranger": 10,
    "Bard": 8,
    "Cleric": 8,
    "Druid": 8,
    "Monk": 8,
    "Rogue": 8,
    "Warlock": 8,
    "Sorcerer": 6,
    "Wizard": 6,
}


# =============================================================================
# ARMOR DATA
# =============================================================================

ARMOR_AC = {
    # Light Armor
    "padded": {"ac": 11, "type": "light"},
    "leather": {"ac": 11, "type": "light"},
    "studded leather": {"ac": 12, "type": "light"},
    # Medium Armor
    "hide": {"ac": 12, "type": "medium"},
    "chain shirt": {"ac": 13, "type": "medium"},
    "scale mail": {"ac": 14, "type": "medium"},
    "breastplate": {"ac": 14, "type": "medium"},
    "half plate": {"ac": 15, "type": "medium"},
    # Heavy Armor
    "ring mail": {"ac": 14, "type": "heavy"},
    "chain mail": {"ac": 16, "type": "heavy"},
    "splint": {"ac": 17, "type": "heavy"},
    "plate": {"ac": 18, "type": "heavy"},
}


# =============================================================================
# SKILLS LIST
# =============================================================================

SKILLS = [
    "Acrobatics",
    "Animal Handling",
    "Arcana",
    "Athletics",
    "Deception",
    "History",
    "Insight",
    "Intimidation",
    "Investigation",
    "Medicine",
    "Nature",
    "Perception",
    "Performance",
    "Persuasion",
    "Religion",
    "Sleight of Hand",
    "Stealth",
    "Survival",
]

# Skill to ability mapping
SKILL_ABILITIES = {
    "Acrobatics": "dexterity",
    "Animal Handling": "wisdom",
    "Arcana": "intelligence",
    "Athletics": "strength",
    "Deception": "charisma",
    "History": "intelligence",
    "Insight": "wisdom",
    "Intimidation": "charisma",
    "Investigation": "intelligence",
    "Medicine": "wisdom",
    "Nature": "intelligence",
    "Perception": "wisdom",
    "Performance": "charisma",
    "Persuasion": "charisma",
    "Religion": "intelligence",
    "Sleight of Hand": "dexterity",
    "Stealth": "dexterity",
    "Survival": "wisdom",
}


# =============================================================================
# RACES (Core PHB)
# =============================================================================

RACES = {
    "Human": {
        "ability_bonus": {
            "strength": 1,
            "dexterity": 1,
            "constitution": 1,
            "intelligence": 1,
            "wisdom": 1,
            "charisma": 1,
        },
        "speed": 30,
        "size": "Medium",
        "traits": ["Extra Language"],
        "languages": ["Common", "One extra"],
    },
    "Elf": {
        "ability_bonus": {"dexterity": 2},
        "speed": 30,
        "size": "Medium",
        "traits": ["Darkvision", "Keen Senses", "Fey Ancestry", "Trance"],
        "languages": ["Common", "Elvish"],
        "subraces": ["High Elf", "Wood Elf", "Dark Elf (Drow)"],
    },
    "High Elf": {
        "ability_bonus": {"dexterity": 2, "intelligence": 1},
        "speed": 30,
        "size": "Medium",
        "traits": ["Darkvision", "Keen Senses", "Fey Ancestry", "Trance", "Elf Weapon Training", "Cantrip", "Extra Language"],
        "languages": ["Common", "Elvish", "One extra"],
    },
    "Wood Elf": {
        "ability_bonus": {"dexterity": 2, "wisdom": 1},
        "speed": 35,
        "size": "Medium",
        "traits": ["Darkvision", "Keen Senses", "Fey Ancestry", "Trance", "Elf Weapon Training", "Fleet of Foot", "Mask of the Wild"],
        "languages": ["Common", "Elvish"],
    },
    "Dwarf": {
        "ability_bonus": {"constitution": 2},
        "speed": 25,
        "size": "Medium",
        "traits": ["Darkvision", "Dwarven Resilience", "Dwarven Combat Training", "Stonecunning"],
        "languages": ["Common", "Dwarvish"],
        "subraces": ["Hill Dwarf", "Mountain Dwarf"],
    },
    "Hill Dwarf": {
        "ability_bonus": {"constitution": 2, "wisdom": 1},
        "speed": 25,
        "size": "Medium",
        "traits": ["Darkvision", "Dwarven Resilience", "Dwarven Combat Training", "Stonecunning", "Dwarven Toughness"],
        "languages": ["Common", "Dwarvish"],
    },
    "Mountain Dwarf": {
        "ability_bonus": {"constitution": 2, "strength": 2},
        "speed": 25,
        "size": "Medium",
        "traits": ["Darkvision", "Dwarven Resilience", "Dwarven Combat Training", "Stonecunning", "Dwarven Armor Training"],
        "languages": ["Common", "Dwarvish"],
    },
    "Halfling": {
        "ability_bonus": {"dexterity": 2},
        "speed": 25,
        "size": "Small",
        "traits": ["Lucky", "Brave", "Halfling Nimbleness"],
        "languages": ["Common", "Halfling"],
        "subraces": ["Lightfoot", "Stout"],
    },
    "Lightfoot Halfling": {
        "ability_bonus": {"dexterity": 2, "charisma": 1},
        "speed": 25,
        "size": "Small",
        "traits": ["Lucky", "Brave", "Halfling Nimbleness", "Naturally Stealthy"],
        "languages": ["Common", "Halfling"],
    },
    "Stout Halfling": {
        "ability_bonus": {"dexterity": 2, "constitution": 1},
        "speed": 25,
        "size": "Small",
        "traits": ["Lucky", "Brave", "Halfling Nimbleness", "Stout Resilience"],
        "languages": ["Common", "Halfling"],
    },
    "Dragonborn": {
        "ability_bonus": {"strength": 2, "charisma": 1},
        "speed": 30,
        "size": "Medium",
        "traits": ["Draconic Ancestry", "Breath Weapon", "Damage Resistance"],
        "languages": ["Common", "Draconic"],
    },
    "Gnome": {
        "ability_bonus": {"intelligence": 2},
        "speed": 25,
        "size": "Small",
        "traits": ["Darkvision", "Gnome Cunning"],
        "languages": ["Common", "Gnomish"],
        "subraces": ["Forest Gnome", "Rock Gnome"],
    },
    "Half-Elf": {
        "ability_bonus": {"charisma": 2},  # +1 to two other abilities (player's choice)
        "speed": 30,
        "size": "Medium",
        "traits": ["Darkvision", "Fey Ancestry", "Skill Versatility"],
        "languages": ["Common", "Elvish", "One extra"],
    },
    "Half-Orc": {
        "ability_bonus": {"strength": 2, "constitution": 1},
        "speed": 30,
        "size": "Medium",
        "traits": ["Darkvision", "Menacing", "Relentless Endurance", "Savage Attacks"],
        "languages": ["Common", "Orc"],
    },
    "Tiefling": {
        "ability_bonus": {"charisma": 2, "intelligence": 1},
        "speed": 30,
        "size": "Medium",
        "traits": ["Darkvision", "Hellish Resistance", "Infernal Legacy"],
        "languages": ["Common", "Infernal"],
    },
}


# =============================================================================
# CLASSES (Core PHB)
# =============================================================================

CLASSES = {
    "Barbarian": {
        "hit_die": 12,
        "primary_ability": "Strength",
        "saving_throws": ["Strength", "Constitution"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "skill_choices": ["Animal Handling", "Athletics", "Intimidation", "Nature", "Perception", "Survival"],
        "num_skills": 2,
        "default_skills": ["Athletics", "Intimidation"],
        "starting_equipment": ["Greataxe", "Two handaxes", "Explorer's pack", "Four javelins"],
        "spellcasting": False,
        "features": {
            "1": ["Rage", "Unarmored Defense"],
            "2": ["Reckless Attack", "Danger Sense"],
            "3": ["Primal Path"],
            "4": ["Ability Score Improvement"],
            "5": ["Extra Attack", "Fast Movement"],
        },
    },
    "Bard": {
        "hit_die": 8,
        "primary_ability": "Charisma",
        "saving_throws": ["Dexterity", "Charisma"],
        "armor_proficiencies": ["Light armor"],
        "weapon_proficiencies": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
        "skill_choices": SKILLS,  # Bards can choose any 3 skills
        "num_skills": 3,
        "default_skills": ["Performance", "Persuasion", "Deception"],
        "starting_equipment": ["Rapier", "Diplomat's pack", "Lute", "Leather armor", "Dagger"],
        "spellcasting": True,
        "caster_type": "full",
        "spellcasting_ability": "Charisma",
        "features": {
            "1": ["Spellcasting", "Bardic Inspiration (d6)"],
            "2": ["Jack of All Trades", "Song of Rest (d6)"],
            "3": ["Bard College", "Expertise"],
            "4": ["Ability Score Improvement"],
            "5": ["Bardic Inspiration (d8)", "Font of Inspiration"],
        },
    },
    "Cleric": {
        "hit_die": 8,
        "primary_ability": "Wisdom",
        "saving_throws": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "weapon_proficiencies": ["Simple weapons"],
        "skill_choices": ["History", "Insight", "Medicine", "Persuasion", "Religion"],
        "num_skills": 2,
        "default_skills": ["Insight", "Religion"],
        "starting_equipment": ["Mace", "Scale mail", "Light crossbow and 20 bolts", "Priest's pack", "Shield", "Holy symbol"],
        "spellcasting": True,
        "caster_type": "full",
        "spellcasting_ability": "Wisdom",
        "features": {
            "1": ["Spellcasting", "Divine Domain"],
            "2": ["Channel Divinity (1/rest)", "Divine Domain feature"],
            "3": [],
            "4": ["Ability Score Improvement"],
            "5": ["Destroy Undead (CR 1/2)"],
        },
    },
    "Druid": {
        "hit_die": 8,
        "primary_ability": "Wisdom",
        "saving_throws": ["Intelligence", "Wisdom"],
        "armor_proficiencies": ["Light armor (non-metal)", "Medium armor (non-metal)", "Shields (non-metal)"],
        "weapon_proficiencies": ["Clubs", "Daggers", "Darts", "Javelins", "Maces", "Quarterstaffs", "Scimitars", "Sickles", "Slings", "Spears"],
        "skill_choices": ["Arcana", "Animal Handling", "Insight", "Medicine", "Nature", "Perception", "Religion", "Survival"],
        "num_skills": 2,
        "default_skills": ["Nature", "Perception"],
        "starting_equipment": ["Wooden shield", "Scimitar", "Leather armor", "Explorer's pack", "Druidic focus"],
        "spellcasting": True,
        "caster_type": "full",
        "spellcasting_ability": "Wisdom",
        "features": {
            "1": ["Druidic", "Spellcasting"],
            "2": ["Wild Shape", "Druid Circle"],
            "3": [],
            "4": ["Wild Shape improvement", "Ability Score Improvement"],
            "5": [],
        },
    },
    "Fighter": {
        "hit_die": 10,
        "primary_ability": "Strength or Dexterity",
        "saving_throws": ["Strength", "Constitution"],
        "armor_proficiencies": ["All armor", "Shields"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "skill_choices": ["Acrobatics", "Animal Handling", "Athletics", "History", "Insight", "Intimidation", "Perception", "Survival"],
        "num_skills": 2,
        "default_skills": ["Athletics", "Perception"],
        "starting_equipment": ["Chain mail", "Longsword", "Shield", "Light crossbow and 20 bolts", "Dungeoneer's pack"],
        "spellcasting": False,
        "features": {
            "1": ["Fighting Style", "Second Wind"],
            "2": ["Action Surge (one use)"],
            "3": ["Martial Archetype"],
            "4": ["Ability Score Improvement"],
            "5": ["Extra Attack"],
        },
    },
    "Monk": {
        "hit_die": 8,
        "primary_ability": "Dexterity and Wisdom",
        "saving_throws": ["Strength", "Dexterity"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Simple weapons", "Shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "History", "Insight", "Religion", "Stealth"],
        "num_skills": 2,
        "default_skills": ["Acrobatics", "Stealth"],
        "starting_equipment": ["Shortsword", "Dungeoneer's pack", "10 darts"],
        "spellcasting": False,
        "features": {
            "1": ["Unarmored Defense", "Martial Arts"],
            "2": ["Ki", "Unarmored Movement"],
            "3": ["Monastic Tradition", "Deflect Missiles"],
            "4": ["Ability Score Improvement", "Slow Fall"],
            "5": ["Extra Attack", "Stunning Strike"],
        },
    },
    "Paladin": {
        "hit_die": 10,
        "primary_ability": "Strength and Charisma",
        "saving_throws": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["All armor", "Shields"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "skill_choices": ["Athletics", "Insight", "Intimidation", "Medicine", "Persuasion", "Religion"],
        "num_skills": 2,
        "default_skills": ["Athletics", "Persuasion"],
        "starting_equipment": ["Chain mail", "Longsword", "Shield", "5 javelins", "Priest's pack", "Holy symbol"],
        "spellcasting": True,
        "caster_type": "half",
        "spellcasting_ability": "Charisma",
        "features": {
            "1": ["Divine Sense", "Lay on Hands"],
            "2": ["Fighting Style", "Spellcasting", "Divine Smite"],
            "3": ["Divine Health", "Sacred Oath"],
            "4": ["Ability Score Improvement"],
            "5": ["Extra Attack"],
        },
    },
    "Ranger": {
        "hit_die": 10,
        "primary_ability": "Dexterity and Wisdom",
        "saving_throws": ["Strength", "Dexterity"],
        "armor_proficiencies": ["Light armor", "Medium armor", "Shields"],
        "weapon_proficiencies": ["Simple weapons", "Martial weapons"],
        "skill_choices": ["Animal Handling", "Athletics", "Insight", "Investigation", "Nature", "Perception", "Stealth", "Survival"],
        "num_skills": 3,
        "default_skills": ["Perception", "Stealth", "Survival"],
        "starting_equipment": ["Scale mail", "Two shortswords", "Dungeoneer's pack", "Longbow and 20 arrows"],
        "spellcasting": True,
        "caster_type": "half",
        "spellcasting_ability": "Wisdom",
        "features": {
            "1": ["Favored Enemy", "Natural Explorer"],
            "2": ["Fighting Style", "Spellcasting"],
            "3": ["Ranger Archetype", "Primeval Awareness"],
            "4": ["Ability Score Improvement"],
            "5": ["Extra Attack"],
        },
    },
    "Rogue": {
        "hit_die": 8,
        "primary_ability": "Dexterity",
        "saving_throws": ["Dexterity", "Intelligence"],
        "armor_proficiencies": ["Light armor"],
        "weapon_proficiencies": ["Simple weapons", "Hand crossbows", "Longswords", "Rapiers", "Shortswords"],
        "skill_choices": ["Acrobatics", "Athletics", "Deception", "Insight", "Intimidation", "Investigation", "Perception", "Performance", "Persuasion", "Sleight of Hand", "Stealth"],
        "num_skills": 4,
        "default_skills": ["Stealth", "Perception", "Sleight of Hand", "Investigation"],
        "starting_equipment": ["Rapier", "Shortbow and 20 arrows", "Burglar's pack", "Leather armor", "Two daggers", "Thieves' tools"],
        "spellcasting": False,
        "features": {
            "1": ["Expertise", "Sneak Attack (1d6)", "Thieves' Cant"],
            "2": ["Cunning Action"],
            "3": ["Roguish Archetype", "Sneak Attack (2d6)"],
            "4": ["Ability Score Improvement"],
            "5": ["Uncanny Dodge", "Sneak Attack (3d6)"],
        },
    },
    "Sorcerer": {
        "hit_die": 6,
        "primary_ability": "Charisma",
        "saving_throws": ["Constitution", "Charisma"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "skill_choices": ["Arcana", "Deception", "Insight", "Intimidation", "Persuasion", "Religion"],
        "num_skills": 2,
        "default_skills": ["Arcana", "Persuasion"],
        "starting_equipment": ["Light crossbow and 20 bolts", "Component pouch", "Dungeoneer's pack", "Two daggers"],
        "spellcasting": True,
        "caster_type": "full",
        "spellcasting_ability": "Charisma",
        "features": {
            "1": ["Spellcasting", "Sorcerous Origin"],
            "2": ["Font of Magic"],
            "3": ["Metamagic"],
            "4": ["Ability Score Improvement"],
            "5": [],
        },
    },
    "Warlock": {
        "hit_die": 8,
        "primary_ability": "Charisma",
        "saving_throws": ["Wisdom", "Charisma"],
        "armor_proficiencies": ["Light armor"],
        "weapon_proficiencies": ["Simple weapons"],
        "skill_choices": ["Arcana", "Deception", "History", "Intimidation", "Investigation", "Nature", "Religion"],
        "num_skills": 2,
        "default_skills": ["Arcana", "Deception"],
        "starting_equipment": ["Light crossbow and 20 bolts", "Component pouch", "Scholar's pack", "Leather armor", "Simple weapon", "Two daggers"],
        "spellcasting": True,
        "caster_type": "pact",  # Special: Pact Magic
        "spellcasting_ability": "Charisma",
        "features": {
            "1": ["Otherworldly Patron", "Pact Magic"],
            "2": ["Eldritch Invocations"],
            "3": ["Pact Boon"],
            "4": ["Ability Score Improvement"],
            "5": [],
        },
    },
    "Wizard": {
        "hit_die": 6,
        "primary_ability": "Intelligence",
        "saving_throws": ["Intelligence", "Wisdom"],
        "armor_proficiencies": [],
        "weapon_proficiencies": ["Daggers", "Darts", "Slings", "Quarterstaffs", "Light crossbows"],
        "skill_choices": ["Arcana", "History", "Insight", "Investigation", "Medicine", "Religion"],
        "num_skills": 2,
        "default_skills": ["Arcana", "Investigation"],
        "starting_equipment": ["Quarterstaff", "Component pouch", "Scholar's pack", "Spellbook"],
        "spellcasting": True,
        "caster_type": "full",
        "spellcasting_ability": "Intelligence",
        "features": {
            "1": ["Spellcasting", "Arcane Recovery"],
            "2": ["Arcane Tradition"],
            "3": [],
            "4": ["Ability Score Improvement"],
            "5": [],
        },
    },
}


# =============================================================================
# BACKGROUNDS
# =============================================================================

BACKGROUNDS = {
    "Acolyte": {
        "skills": ["Insight", "Religion"],
        "languages": 2,
        "equipment": ["Holy symbol", "Prayer book or prayer wheel", "5 sticks of incense", "Vestments", "Common clothes", "Belt pouch"],
        "starting_gold": 15,
        "feature": "Shelter of the Faithful",
    },
    "Charlatan": {
        "skills": ["Deception", "Sleight of Hand"],
        "tool_proficiencies": ["Disguise kit", "Forgery kit"],
        "equipment": ["Fine clothes", "Disguise kit", "Con tools", "Belt pouch"],
        "starting_gold": 15,
        "feature": "False Identity",
    },
    "Criminal": {
        "skills": ["Deception", "Stealth"],
        "tool_proficiencies": ["Gaming set", "Thieves' tools"],
        "equipment": ["Crowbar", "Dark common clothes with hood", "Belt pouch"],
        "starting_gold": 15,
        "feature": "Criminal Contact",
    },
    "Entertainer": {
        "skills": ["Acrobatics", "Performance"],
        "tool_proficiencies": ["Disguise kit", "Musical instrument"],
        "equipment": ["Musical instrument", "Favor of an admirer", "Costume", "Belt pouch"],
        "starting_gold": 15,
        "feature": "By Popular Demand",
    },
    "Folk Hero": {
        "skills": ["Animal Handling", "Survival"],
        "tool_proficiencies": ["Artisan's tools", "Vehicles (land)"],
        "equipment": ["Artisan's tools", "Shovel", "Iron pot", "Common clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "Rustic Hospitality",
    },
    "Guild Artisan": {
        "skills": ["Insight", "Persuasion"],
        "tool_proficiencies": ["Artisan's tools"],
        "languages": 1,
        "equipment": ["Artisan's tools", "Letter of introduction", "Traveler's clothes", "Belt pouch"],
        "starting_gold": 15,
        "feature": "Guild Membership",
    },
    "Hermit": {
        "skills": ["Medicine", "Religion"],
        "tool_proficiencies": ["Herbalism kit"],
        "languages": 1,
        "equipment": ["Scroll case with notes", "Winter blanket", "Common clothes", "Herbalism kit"],
        "starting_gold": 5,
        "feature": "Discovery",
    },
    "Noble": {
        "skills": ["History", "Persuasion"],
        "tool_proficiencies": ["Gaming set"],
        "languages": 1,
        "equipment": ["Fine clothes", "Signet ring", "Scroll of pedigree", "Purse"],
        "starting_gold": 25,
        "feature": "Position of Privilege",
    },
    "Outlander": {
        "skills": ["Athletics", "Survival"],
        "tool_proficiencies": ["Musical instrument"],
        "languages": 1,
        "equipment": ["Staff", "Hunting trap", "Trophy from animal", "Traveler's clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "Wanderer",
    },
    "Sage": {
        "skills": ["Arcana", "History"],
        "languages": 2,
        "equipment": ["Bottle of ink", "Quill", "Small knife", "Letter from dead colleague", "Common clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "Researcher",
    },
    "Sailor": {
        "skills": ["Athletics", "Perception"],
        "tool_proficiencies": ["Navigator's tools", "Vehicles (water)"],
        "equipment": ["Belaying pin (club)", "50 feet of silk rope", "Lucky charm", "Common clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "Ship's Passage",
    },
    "Soldier": {
        "skills": ["Athletics", "Intimidation"],
        "tool_proficiencies": ["Gaming set", "Vehicles (land)"],
        "equipment": ["Insignia of rank", "Trophy from fallen enemy", "Gaming set", "Common clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "Military Rank",
    },
    "Urchin": {
        "skills": ["Sleight of Hand", "Stealth"],
        "tool_proficiencies": ["Disguise kit", "Thieves' tools"],
        "equipment": ["Small knife", "City map", "Pet mouse", "Token from parents", "Common clothes", "Belt pouch"],
        "starting_gold": 10,
        "feature": "City Secrets",
    },
}


# =============================================================================
# CONDITIONS (5e)
# =============================================================================

CONDITIONS = {
    "Blinded": "Can't see. Auto-fail sight checks. Attacks have disadvantage. Attacks against have advantage.",
    "Charmed": "Can't attack charmer. Charmer has advantage on social checks.",
    "Deafened": "Can't hear. Auto-fail hearing checks.",
    "Frightened": "Disadvantage on ability checks and attacks while source of fear is visible. Can't willingly move closer.",
    "Grappled": "Speed becomes 0. Ends if grappler incapacitated or moved apart.",
    "Incapacitated": "Can't take actions or reactions.",
    "Invisible": "Impossible to see without special sense. Attacks have advantage. Attacks against have disadvantage.",
    "Paralyzed": "Incapacitated. Can't move or speak. Auto-fail STR/DEX saves. Attacks have advantage. Hits within 5ft are crits.",
    "Petrified": "Transformed to stone. Incapacitated. Weight x10. Unaware of surroundings. Resistance to all damage. Immune to poison/disease.",
    "Poisoned": "Disadvantage on attack rolls and ability checks.",
    "Prone": "Can only crawl. Disadvantage on attacks. Melee attacks have advantage, ranged have disadvantage.",
    "Restrained": "Speed 0. Attacks have disadvantage. Attacks against have advantage. Disadvantage on DEX saves.",
    "Stunned": "Incapacitated. Can't move. Speak only falteringly. Auto-fail STR/DEX saves. Attacks have advantage.",
    "Unconscious": "Incapacitated. Can't move or speak. Unaware. Drop what holding, fall prone. Auto-fail STR/DEX saves. Attacks have advantage. Hits within 5ft are crits.",
}

# Exhaustion levels
EXHAUSTION_LEVELS = {
    1: "Disadvantage on ability checks",
    2: "Speed halved",
    3: "Disadvantage on attack rolls and saving throws",
    4: "Hit point maximum halved",
    5: "Speed reduced to 0",
    6: "Death",
}


# =============================================================================
# XP THRESHOLDS
# =============================================================================

XP_BY_LEVEL = {
    1: 0,
    2: 300,
    3: 900,
    4: 2700,
    5: 6500,
    6: 14000,
    7: 23000,
    8: 34000,
    9: 48000,
    10: 64000,
    11: 85000,
    12: 100000,
    13: 120000,
    14: 140000,
    15: 165000,
    16: 195000,
    17: 225000,
    18: 265000,
    19: 305000,
    20: 355000,
}


def get_level_from_xp(xp: int) -> int:
    """Determine character level from XP total."""
    level = 1
    for lvl, threshold in XP_BY_LEVEL.items():
        if xp >= threshold:
            level = lvl
    return level


def get_xp_for_next_level(current_level: int) -> int:
    """Get XP needed for next level."""
    if current_level >= 20:
        return 0
    return XP_BY_LEVEL.get(current_level + 1, 0)


# =============================================================================
# STANDARD ARRAY AND POINT BUY
# =============================================================================

STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]

POINT_BUY_COSTS = {
    8: 0,
    9: 1,
    10: 2,
    11: 3,
    12: 4,
    13: 5,
    14: 7,
    15: 9,
}

POINT_BUY_TOTAL = 27


def validate_point_buy(scores: dict) -> tuple:
    """
    Validate a point buy allocation.
    Returns (is_valid, points_spent, message)
    """
    total = 0
    for ability, score in scores.items():
        if score < 8 or score > 15:
            return (False, 0, f"{ability} must be between 8 and 15")
        total += POINT_BUY_COSTS.get(score, 0)

    if total > POINT_BUY_TOTAL:
        return (False, total, f"Spent {total} points, max is {POINT_BUY_TOTAL}")

    return (True, total, f"Valid! Spent {total}/{POINT_BUY_TOTAL} points")


# =============================================================================
# DIFFICULTY CLASSES
# =============================================================================

DIFFICULTY_CLASSES = {
    "Very Easy": 5,
    "Easy": 10,
    "Medium": 15,
    "Hard": 20,
    "Very Hard": 25,
    "Nearly Impossible": 30,
}


# =============================================================================
# CAMPAIGN SPREADSHEET HELPERS
# =============================================================================

def get_campaign_sheet_headers() -> dict:
    """Get the column headers for each sheet in the campaign spreadsheet."""
    return {
        "Overview": ["Field", "Value"],
        "Characters": [
            "Player Name", "Character Name", "Race", "Class", "Level", "XP",
            "Background", "Max HP", "Current HP", "Temp HP", "AC",
            "STR", "DEX", "CON", "INT", "WIS", "CHA",
            "Proficiency Bonus", "Speed",
            "Skills", "Saving Throws", "Equipment",
            "Gold", "Conditions", "Spell Slots", "Spells Known",
            "Personality Traits", "Ideal", "Bond", "Flaw", "Notes"
        ],
        "NPCs": [
            "Name", "Role", "Location", "Description", "Relationship",
            "First Met (Session)", "Notes", "Status"
        ],
        "Locations": [
            "Name", "Type", "Description", "Connected To",
            "NPCs Present", "Discovered", "First Visited (Session)", "Notes"
        ],
        "Items": [
            "Name", "Type", "Description", "Owner", "Acquired (Session)", "Notes"
        ],
        "Combat Log": [
            "Session", "Encounter Name", "Enemies", "Outcome",
            "XP Awarded", "Loot", "Notes", "Timestamp"
        ],
        "Session History": [
            "Session #", "Date", "Summary", "Key Events",
            "NPCs Met", "Locations Visited", "XP Earned", "Next Session Hook"
        ],
    }


def get_overview_initial_data(campaign_name: str, setting: str, tone: str, starting_level: int) -> list:
    """Get initial Overview sheet data as [field, value] rows."""
    return [
        ["Campaign Name", campaign_name],
        ["Setting", setting or "Fantasy"],
        ["Tone", tone or "heroic"],
        ["Starting Level", str(starting_level)],
        ["Current Date (In-Game)", "Day 1"],
        ["Current Location", "TBD"],
        ["Party Gold", "0"],
        ["Story Flags", ""],
        ["Session Count", "0"],
        ["Last Played", "Never"],
        ["Active Combat", "No"],
        ["Combat Initiative Order", ""],
    ]


def character_to_row(char_data: dict) -> list:
    """Convert character data dict to spreadsheet row."""
    return [
        char_data.get("player_name", ""),
        char_data.get("character_name", ""),
        char_data.get("race", ""),
        char_data.get("class", ""),
        str(char_data.get("level", 1)),
        str(char_data.get("xp", 0)),
        char_data.get("background", ""),
        str(char_data.get("max_hp", 0)),
        str(char_data.get("current_hp", 0)),
        str(char_data.get("temp_hp", 0)),
        str(char_data.get("ac", 10)),
        str(char_data.get("ability_scores", {}).get("strength", 10)),
        str(char_data.get("ability_scores", {}).get("dexterity", 10)),
        str(char_data.get("ability_scores", {}).get("constitution", 10)),
        str(char_data.get("ability_scores", {}).get("intelligence", 10)),
        str(char_data.get("ability_scores", {}).get("wisdom", 10)),
        str(char_data.get("ability_scores", {}).get("charisma", 10)),
        str(char_data.get("proficiency_bonus", 2)),
        str(char_data.get("speed", 30)),
        json.dumps(char_data.get("skill_proficiencies", [])),
        json.dumps(char_data.get("saving_throw_proficiencies", [])),
        json.dumps(char_data.get("equipment", [])),
        str(char_data.get("gold", 0)),
        json.dumps(char_data.get("conditions", [])),
        json.dumps(char_data.get("spell_slots", {})),
        json.dumps(char_data.get("spells_known", [])),
        char_data.get("personality_traits", ""),
        char_data.get("ideal", ""),
        char_data.get("bond", ""),
        char_data.get("flaw", ""),
        char_data.get("notes", ""),
        str(char_data.get("player_number", 1)),  # Column 32 (index 31)
    ]


def row_to_character(row: list) -> dict:
    """Convert spreadsheet row back to character data dict."""
    if len(row) < 32:
        row = row + [""] * (32 - len(row))  # Pad with empty strings

    def safe_json_loads(s, default):
        try:
            return json.loads(s) if s else default
        except:
            return default

    def safe_int(s, default=0):
        try:
            return int(s) if s else default
        except:
            return default

    return {
        "player_name": row[0],
        "character_name": row[1],
        "race": row[2],
        "class": row[3],
        "level": safe_int(row[4], 1),
        "xp": safe_int(row[5], 0),
        "background": row[6],
        "max_hp": safe_int(row[7], 0),
        "current_hp": safe_int(row[8], 0),
        "temp_hp": safe_int(row[9], 0),
        "ac": safe_int(row[10], 10),
        "ability_scores": {
            "strength": safe_int(row[11], 10),
            "dexterity": safe_int(row[12], 10),
            "constitution": safe_int(row[13], 10),
            "intelligence": safe_int(row[14], 10),
            "wisdom": safe_int(row[15], 10),
            "charisma": safe_int(row[16], 10),
        },
        "proficiency_bonus": safe_int(row[17], 2),
        "speed": safe_int(row[18], 30),
        "skill_proficiencies": safe_json_loads(row[19], []),
        "saving_throw_proficiencies": safe_json_loads(row[20], []),
        "equipment": safe_json_loads(row[21], []),
        "gold": safe_int(row[22], 0),
        "conditions": safe_json_loads(row[23], []),
        "spell_slots": safe_json_loads(row[24], {}),
        "spells_known": safe_json_loads(row[25], []),
        "personality_traits": row[26],
        "ideal": row[27],
        "bond": row[28],
        "flaw": row[29],
        "notes": row[30] if len(row) > 30 else "",
        "player_number": safe_int(row[31], 1),
    }


# =============================================================================
# CAMPAIGN PHASES
# =============================================================================

CAMPAIGN_PHASES = [
    "world_building",       # Setting up setting, tone, size
    "location_creation",    # Generating locations
    "route_determination",  # Dice roll for start/end locations
    "npc_generation",       # Populating NPCs per location
    "character_creation",   # Player characters
    "item_setup",           # Starting equipment confirmation
    "ready_to_play",        # Campaign setup complete
    "in_progress",          # Active campaign
]


# =============================================================================
# CAMPAIGN SIZE DEFINITIONS
# =============================================================================

CAMPAIGN_SIZES = {
    "small": 3,
    "medium": 6,
    "large": 12,
}


# =============================================================================
# DIFFICULTY TIER SYSTEM (1-5)
# =============================================================================

DIFFICULTY_TIERS = {
    1: {
        "cr_range": "0-1/4",
        "hp_range": (4, 15),
        "ac_range": (10, 12),
        "attack_bonus": (2, 3),
        "damage": "1d6+1",
        "examples": ["Rat", "Goblin", "Bandit", "Kobold"],
    },
    2: {
        "cr_range": "1/2-1",
        "hp_range": (15, 30),
        "ac_range": (12, 14),
        "attack_bonus": (3, 4),
        "damage": "1d8+2",
        "examples": ["Hobgoblin", "Wolf", "Thug", "Orc"],
    },
    3: {
        "cr_range": "2-3",
        "hp_range": (30, 60),
        "ac_range": (13, 15),
        "attack_bonus": (4, 5),
        "damage": "2d6+3",
        "examples": ["Ogre", "Veteran", "Ghost", "Werewolf"],
    },
    4: {
        "cr_range": "4-6",
        "hp_range": (60, 100),
        "ac_range": (14, 16),
        "attack_bonus": (5, 7),
        "damage": "2d8+4",
        "examples": ["Troll", "Assassin", "Elemental", "Wraith"],
    },
    5: {
        "cr_range": "7+",
        "hp_range": (100, 150),
        "ac_range": (15, 18),
        "attack_bonus": (7, 9),
        "damage": "2d10+5",
        "examples": ["Young Dragon", "Giant", "Vampire Spawn", "Mind Flayer"],
    },
}

# Boss stats are +1-2 CR above regular enemies at each tier
BOSS_TIERS = {
    1: {"cr": "1", "hp_range": (20, 35), "ac": 13, "attack_bonus": 4, "damage": "1d10+2", "examples": ["Bugbear Chief", "Gnoll Pack Lord"]},
    2: {"cr": "2-3", "hp_range": (35, 55), "ac": 14, "attack_bonus": 5, "damage": "2d6+3", "examples": ["Cult Fanatic", "Berserker"]},
    3: {"cr": "4-5", "hp_range": (55, 85), "ac": 15, "attack_bonus": 6, "damage": "2d8+4", "examples": ["Gladiator", "Bandit Captain"]},
    4: {"cr": "6-8", "hp_range": (85, 120), "ac": 16, "attack_bonus": 7, "damage": "2d10+5", "examples": ["Mage", "Champion"]},
    5: {"cr": "8-10", "hp_range": (120, 180), "ac": 17, "attack_bonus": 9, "damage": "3d10+6", "examples": ["Young Dragon", "Vampire"]},
}


def generate_combat_stats(tier: int, is_boss: bool = False) -> dict:
    """Generate combat stats for an NPC based on difficulty tier."""
    import random

    if is_boss:
        tier_data = BOSS_TIERS.get(tier, BOSS_TIERS[1])
        hp = random.randint(tier_data["hp_range"][0], tier_data["hp_range"][1])
        return {
            "hp": hp,
            "ac": tier_data["ac"],
            "attack_bonus": tier_data["attack_bonus"],
            "damage": tier_data["damage"],
            "cr": tier_data["cr"],
        }
    else:
        tier_data = DIFFICULTY_TIERS.get(tier, DIFFICULTY_TIERS[1])
        hp = random.randint(tier_data["hp_range"][0], tier_data["hp_range"][1])
        ac = random.randint(tier_data["ac_range"][0], tier_data["ac_range"][1])
        attack = random.randint(tier_data["attack_bonus"][0], tier_data["attack_bonus"][1])
        return {
            "hp": hp,
            "ac": ac,
            "attack_bonus": attack,
            "damage": tier_data["damage"],
            "cr": tier_data["cr_range"],
        }


# =============================================================================
# LOCATION TEMPLATES BY SETTING
# =============================================================================

LOCATION_TEMPLATES = {
    "high_fantasy": {
        "settlements": [
            {"name": "Starting Village", "type": "village", "description": "A quiet farming village on the frontier"},
            {"name": "Crossroads Inn", "type": "tavern", "description": "A bustling waypoint for travelers"},
            {"name": "Market Town", "type": "town", "description": "A thriving trade center with diverse merchants"},
            {"name": "Capital City", "type": "city", "description": "A grand metropolis of culture and politics"},
            {"name": "Elven Enclave", "type": "settlement", "description": "An ancient elven community hidden in the forest"},
            {"name": "Dwarven Hold", "type": "stronghold", "description": "A fortress carved into the mountains"},
        ],
        "dungeons": [
            {"name": "Goblin Warrens", "type": "dungeon", "description": "A network of tunnels infested with goblins"},
            {"name": "Ancient Ruins", "type": "ruins", "description": "Crumbling remnants of a forgotten civilization"},
            {"name": "Dark Caverns", "type": "cave", "description": "Natural caves that descend into darkness"},
            {"name": "Necromancer's Tower", "type": "tower", "description": "A sinister spire crackling with dark energy"},
            {"name": "Dragon's Lair", "type": "lair", "description": "A volcanic cavern that serves as a dragon's home"},
            {"name": "Forgotten Temple", "type": "temple", "description": "An abandoned temple to a fallen god"},
        ],
        "wilderness": [
            {"name": "Whispering Woods", "type": "forest", "description": "An enchanted forest where the trees seem to speak"},
            {"name": "Misty Marshes", "type": "swamp", "description": "Treacherous wetlands shrouded in fog"},
            {"name": "Thunder Peaks", "type": "mountains", "description": "Towering mountains prone to storms"},
            {"name": "Golden Plains", "type": "plains", "description": "Vast grasslands stretching to the horizon"},
            {"name": "Cursed Graveyard", "type": "graveyard", "description": "An ancient burial ground with restless spirits"},
            {"name": "Fey Crossing", "type": "magical", "description": "A place where the veil to the Feywild is thin"},
        ],
    },
    "dark_fantasy": {
        "settlements": [
            {"name": "Plague Village", "type": "village", "description": "A dying village ravaged by disease"},
            {"name": "Last Light Inn", "type": "tavern", "description": "The only safe haven for miles"},
            {"name": "Fallen City", "type": "city", "description": "A once-great city now fallen to corruption"},
            {"name": "Refugee Camp", "type": "camp", "description": "A desperate collection of survivors"},
        ],
        "dungeons": [
            {"name": "Torture Chambers", "type": "dungeon", "description": "Underground cells of unspeakable horror"},
            {"name": "Corpse Pit", "type": "pit", "description": "A mass grave that has become a lair for undead"},
            {"name": "Blood Sanctum", "type": "temple", "description": "A temple dedicated to dark blood rituals"},
            {"name": "Witch's Coven", "type": "lair", "description": "A hidden meeting place for practitioners of dark arts"},
        ],
        "wilderness": [
            {"name": "Dead Forest", "type": "forest", "description": "A corrupted woodland where nothing grows"},
            {"name": "Ashen Wastes", "type": "wasteland", "description": "Barren lands scarred by magical catastrophe"},
            {"name": "Bone Fields", "type": "battlefield", "description": "Ancient battlegrounds littered with remains"},
        ],
    },
    "exploration": {
        "settlements": [
            {"name": "Frontier Outpost", "type": "outpost", "description": "A remote base for explorers and adventurers"},
            {"name": "Scholar's Haven", "type": "library", "description": "A center of knowledge and research"},
            {"name": "Port Town", "type": "port", "description": "A coastal town with ships to distant lands"},
        ],
        "dungeons": [
            {"name": "Lost Library", "type": "library", "description": "Ancient repository of forbidden knowledge"},
            {"name": "Sunken Temple", "type": "ruins", "description": "Partially submerged ruins of an ancient faith"},
            {"name": "Clockwork Vault", "type": "vault", "description": "A mechanical dungeon full of traps and puzzles"},
            {"name": "Crystal Caves", "type": "cave", "description": "Glittering caverns with magical properties"},
        ],
        "wilderness": [
            {"name": "Uncharted Jungle", "type": "jungle", "description": "Dense tropical forest hiding ancient secrets"},
            {"name": "Floating Islands", "type": "magical", "description": "Archipelago of islands suspended in the sky"},
            {"name": "Desert of Whispers", "type": "desert", "description": "Endless sands that seem to speak to travelers"},
            {"name": "Frozen North", "type": "tundra", "description": "Icy wastelands at the edge of the world"},
        ],
    },
}


def get_location_templates(setting: str, tone: str) -> dict:
    """Get location templates based on setting and tone."""
    # Map tone to template category
    template_key = "high_fantasy"  # default

    if "dark" in tone.lower() or "horror" in tone.lower() or "gritty" in tone.lower():
        template_key = "dark_fantasy"
    elif "exploration" in tone.lower() or "discovery" in tone.lower():
        template_key = "exploration"

    return LOCATION_TEMPLATES.get(template_key, LOCATION_TEMPLATES["high_fantasy"])


def generate_location_list(count: int, setting: str, tone: str) -> list:
    """Generate a list of locations for a campaign."""
    import random

    templates = get_location_templates(setting, tone)
    locations = []

    # Distribution: ~40% settlements, ~40% dungeons, ~20% wilderness
    settlement_count = max(1, int(count * 0.35))  # At least 1 settlement
    dungeon_count = max(1, int(count * 0.40))     # At least 1 dungeon
    wilderness_count = count - settlement_count - dungeon_count

    # Pick random locations from each category
    all_settlements = templates.get("settlements", [])
    all_dungeons = templates.get("dungeons", [])
    all_wilderness = templates.get("wilderness", [])

    random.shuffle(all_settlements)
    random.shuffle(all_dungeons)
    random.shuffle(all_wilderness)

    locations.extend(all_settlements[:settlement_count])
    locations.extend(all_dungeons[:dungeon_count])
    locations.extend(all_wilderness[:wilderness_count])

    # Shuffle final list
    random.shuffle(locations)

    # Add index numbers
    for i, loc in enumerate(locations):
        loc["index"] = i + 1
        loc["difficulty_tier"] = 1  # Will be calculated after route determination
        loc["is_starting"] = False
        loc["is_ending"] = False
        loc["discovered"] = False

    return locations


def calculate_difficulty_tiers(locations: list, start_index: int, end_index: int) -> list:
    """
    Calculate difficulty tiers for all locations based on their position
    relative to start and end points.

    Simple algorithm: Tier increases as you get closer to the end location.
    """
    total_locations = len(locations)
    if total_locations <= 1:
        return locations

    # Find positions
    start_pos = None
    end_pos = None

    for i, loc in enumerate(locations):
        if loc.get("index") == start_index:
            start_pos = i
            loc["is_starting"] = True
        if loc.get("index") == end_index:
            end_pos = i
            loc["is_ending"] = True

    if start_pos is None or end_pos is None:
        # Fallback: just use index order
        for i, loc in enumerate(locations):
            tier = min(5, 1 + (i * 5) // total_locations)
            loc["difficulty_tier"] = tier
        return locations

    # Calculate "distance" from start for each location
    # and map to difficulty tier
    for i, loc in enumerate(locations):
        if loc.get("is_starting"):
            loc["difficulty_tier"] = 1  # Starting location is always tier 1
        elif loc.get("is_ending"):
            loc["difficulty_tier"] = 5  # Ending location is always tier 5
        else:
            # Calculate relative position (0.0 to 1.0) between start and end
            # Using simple index-based distance for now
            relative_pos = abs(i - start_pos) / max(1, total_locations - 1)
            tier = min(5, max(1, int(relative_pos * 5) + 1))
            loc["difficulty_tier"] = tier

    return locations


# =============================================================================
# NPC GENERATION TEMPLATES
# =============================================================================

NPC_TEMPLATES_BY_LOCATION_TYPE = {
    "tavern": {
        "friendly": ["Barkeep", "Serving Wench", "Regular Patron", "Traveling Bard", "Retired Adventurer"],
        "neutral": ["Merchant", "Traveler", "Gambler", "Off-duty Guard", "Mysterious Stranger"],
        "hostile": ["Thug", "Pickpocket", "Bandit Scout", "Bounty Hunter"],
        "quest_giver": ["Desperate Farmer", "Mysterious Elder", "Frantic Messenger", "Wealthy Patron"],
    },
    "village": {
        "friendly": ["Village Elder", "Kindly Farmer", "Local Healer", "Blacksmith", "Innkeeper"],
        "neutral": ["Suspicious Villager", "Traveling Merchant", "Wandering Priest", "Hunter"],
        "hostile": ["Town Drunk", "Thief", "Bandit Informant"],
        "quest_giver": ["Village Elder", "Distraught Parent", "Local Priest"],
    },
    "town": {
        "friendly": ["Town Guard Captain", "Merchant Guild Master", "Temple Priest", "Scholar"],
        "neutral": ["Politician", "Rich Merchant", "Guild Member", "Artisan", "Street Vendor"],
        "hostile": ["Thieves' Guild Contact", "Corrupt Official", "Gang Member", "Assassin"],
        "quest_giver": ["Mayor", "Guild Master", "Temple High Priest", "Noble"],
    },
    "city": {
        "friendly": ["Noble Ally", "Influential Merchant", "Temple Archbishop", "Archmage"],
        "neutral": ["Court Noble", "Guildmaster", "Foreign Ambassador", "Street Performer"],
        "hostile": ["Crime Lord", "Corrupt Noble", "Cult Leader", "Assassin"],
        "quest_giver": ["King/Queen", "High Council Member", "Arcane Order Leader"],
    },
    "dungeon": {
        "friendly": ["Captured Prisoner", "Lost Explorer", "Reformed Cultist"],
        "neutral": ["Trapped Ghost", "Neutral Monster", "Dungeon Hermit"],
        "hostile": ["Dungeon Guardian", "Undead Sentinel", "Monster Patrol", "Trap Master"],
        "boss": ["Dungeon Lord", "Necromancer", "Beast Alpha", "Ancient Guardian"],
    },
    "forest": {
        "friendly": ["Wood Elf Scout", "Druid", "Forest Spirit", "Ranger"],
        "neutral": ["Hermit", "Lost Traveler", "Fey Creature", "Wildlife"],
        "hostile": ["Goblin Raider", "Bandit", "Corrupted Beast", "Dark Fey"],
        "quest_giver": ["Archdruid", "Forest Guardian", "Dryad Queen"],
    },
    "cave": {
        "friendly": ["Trapped Miner", "Friendly Kobold", "Cave Hermit"],
        "neutral": ["Blind Cave Creature", "Underground Merchant", "Myconid"],
        "hostile": ["Giant Spider", "Orc Warrior", "Cave Troll", "Dark Dweller"],
        "boss": ["Spider Queen", "Orc Warchief", "Cave Dragon"],
    },
    "ruins": {
        "friendly": ["Archaeological Scholar", "Spirit of the Past", "Survivor"],
        "neutral": ["Treasure Hunter", "Curious Ghost", "Neutral Construct"],
        "hostile": ["Undead Guardian", "Looter Band", "Animated Statue", "Curse Victim"],
        "boss": ["Ancient Lich", "Fallen Paladin", "Awakened Horror"],
    },
    "default": {
        "friendly": ["Helpful Local", "Fellow Traveler", "Sympathetic Soul"],
        "neutral": ["Passerby", "Local Worker", "Wanderer", "Merchant"],
        "hostile": ["Bandit", "Creature", "Hostile Local", "Monster"],
        "quest_giver": ["Mysterious Figure", "Person in Need", "Authority Figure"],
    },
}

# Generic name lists for auto-generation
NPC_FIRST_NAMES = {
    "human": ["Aldric", "Brennan", "Cora", "Dara", "Elena", "Finn", "Gwen", "Hugo", "Ivy", "Jasper",
              "Kira", "Leo", "Mira", "Nolan", "Olive", "Quinn", "Rosa", "Seth", "Tara", "Victor"],
    "elf": ["Aelindra", "Branwyn", "Caelum", "Daeris", "Elara", "Faelar", "Galadrel", "Haela", "Ithil",
            "Jhaer", "Kaelen", "Lirael", "Mythris", "Nailo", "Orion", "Phaedra", "Queleth", "Rael", "Sylra", "Theren"],
    "dwarf": ["Baldur", "Brynn", "Dolgrin", "Eberk", "Flint", "Gimbol", "Helga", "Ingram", "Kira",
              "Lothur", "Moradin", "Nura", "Orsik", "Petra", "Ragni", "Sigrid", "Thorin", "Ulfgar", "Vondal", "Wynnra"],
    "halfling": ["Bardon", "Cade", "Delia", "Eida", "Felix", "Garret", "Hanna", "Iver", "Jillian",
                 "Kip", "Lidda", "Merric", "Nedda", "Osborn", "Paela", "Roscoe", "Seraphina", "Tegan", "Verna", "Welby"],
    "generic": ["Alex", "Blake", "Casey", "Drew", "Ellis", "Finley", "Gray", "Haven", "Indigo",
                "Jordan", "Kerry", "Logan", "Morgan", "Nova", "Oakley", "Phoenix", "Quinn", "River", "Sage", "Taylor"],
}


def generate_npc_name() -> str:
    """Generate a random NPC name."""
    import random
    race = random.choice(list(NPC_FIRST_NAMES.keys()))
    return random.choice(NPC_FIRST_NAMES[race])


def get_npc_count_for_location(location_type: str) -> dict:
    """Get the recommended NPC counts for a location type."""
    if location_type in ["tavern", "inn"]:
        return {"friendly": 2, "neutral": 3, "hostile": 1, "quest_giver": 1, "general": 3}
    elif location_type in ["village"]:
        return {"friendly": 2, "neutral": 2, "hostile": 1, "quest_giver": 1, "general": 2}
    elif location_type in ["town"]:
        return {"friendly": 2, "neutral": 3, "hostile": 2, "quest_giver": 1, "general": 3}
    elif location_type in ["city"]:
        return {"friendly": 3, "neutral": 4, "hostile": 2, "quest_giver": 2, "general": 4}
    elif location_type in ["dungeon", "cave", "ruins", "tower", "lair"]:
        return {"friendly": 1, "neutral": 0, "hostile": 4, "boss": 1, "general": 0}
    elif location_type in ["forest", "swamp", "mountains", "plains"]:
        return {"friendly": 1, "neutral": 2, "hostile": 2, "quest_giver": 1, "general": 1}
    else:
        return {"friendly": 1, "neutral": 2, "hostile": 1, "quest_giver": 1, "general": 2}


def generate_npcs_for_location(location: dict, difficulty_tier: int) -> list:
    """Generate NPCs for a specific location."""
    import random

    location_type = location.get("type", "default").lower()
    location_name = location.get("name", "Unknown")

    # Get templates for this location type
    templates = NPC_TEMPLATES_BY_LOCATION_TYPE.get(location_type, NPC_TEMPLATES_BY_LOCATION_TYPE["default"])
    counts = get_npc_count_for_location(location_type)

    npcs = []

    # Generate friendly NPCs
    for _ in range(counts.get("friendly", 1)):
        role = random.choice(templates.get("friendly", ["Friendly Local"]))
        npcs.append({
            "name": generate_npc_name(),
            "role": role,
            "location": location_name,
            "relationship": "friendly",
            "npc_type": "minor",
            "difficulty_tier": difficulty_tier,
            "combat_stats": None,
            "status": "alive",
        })

    # Generate neutral NPCs
    for _ in range(counts.get("neutral", 1)):
        role = random.choice(templates.get("neutral", ["Local"]))
        npcs.append({
            "name": generate_npc_name(),
            "role": role,
            "location": location_name,
            "relationship": "neutral",
            "npc_type": "minor",
            "difficulty_tier": difficulty_tier,
            "combat_stats": None,
            "status": "alive",
        })

    # Generate hostile NPCs with combat stats
    for _ in range(counts.get("hostile", 1)):
        role = random.choice(templates.get("hostile", ["Enemy"]))
        combat_stats = generate_combat_stats(difficulty_tier, is_boss=False)
        npcs.append({
            "name": generate_npc_name(),
            "role": role,
            "location": location_name,
            "relationship": "hostile",
            "npc_type": "minor",
            "difficulty_tier": difficulty_tier,
            "combat_stats": combat_stats,
            "status": "alive",
        })

    # Generate quest giver (if applicable)
    if counts.get("quest_giver", 0) > 0:
        role = random.choice(templates.get("quest_giver", ["Quest Giver"]))
        npcs.append({
            "name": generate_npc_name(),
            "role": role,
            "location": location_name,
            "relationship": "quest_giver",
            "npc_type": "major",
            "difficulty_tier": difficulty_tier,
            "combat_stats": None,
            "status": "alive",
        })

    # Generate boss (if applicable, typically in dungeons)
    if counts.get("boss", 0) > 0:
        role = random.choice(templates.get("boss", templates.get("hostile", ["Boss"])))
        combat_stats = generate_combat_stats(difficulty_tier, is_boss=True)
        npcs.append({
            "name": generate_npc_name() + " the " + role,
            "role": "Boss - " + role,
            "location": location_name,
            "relationship": "boss",
            "npc_type": "major",
            "difficulty_tier": difficulty_tier,
            "combat_stats": combat_stats,
            "status": "alive",
        })

    # Generate general/background NPCs
    for _ in range(counts.get("general", 1)):
        role = random.choice(["Commoner", "Traveler", "Worker", "Bystander", "Local"])
        npcs.append({
            "name": generate_npc_name(),
            "role": role,
            "location": location_name,
            "relationship": "neutral",
            "npc_type": "general",
            "difficulty_tier": difficulty_tier,
            "combat_stats": None,
            "status": "alive",
        })

    return npcs


def npc_to_row(npc: dict, session_num: str = "0") -> list:
    """Convert NPC data to spreadsheet row."""
    combat_stats = npc.get("combat_stats")
    combat_json = json.dumps(combat_stats) if combat_stats else ""

    return [
        npc.get("name", ""),
        npc.get("role", ""),
        npc.get("location", ""),
        npc.get("description", ""),
        npc.get("relationship", "neutral"),
        npc.get("npc_type", "minor"),
        str(npc.get("difficulty_tier", 1)),
        combat_json,
        session_num,
        npc.get("notes", ""),
        npc.get("status", "alive"),
    ]


def location_to_row(location: dict, session_num: str = "0") -> list:
    """Convert location data to spreadsheet row."""
    connected = location.get("connected_to", [])
    npcs = location.get("npcs_present", [])

    return [
        location.get("name", ""),
        location.get("type", ""),
        location.get("description", ""),
        ", ".join(connected) if isinstance(connected, list) else connected,
        ", ".join(npcs) if isinstance(npcs, list) else npcs,
        str(location.get("index", 0)),
        str(location.get("difficulty_tier", 1)),
        "Yes" if location.get("is_starting") else "No",
        "Yes" if location.get("is_ending") else "No",
        "Yes" if location.get("discovered") else "No",
        session_num,
        location.get("notes", ""),
    ]


# =============================================================================
# UPDATED SHEET HEADERS (with new columns)
# =============================================================================

def get_campaign_sheet_headers_v2() -> dict:
    """Get the updated column headers for campaign spreadsheets with new columns."""
    return {
        "Overview": ["Field", "Value"],
        "Characters": [
            "Player Name", "Character Name", "Race", "Class", "Level", "XP",
            "Background", "Max HP", "Current HP", "Temp HP", "AC",
            "STR", "DEX", "CON", "INT", "WIS", "CHA",
            "Proficiency Bonus", "Speed",
            "Skills", "Saving Throws", "Equipment",
            "Gold", "Conditions", "Spell Slots", "Spells Known",
            "Personality Traits", "Ideal", "Bond", "Flaw", "Notes",
            "Player Number"  # NEW
        ],
        "NPCs": [
            "Name", "Role", "Location", "Description", "Relationship",
            "NPC Type", "Difficulty Tier", "Combat Stats",  # NEW columns
            "First Met (Session)", "Notes", "Status"
        ],
        "Locations": [
            "Name", "Type", "Description", "Connected To", "NPCs Present",
            "Location Index", "Difficulty Tier", "Is Starting", "Is Ending",  # NEW columns
            "Discovered", "First Visited (Session)", "Notes"
        ],
        "Items": [
            "Name", "Type", "Description", "Owner",
            "Is Starting Gear",  # NEW
            "Acquired (Session)", "Notes"
        ],
        "Combat Log": [
            "Session", "Encounter Name", "Enemies", "Outcome",
            "XP Awarded", "Loot", "Notes", "Timestamp"
        ],
        "Session History": [
            "Session #", "Date", "Summary", "Key Events",
            "NPCs Met", "Locations Visited", "XP Earned", "Next Session Hook"
        ],
        "Event Log": [
            "Session", "Event Type", "Round", "Actor", "Summary",
            "Location", "NPCs Involved", "Damage", "Healing", "Outcome", "Timestamp"
        ],
        "Quick Reference": [
            "Field", "Value"  # Simple key-value for quick reference tab
        ],
    }


def get_overview_initial_data_v2(
    campaign_name: str,
    setting: str,
    tone: str,
    starting_level: int,
    campaign_size: str,
    total_locations: int
) -> list:
    """Get initial Overview sheet data with new fields."""
    return [
        ["Campaign Name", campaign_name],
        ["Setting", setting or "Fantasy"],
        ["Tone", tone or "heroic"],
        ["Starting Level", str(starting_level)],
        ["Campaign Size", campaign_size],
        ["Total Locations", str(total_locations)],
        ["Campaign Phase", "world_building"],
        ["Current Date (In-Game)", "Day 1"],
        ["Current Location", "TBD"],
        ["Starting Location", "TBD"],
        ["Ending Location", "TBD"],
        ["Party Gold", "0"],
        ["Story Flags", ""],
        ["Session Count", "0"],
        ["Last Played", "Never"],
        ["Active Combat", "No"],
        ["Combat Initiative Order", ""],
    ]


# =============================================================================
# COMBAT STATE MIGRATION HELPER
# =============================================================================

def parse_combat_state(combat_data: str) -> dict:
    """
    Parse combat state from Overview sheet, handling both old and new formats.

    Old format (flat array):
        [{"name": "Aldric", "initiative": 18, "hp": 25, ...}, ...]

    New format (object with tracking):
        {
            "round": 1,
            "current_turn_index": 0,
            "encounter_name": "Combat",
            "combatants": [...]
        }

    Returns new format dict, migrating old format if necessary.
    """
    if not combat_data or combat_data.strip() == "":
        return None

    try:
        data = json.loads(combat_data)
    except json.JSONDecodeError:
        return None

    # Check if it's already new format (has 'combatants' key)
    if isinstance(data, dict) and "combatants" in data:
        # Ensure all required fields exist
        return {
            "round": data.get("round", 1),
            "current_turn_index": data.get("current_turn_index", 0),
            "encounter_name": data.get("encounter_name", "Combat"),
            "combatants": data.get("combatants", [])
        }

    # Old format: flat array of combatants
    if isinstance(data, list):
        # Migrate to new format
        return {
            "round": 1,
            "current_turn_index": 0,
            "encounter_name": "Combat",
            "combatants": data
        }

    return None


def combat_state_to_json(combat_state: dict) -> str:
    """Convert combat state dict to JSON string for storage."""
    return json.dumps(combat_state)


def event_to_row(
    session_num: str,
    event_type: str,
    actor: str,
    summary: str,
    location: str = "",
    npcs_involved: list = None,
    damage: int = 0,
    healing: int = 0,
    outcome: str = "",
    round_num: int = None
) -> list:
    """Convert event data to spreadsheet row for Event Log."""
    from datetime import datetime

    return [
        session_num,
        event_type,
        str(round_num) if round_num is not None else "",
        actor,
        summary,
        location,
        ", ".join(npcs_involved) if npcs_involved else "",
        str(damage) if damage else "",
        str(healing) if healing else "",
        outcome,
        datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    ]
