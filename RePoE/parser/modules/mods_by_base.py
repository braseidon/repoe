import json
from collections import OrderedDict

import requests

from RePoE.model.mods_by_base import (
    EssenceModLevels,
    EssenceMods,
    ItemClasses,
    ModTypes,
    ModWeights,
    SynthModGroups,
    TagSet,
    TagSets,
)
from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json

include_classes = set(
    [
        "AbyssJewel",
        "ExpeditionLogbook",
        "FishingRod",
        "HeistBlueprint",
        "HeistContract",
        "HeistEquipmentReward",
        "HeistEquipmentTool",
        "HeistEquipmentUtility",
        "HeistEquipmentWeapon",
        "Flask",
        "Jewel",
        "Map",
        "Relic",
        "Tincture",
        "Trinket",
    ]
)


class mods_by_base(Parser_Module):
    def write(self) -> None:
        root = ItemClasses({})

        with open(self.data_path + "base_items.min.json") as f:
            base_items: dict[str, dict] = json.load(f)
        with open(self.data_path + "item_classes.min.json") as f:
            item_classes: dict = json.load(f)
        with open(self.data_path + "mods.min.json") as f:
            mods = json.load(f)
            mods_by_domain: dict[str, dict[str, dict]] = {}
            for mod_id, mod in mods.items():
                if mod["generation_type"] in ["blight_tower", "unique", "tempest", "enchantment", "crucible_tree"]:
                    continue
                mods_by_domain.setdefault(mod["domain"], {})[mod_id] = mod

        # Collect legacy mods (all spawn weights = 0) for the second pass.
        # These are prefix/suffix mods that GGG removed from the drop/craft pool.
        # The main loop skips them because weight=0 is falsy in Python.
        #
        # Two categories:
        # - "specific_tags" mods: have item-class tags (weapon, ring, etc.) — route to matching bases
        # - "default_only" mods: only {default: 0} — apply to all standard equipment bases
        #
        # Collected from domain=item, domain=crafted, and domain=unveiled (all have legacy mods).
        # Exclusions (handled by dedicated cache sections, not the regular mod pool):
        # - is_essence_only mods
        # - Delve* prefix mods (delve drop-only, handled by delve generator)
        # - BreachBody* mods (breach-specific, handled by breach generator)
        legacy_specific: dict[str, dict] = {}
        legacy_default_only: dict[str, dict] = {}
        for legacy_domain in ["item", "crafted", "unveiled"]:
            gen_type_prefix = f"{legacy_domain}_" if legacy_domain != "item" else ""
            for mod_id, mod in mods_by_domain.get(legacy_domain, {}).items():
                gen_type = mod["generation_type"]
                if gen_type not in ("prefix", "suffix"):
                    continue
                spawn_weights = mod["spawn_weights"]
                if not spawn_weights:
                    continue
                if not all(sw["weight"] == 0 for sw in spawn_weights):
                    continue
                # Skip mods handled by dedicated cache sections
                if mod.get("is_essence_only", False):
                    continue
                if mod_id.startswith("Delve"):
                    continue
                if mod_id.startswith("BreachBody"):
                    continue
                specific_tags = [sw["tag"] for sw in spawn_weights if sw["tag"] != "default"]
                if specific_tags:
                    legacy_specific[mod_id] = {"mod": mod, "specific_tags": set(specific_tags), "gen_type_prefix": gen_type_prefix}
                else:
                    legacy_default_only[mod_id] = {"mod": mod, "gen_type_prefix": gen_type_prefix}

        for base_id, base in base_items.items():
            item_class: dict = item_classes[base["item_class"]]
            influence_tags = item_class.get("influence_tags", [])
            if not (influence_tags or item_class.get("category_id", None) in include_classes):
                continue
            by_class = root.root.setdefault(item_class["name"], TagSets({}))
            by_tags: TagSet = by_class.root.setdefault(",".join(base["tags"]), TagSet(bases=[], mods={}))
            by_tags.bases.append(base_id)
            mods_data = by_tags.mods
            tags = OrderedDict.fromkeys(base["tags"])
            conditional_tags = OrderedDict(tags)
            conditional_mods = set()
            # Domains with prefixed gen_types (e.g. delve → delve_prefix, crafted → crafted_prefix)
            # so downstream consumers can query each source separately.
            # flask/tincture are NOT extra domains — they're the base's own domain for those
            # item types and are already iterated via base["domain"]. Adding them here would
            # cause cross-contamination via the "default" spawn_weight tag.
            prefixed_domains = {"delve", "crafted", "unveiled", "flask", "tincture"}
            extra_domains = ["delve", "crafted", "unveiled"]
            restart = True
            while restart:
                restart = False
                for domain in [base["domain"]] + extra_domains:
                    for mod_id, mod in mods_by_domain.get(domain, {}).items():

                        weight = next(
                            (weight["weight"] for weight in mod["spawn_weights"] if weight["tag"] in tags), None
                        )
                        conditional_weight = next(
                            (weight["weight"] for weight in mod["spawn_weights"] if weight["tag"] in conditional_tags),
                            None,
                        )
                        if weight != conditional_weight:
                            conditional_mods.add(mod_id)
                        gen_type = mod["generation_type"]
                        # GGG tagged all Eater of Worlds eldritch implicits as "archnemesis"
                        # instead of "eater_of_worlds_implicit" — remap to match Exarch naming
                        if gen_type == "archnemesis":
                            gen_type = "eater_of_worlds_implicit"
                        if domain in prefixed_domains:
                            gen_type = domain + "_" + gen_type
                        if not weight and not conditional_weight:
                            influence = next(
                                (weight for weight in mod["spawn_weights"] if weight["tag"] in influence_tags), {}
                            )
                            if influence:
                                weight = influence["weight"]
                                gen_type = gen_type + "_" + influence["tag"].split("_")[-1]
                            else:
                                continue
                        mod_generation = mods_data.root.setdefault(gen_type, ModTypes({}))
                        mod_group = mod_generation.root.setdefault(mod["type"], ModWeights({}))
                        mod_group.root[mod_id] = weight
                        for added_tag in mod.get("adds_tags", []):
                            if added_tag not in conditional_tags:
                                restart = conditional_tags[added_tag] = True
                                conditional_tags.move_to_end(added_tag, False)
                        if restart:
                            break
            if conditional_mods:
                by_tags.conditional_mods = list(sorted(conditional_mods))

            # Legacy pass: add all-zero-weight mods that the main loop skipped (weight=0 is falsy).
            # Influence legacy mods are already handled by the influence fallback above.
            base_tags = set(base["tags"])
            influence_tag_set = set(influence_tags)

            # 1) Specific-tag legacy mods: route by non-default, non-influence tag match
            for mod_id, legacy_info in legacy_specific.items():
                non_influence_tags = legacy_info["specific_tags"] - influence_tag_set
                if not non_influence_tags:
                    continue
                if not non_influence_tags.intersection(base_tags):
                    continue
                gen_type = legacy_info["gen_type_prefix"] + legacy_info["mod"]["generation_type"]
                if gen_type == "archnemesis":
                    gen_type = "eater_of_worlds_implicit"
                mod_generation = mods_data.root.setdefault(gen_type, ModTypes({}))
                mod_group = mod_generation.root.setdefault(legacy_info["mod"]["type"], ModWeights({}))
                if mod_id not in (mod_group.root or {}):
                    mod_group.root[mod_id] = 0

            # 2) Default-only legacy mods: apply to all standard equipment bases
            #    (skip dedicated categories like jewels, flasks, etc.)
            if item_class.get("category_id", None) not in include_classes:
                for mod_id, legacy_info in legacy_default_only.items():
                    gen_type = legacy_info["gen_type_prefix"] + legacy_info["mod"]["generation_type"]
                    if gen_type == "archnemesis":
                        gen_type = "eater_of_worlds_implicit"
                    mod_generation = mods_data.root.setdefault(gen_type, ModTypes({}))
                    mod_group = mod_generation.root.setdefault(legacy_info["mod"]["type"], ModWeights({}))
                    if mod_id not in (mod_group.root or {}):
                        mod_group.root[mod_id] = 0

        for synth in requests.get(
            "https://www.poewiki.net/index.php?title=Special:CargoExport&tables=synthesis_mods&format=json"
            "&fields=synthesis_mods.item_class_ids__full%3Ditem_classes%2C+synthesis_mods.mod_ids__full%3Dmods"
            "&group+by=synthesis_mods.mod_ids__full%2Csynthesis_mods.item_class_ids__full&order+by=&limit=2000"
        ).json():
            for item_class in synth["item_classes"]:
                results: SynthModGroups = root.root[item_classes[item_class]["name"]].root.setdefault(
                    "synthesis", SynthModGroups({})
                )
                for mod_id in synth["mods"]:
                    if mod_id == "SynthesisImplicitMaximumAttackDodge1":
                        mod_id = "SynthesisImplicitSpellDamageSuppressed1_"
                    mod = mods[mod_id]
                    group = results.root.setdefault(mod["type"], [])
                    if mod_id not in group:
                        group.append(mod_id)

        essences = self.relational_reader["Essences.dat64"]
        keys = [k for k in essences.table_columns.keys() if k.endswith("ModsKey") and not k.startswith("Display")]
        item_class_map = {k.replace(" ", "") + "_ModsKey": k for k in item_classes}
        item_class_map["OneHandThrustingSword_ModsKey"] = "Thrusting One Hand Sword"
        for essence in essences:
            essence_item = essence["BaseItemTypesKey"]
            if essence_item["Id"] == "Metadata/Items/Currency/CurrencyCorruptMonolith":
                continue
            name = essence_item["Name"]
            level = name.split()[0]
            type = name.split()[-1]
            for key in keys:
                essence_levels: EssenceModLevels = root.root[item_classes[item_class_map[key]]["name"]].root.setdefault(
                    "essences", EssenceModLevels({})
                )
                essence_levels.root.setdefault(type, EssenceMods({})).root[level] = essence[key]["Id"]

        write_json(root, self.data_path, "mods_by_base")


if __name__ == "__main__":
    call_with_default_args(mods_by_base)
