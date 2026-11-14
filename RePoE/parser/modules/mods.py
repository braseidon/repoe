from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple, Union

from PyPoE.poe.file.dat import DatRecord
from PyPoE.poe.file.translations import install_data_dependant_quantifiers, TranslationFileCache
from PyPoE.poe.poe1constants import MOD_DOMAIN
from PyPoE.poe.sim.mods import get_translation_file_from_domain

from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_any_json, write_json


def _convert_stats(
    stats: Union[
        List[List[Optional[int]]],
        List[List[Union[DatRecord, int]]],
        List[Union[List[Optional[int]], List[Union[DatRecord, int]]]],
    ],
    exclude_ids: FrozenSet[str] = frozenset(),
) -> List[Dict[str, Any]]:
    # 'Stats' is a virtual field that is an array of ['Stat1', ..., 'Stat5'].
    # 'Stat{i}' is a virtual field that is an array of ['StatsKey{i}', 'Stat{i}Min', 'Stat{i}Max']
    r = []
    for stat in stats:
        if isinstance(stat[0], DatRecord):
            stat_id = stat[0]["Id"]
            if stat_id in exclude_ids:
                continue
            r.append({"id": stat_id, "min": stat[1], "max": stat[2]})
    return r


def _get_buff_template_stat_ids(mod: DatRecord) -> Set[str]:
    # PoE's Mods.dat64 duplicates a buff's mechanical stats (e.g. -15% PDR for
    # Crushed) into the mod's own Stats list so the engine applies them when
    # the display-flag stat (e.g. local_display_self_crushed) fires. In-game
    # and PoB suppress these from the displayed text — only the flag line
    # shows, with its reminder_text.
    ids: Set[str] = set()
    buff_template = mod["BuffTemplate"]
    if buff_template is None:
        return ids
    buff_def = buff_template["BuffDefinitionsKey"]
    if buff_def is None:
        return ids
    for stat in buff_def["StatsKeys"]:
        ids.add(stat["Id"])
    for stat in buff_def["Binary_StatsKeys"]:
        ids.add(stat["Id"])
    return ids


def _convert_buff_template(mod: DatRecord) -> Optional[Dict[str, Any]]:
    buff_template = mod["BuffTemplate"]
    if buff_template is None:
        return None
    result: Dict[str, Any] = {"id": buff_template["Id"]}
    buff_def = buff_template["BuffDefinitionsKey"]
    if buff_def is not None:
        result["buff"] = buff_def["Id"]
    if buff_template["AuraRadius"]:
        result["aura_radius_metres"] = buff_template["AuraRadius"] / 10
    return result


def _translate_mod(
    mod: DatRecord,
    translation_cache: TranslationFileCache,
    exclude_ids: FrozenSet[str] = frozenset(),
    lang: str = "English",
) -> Tuple[List[str], List[str]]:
    constants = mod.parent.constants
    ids: List[str] = []
    values: List[List[int]] = []
    for i in constants.MOD_STATS_RANGE:
        stat = mod["StatsKey%s" % i]
        if stat is None:
            continue
        stat_id = stat["Id"]
        if stat_id in exclude_ids:
            continue
        ids.append(stat_id)
        values.append([mod["Stat%sMin" % i], mod["Stat%sMax" % i]])
    tf_name = get_translation_file_from_domain(mod["Domain"], constants)
    result = translation_cache[tf_name].get_translation(ids, values, full_result=True, lang=lang)
    return result.lines, result.missing_ids


def _convert_spawn_weights(spawn_weights: zip) -> List[Dict[str, Any]]:
    # 'SpawnWeight' is a virtual field that is a zipped tuple of
    # ('SpawnWeight_TagsKeys', 'SpawnWeight_Values')
    r = []
    for tag, weight in spawn_weights:
        r.append({"tag": tag["Id"], "weight": weight})
    return r


def _convert_generation_weights(generation_weights: zip) -> List[Dict[str, Any]]:
    # 'GenerationWeight' is a virtual field that is a tuple of
    # ('GenerationWeight_TagsKeys', 'GenerationWeight_Values')
    r = []
    for tag, weight in generation_weights:
        r.append({"tag": tag["Id"], "weight": weight})
    return r


def _convert_granted_effects(granted_effects_per_level: List[DatRecord]) -> List[Dict[str, Any]]:
    if granted_effects_per_level is None:
        return {}
    # These two identify a row in GrantedEffectsPerLevel.dat64
    return [
        {"granted_effect_id": gepl["GrantedEffect"]["Id"], "level": gepl["Level"]} for gepl in granted_effects_per_level
    ]


