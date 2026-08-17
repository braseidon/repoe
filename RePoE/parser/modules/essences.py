from typing import Dict, List, Optional

from PyPoE.poe.file.dat import DatRecord
from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_any_json, write_json

# ClientStrings.dat64 prefix for the human-readable essence slot labels. Covers both the
# exact item classes in `mods` and the grouped slots in `display_mods`, plus the "Other {0}"
# template the game composes with a group label to render lines like "Other Armour".
ESSENCE_CATEGORY_PREFIX = "EssenceCategory"
ESSENCE_MOD_LEVEL_RESTRICTION_ID = "EssenceModLevelRestriction"

# The item-facing Display_*_ModsKey groups on Essences.dat64, in column order.
# Display_Monster_ModsKey is excluded: it buffs the essence monster, not an item.
DISPLAY_GROUPS = (
    "Wand",
    "Bow",
    "Quiver",
    "Amulet",
    "Ring",
    "Belt",
    "Gloves",
    "Boots",
    "BodyArmour",
    "Helmet",
    "Shield",
    "Weapon",
    "MeleeWeapon",
    "OneHandWeapon",
    "TwoHandWeapon",
    "TwoHandMeleeWeapon",
    "Armour",
    "RangedWeapon",
    "Jewellery",
    "Items",
)


def _convert_display_mods(row: DatRecord) -> Dict[str, str]:
    return {
        group: row["Display_" + group + "_ModsKey"]["Id"]
        for group in DISPLAY_GROUPS
        if row["Display_" + group + "_ModsKey"]
    }


# ---------------------------------------------------------------------------
# In-game essence tooltip layout ("display_blocks").
#
# The client renders the Display_*_ModsKey groups as labelled lines in three
# blocks (weapon / armour / jewellery) plus a trailing Items line, separated by
# blank lines, folding a group into its nearest ancestor when both carry the same
# mod. Nothing in Essences.dat64, EssenceType.dat64, EssenceStashTabLayout.dat64
# or ClientStrings.dat64 encodes that hierarchy - the eleven unnamed ref columns
# on Essences.dat64 are empty in every row - so the parent map and block order
# below are hand-maintained. They reproduce GGG's own render (the `explicitMods`
# lines the stash API returns for essences) for 104/104 essences held in a
# stash tab at 3.29.3; Essence of Desolation (removed 3.28.0l) and Remnant of
# Corruption (no display mods) are the two unverified rows.
#
# Rules, in order, per group key present on the row:
#   1. fold   - skip the line when its mod equals the nearest ancestor's mod
#               (walking past ancestors that carry no mod).
#   2. label  - EssenceCategory<Key>; becomes EssenceCategoryOther ("Other {0}")
#               when any descendant of the key already printed a line.
#   3. blocks - lines are grouped by DISPLAY_BLOCKS; a blank line separates
#               non-empty blocks. Quiver prints inside the weapon block but hangs
#               off Items (a bare "Weapon:" line follows a "Quiver:" line, never
#               "Other Weapon:").
#
# Data-pinned edges: Quiver->Items, Wand->OneHandWeapon, every leaf->Armour /
# ->Jewellery, and every top group ->Items. The Bow / TwoHandMeleeWeapon /
# MeleeWeapon / RangedWeapon parents are semantic choices no current essence
# exercises (no row sets both ends of those edges); the two candidate "Other"
# rules (descendant printed vs descendant non-null) also agree on every row.
# ---------------------------------------------------------------------------
DISPLAY_PARENT: Dict[str, Optional[str]] = {
    "Wand": "OneHandWeapon",
    "Bow": "TwoHandWeapon",
    "Quiver": "Items",
    "MeleeWeapon": "Weapon",
    "OneHandWeapon": "Weapon",
    "TwoHandWeapon": "Weapon",
    "TwoHandMeleeWeapon": "TwoHandWeapon",
    "RangedWeapon": "Weapon",
    "Weapon": "Items",
    "Gloves": "Armour",
    "Boots": "Armour",
    "BodyArmour": "Armour",
    "Helmet": "Armour",
    "Shield": "Armour",
    "Armour": "Items",
    "Amulet": "Jewellery",
    "Ring": "Jewellery",
    "Belt": "Jewellery",
    "Jewellery": "Items",
    "Items": None,
}

DISPLAY_BLOCKS: List[List[str]] = [
    [
        "Wand",
        "Bow",
        "Quiver",
        "MeleeWeapon",
        "OneHandWeapon",
        "TwoHandWeapon",
        "TwoHandMeleeWeapon",
        "RangedWeapon",
        "Weapon",
    ],
    ["Gloves", "Boots", "BodyArmour", "Helmet", "Shield", "Armour"],
    ["Amulet", "Ring", "Belt", "Jewellery"],
    ["Items"],
]

