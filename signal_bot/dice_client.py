"""
Dice rolling client for D&D and other tabletop games.

Supports standard dice notation with modifiers, advantage/disadvantage,
drop lowest/highest, and other common mechanics.

Uses cryptographically secure randomness for trust.
"""

import re
import secrets
from typing import Optional


def roll_die(sides: int) -> int:
    """Roll a single die with the given number of sides using secure randomness."""
    if sides < 1:
        raise ValueError(f"Invalid die size: d{sides}")
    return secrets.randbelow(sides) + 1


def parse_and_roll(notation: str, reason: Optional[str] = None) -> dict:
    """
    Parse dice notation and roll the dice.

    Supported formats:
    - "1d20" - Roll one 20-sided die
    - "2d6+3" - Roll 2d6 and add 3
    - "4d6-2" - Roll 4d6 and subtract 2
    - "1d20 advantage" or "1d20 adv" - Roll with advantage
    - "1d20 disadvantage" or "1d20 dis" - Roll with disadvantage
    - "4d6 drop lowest" or "4d6 dl" - Drop the lowest die
    - "4d6 drop highest" or "4d6 dh" - Drop the highest die
    - "2d20 keep highest" or "2d20 kh" - Keep only the highest
    - "2d20 keep lowest" or "2d20 kl" - Keep only the lowest
    - "d20" - Shorthand for 1d20
    - "d%" or "1d%" - Percentile (1d100)

    Args:
        notation: Dice notation string
        reason: Optional label for the roll (e.g., "attack roll", "saving throw")

    Returns:
        dict with rolls, modifier, total, and metadata
    """
    original_notation = notation.strip()
    notation = notation.lower().strip()

    # Check for special modifiers
    advantage = False
    disadvantage = False
    drop_lowest = 0
    drop_highest = 0
    keep_highest = 0
    keep_lowest = 0

    # Parse special modifiers (must be done before main parsing)
    if " advantage" in notation or " adv" in notation:
        advantage = True
        notation = re.sub(r'\s+(advantage|adv)\b', '', notation)
    elif " disadvantage" in notation or " dis" in notation:
        disadvantage = True
        notation = re.sub(r'\s+(disadvantage|dis)\b', '', notation)

    # Drop/keep modifiers
    drop_match = re.search(r'\s+drop\s+(lowest|highest)(?:\s+(\d+))?', notation)
    if drop_match:
        if drop_match.group(1) == 'lowest':
            drop_lowest = int(drop_match.group(2)) if drop_match.group(2) else 1
        else:
            drop_highest = int(drop_match.group(2)) if drop_match.group(2) else 1
        notation = notation[:drop_match.start()]

    # Shorthand: dl = drop lowest, dh = drop highest
    dl_match = re.search(r'\s+dl(\d*)\b', notation)
    if dl_match:
        drop_lowest = int(dl_match.group(1)) if dl_match.group(1) else 1
        notation = notation[:dl_match.start()]

    dh_match = re.search(r'\s+dh(\d*)\b', notation)
    if dh_match:
        drop_highest = int(dh_match.group(1)) if dh_match.group(1) else 1
        notation = notation[:dh_match.start()]

    # Keep modifiers
    keep_match = re.search(r'\s+keep\s+(highest|lowest)(?:\s+(\d+))?', notation)
    if keep_match:
        if keep_match.group(1) == 'highest':
            keep_highest = int(keep_match.group(2)) if keep_match.group(2) else 1
        else:
            keep_lowest = int(keep_match.group(2)) if keep_match.group(2) else 1
        notation = notation[:keep_match.start()]

    # Shorthand: kh = keep highest, kl = keep lowest
    kh_match = re.search(r'\s+kh(\d*)\b', notation)
    if kh_match:
        keep_highest = int(kh_match.group(1)) if kh_match.group(1) else 1
        notation = notation[:kh_match.start()]

    kl_match = re.search(r'\s+kl(\d*)\b', notation)
    if kl_match:
        keep_lowest = int(kl_match.group(1)) if kl_match.group(1) else 1
        notation = notation[:kl_match.start()]

    notation = notation.strip()

    # Handle percentile dice
    notation = notation.replace('d%', 'd100')

    # Parse the core dice notation: NdS+M or NdS-M
    # Handle missing count (e.g., "d20" -> "1d20")
    if notation.startswith('d'):
        notation = '1' + notation

    # Main pattern: NdS with optional +/- modifier
    pattern = r'^(\d+)d(\d+)(?:([+-])(\d+))?$'
    match = re.match(pattern, notation)

    if not match:
        raise ValueError(f"Invalid dice notation: {original_notation}")

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier_sign = match.group(3)
    modifier_value = int(match.group(4)) if match.group(4) else 0

    if modifier_sign == '-':
        modifier_value = -modifier_value

    # Validate
    if count < 1 or count > 100:
        raise ValueError(f"Invalid dice count: {count} (must be 1-100)")
    if sides < 1 or sides > 1000:
        raise ValueError(f"Invalid die size: d{sides} (must be d1-d1000)")

    # Handle advantage/disadvantage (override count to 2 for d20)
    if advantage or disadvantage:
        if count == 1 and sides == 20:
            count = 2
            if advantage:
                keep_highest = 1
            else:
                keep_lowest = 1
        else:
            # For non-d20, just note it but don't change behavior
            pass

    # Roll the dice
    rolls = [roll_die(sides) for _ in range(count)]
    original_rolls = rolls.copy()

    # Apply drop/keep logic
    dropped = []
    kept = rolls.copy()

    if drop_lowest > 0:
        kept_sorted = sorted(kept)
        dropped = kept_sorted[:drop_lowest]
        kept = kept_sorted[drop_lowest:]
    elif drop_highest > 0:
        kept_sorted = sorted(kept, reverse=True)
        dropped = kept_sorted[:drop_highest]
        kept = kept_sorted[drop_highest:]
    elif keep_highest > 0:
        kept_sorted = sorted(kept, reverse=True)
        kept = kept_sorted[:keep_highest]
        dropped = kept_sorted[keep_highest:]
    elif keep_lowest > 0:
        kept_sorted = sorted(kept)
        kept = kept_sorted[:keep_lowest]
        dropped = kept_sorted[keep_lowest:]

    # Calculate total
    dice_total = sum(kept)
    total = dice_total + modifier_value

    # Check for critical/fumble on d20 rolls
    critical = False
    fumble = False
    if sides == 20 and len(kept) == 1:
        if kept[0] == 20:
            critical = True
        elif kept[0] == 1:
            fumble = True

    # Build result
    result = {
        "notation": original_notation,
        "rolls": original_rolls,
        "kept": kept,
        "dropped": dropped,
        "modifier": modifier_value,
        "dice_total": dice_total,
        "total": total,
        "critical": critical,
        "fumble": fumble,
    }

    if reason:
        result["reason"] = reason

    if advantage:
        result["advantage"] = True
    if disadvantage:
        result["disadvantage"] = True

    return result