class GrantedEffectLines:
    """The line the client writes itself for a mod that grants a skill or a support.

    Since 3.30 such a mod has no stat description for it: the display stat stays on the mod
    with a value of 0 (a few keep their value and only lost the description) and the client
    fills a ClientStrings template with the granted effect's name and level.
    """

    DISPLAY_STAT_PREFIX = "local_display_"

    # The Harbinger skills print without a level ("Grants Summon Harbinger of Time"). Nothing
    # in the effect's data marks that, so the mods are found by their display stat.
    NO_LEVEL_STATS = frozenset({"local_display_summon_harbinger_x_on_equip"})

    # Before 3.30 these stats' descriptions had no level either. What the client prints for
    # them now is not known, so their mods get no line rather than a guessed one.
    UNKNOWN_FORM_STATS = frozenset(
        {
            "local_display_socketed_gems_have_iron_will",
            "local_display_grants_skill_call_of_steel",
        }
    )

    def __init__(self, relational_reader) -> None:
        strings = {
            row["Id"]: row["Text"]
            for row in relational_reader["ClientStrings.dat64"]
            if row["Id"] in ("ModGrantsEffect", "ModGrantsEffectWithLevel", "ModGrantsSupportEffectWithLevel")
        }
        self.skill_template: str = strings["ModGrantsEffectWithLevel"]
        self.skill_template_no_level: str = strings["ModGrantsEffect"]
        self.support_template: str = strings["ModGrantsSupportEffectWithLevel"]
        # a support prints its gem's name; a support with no gem has no name to print
        self.support_names: Dict[str, str] = {}
        # a gem's first effect names it before any gem that only carries the effect as its second
        for column in ("GrantedEffect", "GrantedEffect2"):
            for gem in relational_reader["SkillGems.dat64"]:
                for gem_effect in gem["GemEffects"]:
                    granted_effect = gem_effect[column]
                    if granted_effect is None or not granted_effect["IsSupport"]:
                        continue
                    name = gem_effect["SupportName"] or gem_effect["Name"] or gem["BaseItemTypesKey"]["Name"]
                    if name:
                        self.support_names.setdefault(granted_effect["Id"], name)

    def _display_stats(self, mod: DatRecord, undescribed_ids: List[str]) -> Tuple[List[str], bool]:
        """The mod's display stats that have no description, and whether one is its first stat."""
        ids = []
        leads = False
        first = True
        for i in mod.parent.constants.MOD_STATS_RANGE:
            stat = mod["StatsKey%s" % i]
            if stat is None:
                continue
            if stat["Id"].startswith(self.DISPLAY_STAT_PREFIX):
                zeroed = mod["Stat%sMin" % i] == 0 and mod["Stat%sMax" % i] == 0
                if zeroed or stat["Id"] in undescribed_ids:
                    ids.append(stat["Id"])
                    leads = leads or first
            first = False
        return ids, leads

    def add_line(self, mod: DatRecord, lines: List[str], undescribed_ids: List[str]) -> Tuple[List[str], Optional[str]]:
        """The mod's lines with the client-written one in place, and that line by itself.

        The line sits where the display stat sits among the mod's stats: before the other
        lines when the stat is the mod's first, after them otherwise.
        """
        granted = mod["GrantedEffectsPerLevelKeys"]
        if not granted:
            return lines, None
        display_stats, leads = self._display_stats(mod, undescribed_ids)
        line = self._line(granted, display_stats)
        if line is None:
            return lines, None
        return ([line] + lines if leads else lines + [line]), line

    def _line(self, granted: List[DatRecord], display_stats: List[str]) -> Optional[str]:
        # A mod with no display stat is not covered: some print the line (a 3.30 unique with
        # no stats at all), others are hidden companions of a mod that words the skill itself.
        if not display_stats or any(stat_id in self.UNKNOWN_FORM_STATS for stat_id in display_stats):
            return None
        # only the first effect prints: a second one is its hidden triggered companion
        per_level = granted[0]
        granted_effect = per_level["GrantedEffect"]
        if granted_effect["IsSupport"]:
            name = self.support_names.get(granted_effect["Id"])
            template = self.support_template
        else:
            active_skill = granted_effect["ActiveSkill"]
            name = active_skill["DisplayedName"] if active_skill else None
            template = self.skill_template
            if any(stat_id in self.NO_LEVEL_STATS for stat_id in display_stats):
                template = self.skill_template_no_level
        if not name:
            return None
        return template.format(name, per_level["Level"])


def _convert_tags_keys(tags_keys: List[DatRecord]) -> List[str]:
    r = []
    for tag in tags_keys:
        r.append(tag["Id"])
    return r