# Every group appears in exactly one block, and the parent map covers every group.
assert sorted(k for block in DISPLAY_BLOCKS for k in block) == sorted(DISPLAY_GROUPS)
assert set(DISPLAY_PARENT) == set(DISPLAY_GROUPS)


def _nearest_ancestor_mod(display_mods: Dict[str, str], key: str) -> Optional[str]:
    parent = DISPLAY_PARENT[key]
    while parent is not None:
        if parent in display_mods:
            return display_mods[parent]
        parent = DISPLAY_PARENT[parent]
    return None


def _is_descendant(key: str, ancestor: str) -> bool:
    parent = DISPLAY_PARENT[key]
    while parent is not None:
        if parent == ancestor:
            return True
        parent = DISPLAY_PARENT[parent]
    return False


def _convert_display_blocks(display_mods: Dict[str, str], categories: Dict[str, str]) -> List[List[Dict[str, str]]]:
    printed: List[str] = []
    blocks: List[List[Dict[str, str]]] = []
    for block_keys in DISPLAY_BLOCKS:
        lines: List[Dict[str, str]] = []
        for key in block_keys:
            mod_id = display_mods.get(key)
            if mod_id is None or mod_id == _nearest_ancestor_mod(display_mods, key):
                continue
            label = categories[key]
            if any(_is_descendant(done, key) for done in printed):
                label = categories["Other"].replace("{0}", label)
            lines.append({"category": key, "label": label, "mod": mod_id})
            printed.append(key)
        if lines:
            blocks.append(lines)
    return blocks


def _convert_mods(row: DatRecord) -> Dict[str, str]:
    class_to_key = {
        "Amulet": "Amulet_ModsKey",
        "Belt": "Belt_ModsKey",
        "Body Armour": "BodyArmour_ModsKey",
        "Boots": "Boots_ModsKey",
        "Bow": "Bow_ModsKey",
        "Claw": "Claw_ModsKey",
        "Dagger": "Dagger_ModsKey",
        "Gloves": "Gloves_ModsKey",
        "Helmet": "Helmet_ModsKey",
        "One Hand Axe": "OneHandAxe_ModsKey",
        "One Hand Mace": "OneHandMace_ModsKey",
        "One Hand Sword": "OneHandSword_ModsKey",
        "Quiver": "Display_Quiver_ModsKey",
        "Ring": "Ring_ModsKey",
        "Sceptre": "Sceptre_ModsKey",
        "Shield": "Shield_ModsKey",
        "Staff": "Staff_ModsKey",
        "Thrusting One Hand Sword": "OneHandThrustingSword_ModsKey",
        "Two Hand Axe": "TwoHandAxe_ModsKey",
        "Two Hand Mace": "TwoHandMace_ModsKey",
        "Two Hand Sword": "TwoHandSword_ModsKey",
        "Wand": "Wand_ModsKey",
    }
    return {item_class: row[key]["Id"] for item_class, key in class_to_key.items() if row[key]}


class essences(Parser_Module):
    def write(self) -> None:
        categories = {
            row["Id"].removeprefix(ESSENCE_CATEGORY_PREFIX): row["Text"]
            for row in self.relational_reader["ClientStrings.dat64"]
            if row["Id"].startswith(ESSENCE_CATEGORY_PREFIX)
        }
        # "Properties restricted to level {0} and below" - the header line the tooltip
        # prints above the display blocks when ItemLevelRestriction is set.
        level_restriction_template = self.relational_reader["ClientStrings.dat64"].index["Id"][
            ESSENCE_MOD_LEVEL_RESTRICTION_ID
        ]["Text"]

        essences = {}
        for row in self.relational_reader["Essences.dat64"]:
            display_mods = _convert_display_mods(row)
            level_restriction = row["ItemLevelRestriction"] if row["ItemLevelRestriction"] > 0 else None
            essences[row["BaseItemTypesKey"]["Id"]] = {
                "name": row["BaseItemTypesKey"]["Name"],
                "spawn_level_min": (row["DropLevel"] or [0])[0],
                "level": row["Level"],
                "item_level_restriction": level_restriction,
                "level_restriction_text": (
                    level_restriction_template.replace("{0}", str(level_restriction))
                    if level_restriction is not None
                    else None
                ),
                "type": {
                    "tier": row["EssenceTypeKey"]["EssenceType"],
                    "is_corruption_only": row["EssenceTypeKey"]["IsCorruptedEssence"],
                },
                "mods": _convert_mods(row),
                "display_mods": display_mods,
                "display_blocks": _convert_display_blocks(display_mods, categories),
            }
        write_json(essences, self.data_path, "essences")

        write_any_json(categories, self.data_path, "essence_categories")


if __name__ == "__main__":
    call_with_default_args(essences)
