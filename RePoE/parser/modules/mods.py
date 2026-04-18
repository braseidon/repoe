from typing import Any, Dict, FrozenSet, List, Optional, Set, Union

from PyPoE.poe.poe1constants import MOD_DOMAIN
from PyPoE.poe.file.dat import DatRecord
from PyPoE.poe.file.translations import install_data_dependant_quantifiers, TranslationFileCache
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
) -> List[str]:
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
    return translation_cache[tf_name].get_translation(
        ids, values, full_result=True, lang=lang
    ).lines


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
    if obj.get("buff_template"):
        slim["buff_template"] = obj["buff_template"]
    return slim


class mods(Parser_Module):
    def write(self) -> None:
        root = {}
        translation_cache = self.get_cache(TranslationFileCache)
        install_data_dependant_quantifiers(self.relational_reader)
        for mod in self.relational_reader["Mods.dat64"]:
            domain = MOD_DOMAIN_FIX.get(mod["Id"], mod["Domain"])

            buff_template_stat_ids = frozenset(_get_buff_template_stat_ids(mod))

            try:
                lines = _translate_mod(
                    mod, translation_cache, exclude_ids=buff_template_stat_ids, lang=self.language
                )
            except Exception as e:
                print("could not get text for mod", mod["Id"], e)
                lines = []

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
                "buff_template": _convert_buff_template(mod),
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