def _to_slim(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a raw mod object to slim format for cache consumption.

    Changes: spawn_weights/generation_weights flattened to {tag: weight},
    empty arrays omitted, is_essence_only omitted when false,
    implicit_tags renamed to tags.
    """
    slim = {
        "required_level": obj["required_level"],
        "stats": obj["stats"],
        "domain": obj["domain"],
        "name": obj["name"],
        "type": obj["type"],
        "generation_type": obj["generation_type"],
        "groups": obj["groups"],
        "tags": obj["implicit_tags"],
        "spawn_weights": {sw["tag"]: sw["weight"] for sw in obj["spawn_weights"]},
    }
    if obj["text"] is not None:
        slim["text"] = obj["text"]
    if obj["generation_weights"]:
        slim["generation_weights"] = {gw["tag"]: gw["weight"] for gw in obj["generation_weights"]}
    if obj["grants_effects"]:
        slim["grants_effects"] = obj["grants_effects"]
    if obj["is_essence_only"]:
        slim["is_essence_only"] = True
    if obj["adds_tags"]:
        slim["adds_tags"] = obj["adds_tags"]
    if obj["crafting_item_class_restrictions"]:
        slim["crafting_item_class_restrictions"] = obj["crafting_item_class_restrictions"]
    if obj.get("buff_template"):
        slim["buff_template"] = obj["buff_template"]
    if obj.get("granted_effect_text"):
        slim["granted_effect_text"] = obj["granted_effect_text"]
    return slim


class mods(Parser_Module):
    def write(self) -> None:
        root = {}
        translation_cache = self.get_cache(TranslationFileCache)
        install_data_dependant_quantifiers(self.relational_reader)
        granted_effect_lines = GrantedEffectLines(self.relational_reader)
        for mod in self.relational_reader["Mods.dat64"]:
            domain = MOD_DOMAIN_FIX.get(mod["Id"], mod["Domain"])

            buff_template_stat_ids = frozenset(_get_buff_template_stat_ids(mod))

            try:
                lines, undescribed_ids = _translate_mod(
                    mod, translation_cache, exclude_ids=buff_template_stat_ids, lang=self.language
                )
            except Exception as e:
                print("could not get text for mod", mod["Id"], e)
                lines, undescribed_ids = [], []

            lines, granted_effect_text = granted_effect_lines.add_line(mod, lines, undescribed_ids)

            obj = {
                "required_level": mod["Level"],
                "stats": _convert_stats(mod["Stats"], exclude_ids=buff_template_stat_ids),
                "text": "\n".join(lines) if lines else None,
                "domain": domain.name.lower(),
                "name": mod["Name"],
                "type": mod["ModTypeKey"]["Name"],
                "generation_type": mod["GenerationType"].name.lower() if mod["GenerationType"] else "<unknown>",
                "groups": [family["Id"] for family in mod["Families"]],
                "spawn_weights": _convert_spawn_weights(mod["SpawnWeight"]),
                "generation_weights": _convert_generation_weights(mod["GenerationWeight"]),
                "grants_effects": _convert_granted_effects(mod["GrantedEffectsPerLevelKeys"]),
                "is_essence_only": mod["IsEssenceOnlyModifier"] > 0,
                "adds_tags": _convert_tags_keys(mod["TagsKeys"]),
                "implicit_tags": _convert_tags_keys(mod["ImplicitTagsKeys"]),
                "crafting_item_class_restrictions": [
                    ic["Id"] for ic in mod["CraftingItemClassRestrictions"]
                ],
                "buff_template": _convert_buff_template(mod),
                "granted_effect_text": granted_effect_text,
            }
            if mod["Id"] in root:
                print("Duplicate mod id:", mod["Id"])
            else:
                root[mod["Id"]] = obj

        write_json(root, self.data_path, "mods")

        # Slim output for cache commands: flattened weights, omit empties, tags renamed
        slim_root = {k: _to_slim(v) for k, v in root.items()}
        write_any_json(slim_root, self.data_path, "mods_slim")


# a few unique item mods have the wrong mod domain so they wouldn't be added to the file without this
MOD_DOMAIN_FIX = {
    "AreaDamageUniqueBodyDexInt1": MOD_DOMAIN.ITEM,
    "ElementalResistancePerEnduranceChargeDescentShield1": MOD_DOMAIN.ITEM,
    "LifeGainOnEndurangeChargeConsumptionUniqueBodyStrInt6": MOD_DOMAIN.ITEM,
    "ReturningProjectilesUniqueDescentBow1": MOD_DOMAIN.ITEM,
}


if __name__ == "__main__":
    call_with_default_args(mods)