def format_roll_result(result: dict) -> str:
    """Format a roll result as a readable string."""
    parts = []

    # Header with reason if provided
    if result.get("reason"):
        parts.append(f"**{result['reason']}**")

    # Notation
    parts.append(f"Rolling {result['notation']}")

    # Show the rolls
    if result.get("advantage"):
        parts.append("(with advantage)")
    elif result.get("disadvantage"):
        parts.append("(with disadvantage)")

    # Individual dice
    rolls_str = ", ".join(str(r) for r in result["rolls"])
    parts.append(f"Rolls: [{rolls_str}]")

    # Show dropped dice if any
    if result["dropped"]:
        dropped_str = ", ".join(str(r) for r in result["dropped"])
        parts.append(f"Dropped: [{dropped_str}]")
        kept_str = ", ".join(str(r) for r in result["kept"])
        parts.append(f"Kept: [{kept_str}]")

    # Show calculation
    if result["modifier"] != 0:
        sign = "+" if result["modifier"] > 0 else ""
        parts.append(f"Dice total: {result['dice_total']} {sign}{result['modifier']} = **{result['total']}**")
    else:
        parts.append(f"Total: **{result['total']}**")

    # Critical/fumble
    if result["critical"]:
        parts.append("NATURAL 20! CRITICAL!")
    elif result["fumble"]:
        parts.append("Natural 1... fumble!")

    return "\n".join(parts)


def roll_dice(notation: str, reason: Optional[str] = None) -> dict:
    """
    Main entry point for dice rolling.

    Args:
        notation: Dice notation (e.g., "1d20+5", "4d6 drop lowest", "2d6 advantage")
        reason: Optional label for the roll

    Returns:
        dict with roll results and formatted output
    """
    try:
        result = parse_and_roll(notation, reason)
        result["formatted"] = format_roll_result(result)
        result["success"] = True
        return result
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "notation": notation,
        }


# Quick test
if __name__ == "__main__":
    test_cases = [
        "1d20",
        "2d6+3",
        "4d6 drop lowest",
        "1d20 advantage",
        "1d20 disadvantage",
        "d20+5",
        "1d%",
        "8d6",
        "2d20 keep highest",
    ]

    for notation in test_cases:
        print(f"\n{'='*40}")
        result = roll_dice(notation, "test roll")
        if result["success"]:
            print(result["formatted"])
        else:
            print(f"Error: {result['error']}")
