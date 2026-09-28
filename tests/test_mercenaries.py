import unittest
from types import SimpleNamespace
from unittest import mock

from PyPoE.poe.file.translations import TranslationFileCache

from RePoE.model import (
    mercenary_builds,
    mercenary_classes,
    mercenary_flavour_text,
    mercenary_inventories,
    mercenary_skills,
    mercenary_supports,
)
from RePoE.parser.modules.mercenaries import (
    build_entry,
    class_entry,
    flavour_text_entry,
    inventory_entry,
    keyed,
    mercenaries,
    pair_infamous,
    skill_entry,
    support_entry,
)


def ref(row_id, **columns):
    return dict(columns, Id=row_id)


def skill_row(granted_effect_id, name="Shield Crush", supports=(), band="High", granted_effect=True):
    return {
        "GrantedEffect": (
            ref(granted_effect_id, ActiveSkill={"Icon_DDSFile": f"Art/2DArt/SkillIcons/{granted_effect_id}.dds"})
            if granted_effect
            else None
        ),
        "SupportCount": ref(band),
        "PossibleSupports": [ref(s) for s in supports],
        "EncounterGrantedEffect": None,
        "Name": name,
        "Description": "Slams the ground with your shield.",
        "RequiredLevel": 12,
        "SkillFamily": None,
        "HouseIcon": "",
    }


def build_row(build_id="PhysicalDuelistShields", name="Bastion", infamous=False, tags=("mercenary_phys_duelist",)):
    return {
        "Id": build_id,
        "Name": name,
        "Class": ref("PhysicalDuelist"),
        "IsInfamous": infamous,
        "Skills1": [skill_row("ShieldCrushMercenary"), skill_row("ShieldChargeMercenary")],
        "Skills2Count": 2,
        "Skills2": [skill_row("TempestShieldMercenary")],
        "Skills3Count": 2,
        "Skills3": [skill_row("DashMercenary")],
        "IdleSkill": skill_row("DoLiterallyNothing"),
        "Tags": [ref(tag) for tag in tags],
        "WieldableTypes": [{"ItemClass": ref("Shield")}],
        "ExtraStats": [
            {
                "Id": "str0",
                "Stat": ref("base_strength"),
                "Level24": 6,
                "Level68": 21,
                "Level84": 42,
                "Category": ref("Defensive", Name="Defensive"),
            }
        ],
        "Achievements": [],
        "AIFile": "Metadata/Monsters/Mercenaries/MercenaryDuelist/PhysicalDuelistShields.ais",
    }


OVERRIDE = {
    "slot_id": 9,
    "mtx_type": "Metadata/Items/MicrotransactionItemEffects/MasterArmour2Body",
    "dds_file": "Art/x.dds",
}


def translation(ids_per_line, lines):
    return SimpleNamespace(found_ids=ids_per_line, found_lines=lines)


class BuildEntryTest(unittest.TestCase):
    def test_lists_skills_by_granted_effect_id_with_pick_counts(self):
        entry = build_entry(build_row(), [OVERRIDE])

        self.assertEqual(["ShieldCrushMercenary", "ShieldChargeMercenary"], entry["primary_skills"])
        self.assertEqual({"count": 2, "pool": ["TempestShieldMercenary"]}, entry["secondary_skills"])
        self.assertEqual({"count": 2, "pool": ["DashMercenary"]}, entry["utility_skills"])
        self.assertEqual("DoLiterallyNothing", entry["idle_skill"])

    def test_keeps_class_weapon_classes_extra_stats_and_overrides(self):
        entry = build_entry(build_row(), [OVERRIDE])

        self.assertEqual("PhysicalDuelist", entry["class_id"])
        self.assertEqual(["Shield"], entry["weapon_item_classes"])
        self.assertEqual(
            [
                {
                    "id": "str0",
                    "stat_id": "base_strength",
                    "level24": 6,
                    "level68": 21,
                    "level84": 42,
                    "category": {"id": "Defensive", "name": "Defensive"},
                }
            ],
            entry["extra_stats"],
        )
        self.assertEqual([OVERRIDE], entry["visual_overrides"])

    def test_the_model_accepts_a_build(self):
        builds, _ = pair_infamous({"PhysicalDuelistShields": build_entry(build_row(), [OVERRIDE])})

        mercenary_builds.Model(builds)


class PairInfamousTest(unittest.TestCase):
    def builds(self, **infamous_columns):
        regular = build_entry(build_row(), [OVERRIDE])
        infamous_row = dict(
            build_row(
                "PhysicalDuelistShieldsNoble",
                "Infamous Bastion",
                True,
                ("mercenary_phys_duelist", "mercenary_noble_born"),
            ),
            **infamous_columns,
        )
        return {"PhysicalDuelistShields": regular, "PhysicalDuelistShieldsNoble": build_entry(infamous_row, [OVERRIDE])}

    def test_puts_an_infamous_build_inside_its_regular_build_with_only_what_differs(self):
        builds, unpaired = pair_infamous(self.builds())

        self.assertEqual(["PhysicalDuelistShields"], list(builds))
        self.assertEqual([], unpaired)
        self.assertEqual(
            {
                "id": "PhysicalDuelistShieldsNoble",
                "name": "Infamous Bastion",
                "tags": ["mercenary_phys_duelist", "mercenary_noble_born"],
            },
            builds["PhysicalDuelistShields"]["infamous"],
        )

    def test_pairs_by_id_alone_so_a_changed_class_stays_inside(self):
        builds, _ = pair_infamous(self.builds(Class=ref("MeleeAOEStrikeDuelist")))

        self.assertEqual("MeleeAOEStrikeDuelist", builds["PhysicalDuelistShields"]["infamous"]["class_id"])
        self.assertEqual("PhysicalDuelist", builds["PhysicalDuelistShields"]["class_id"])

    def test_keeps_an_infamous_build_with_no_regular_build_on_its_own(self):
        ruckus = build_entry(
            build_row("AurasMinionsTemplarSmiteRuckusNoble", "Infamous Warpriest of the Ruckus", True), []
        )

        builds, unpaired = pair_infamous({"AurasMinionsTemplarSmiteRuckusNoble": ruckus})

        self.assertEqual(["AurasMinionsTemplarSmiteRuckusNoble"], unpaired)
        self.assertTrue(builds["AurasMinionsTemplarSmiteRuckusNoble"]["is_infamous"])
        self.assertIsNone(builds["AurasMinionsTemplarSmiteRuckusNoble"]["infamous"])

    def test_raises_when_an_infamous_build_empties_a_field(self):
        with self.assertRaises(ValueError):
            pair_infamous(self.builds(IdleSkill=None))

    def test_an_unpaired_infamous_build_does_not_catch_a_later_infamous_id(self):
        lone = build_entry(build_row("X", "Lone Infamous", True), [])
        later = build_entry(build_row("XNoble", "Infamous of X", True), [])

        builds, unpaired = pair_infamous({"X": lone, "XNoble": later})

        self.assertEqual(["X", "XNoble"], sorted(unpaired))
        self.assertIsNone(builds["X"]["infamous"])
        self.assertIsNone(builds["XNoble"]["infamous"])

    def test_the_model_accepts_a_paired_build(self):
        builds, _ = pair_infamous(self.builds(Class=ref("MeleeAOEStrikeDuelist")))

        mercenary_builds.Model(builds)


class ClassEntryTest(unittest.TestCase):
    def test_nests_the_attribute_and_keeps_icon_paths(self):
        row = {
            "HouseName": "House Azadi",
            "Attribute": ref("StrDex", Name="Str / Dex", Tags=[ref("str_dex_armour")]),
            "MonsterVariety": ref("Metadata/Monsters/Mercenaries/MercenaryDuelist1"),
            "MonsterVarietyAllied": ref("Metadata/Monsters/Mercenaries/MercenaryDuelist1Allied"),
            "TerrainFeature": ref("MercenaryEncounterDuelist1"),
            "HouseSpawnChanceStats": [ref("map_mercenary_house_azadi_chance_+%")],
            "AttributeSpawnChanceStats": [ref("map_mercenary_strength_dexterity_aligned_chance_+%")],
            "ClassIcon": "Art/2DArt/UIImages/InGame/MercenariesofTrarthus/MercClassIconDuelist",
            "HouseIcon": "Art/2DArt/UIImages/InGame/MercenariesofTrarthus/HouseAzadi",
            "HouseBuffIcon": "Art/2DArt/UIImages/InGame/MercenariesofTrarthus/HouseBuffIconAzadi",
        }

        entry = class_entry(row)

        self.assertEqual({"id": "StrDex", "name": "Str / Dex", "tags": ["str_dex_armour"]}, entry["attribute"])
        self.assertEqual(row["ClassIcon"], entry["class_icon"])
        mercenary_classes.Model({"PhysicalDuelist": entry})


class SkillEntryTest(unittest.TestCase):
    CONVERTED = {
        "is_support": False,
        "tags": None,
        "color": "r",
        "cast_time": 1000,
        "active_skill": {
            "id": "shield_crush",
            "display_name": "Shield Crush",
            "description": "Slams the ground with your shield.",
            "icon": "Art/2DArt/SkillIcons/ShieldCrush.dds",
            "types": ["attack"],
            "weapon_restrictions": ["Shield"],
            "is_skill_totem": False,
            "is_manually_casted": True,
            "stat_conversions": {},
        },
        "stat_translation_file": "stat_translations/skill",
        "base_item": None,
        "base_effectiveness": 1.0,
        "incremental_effectiveness": 0.0,
        "projectile_speed": 1000,
        "gem_style": "trarthan",
        "per_level": {
            "1": {"required_level": 12, "stat_text": {"shield_crush_damage": "Deals 5 to 10 Physical Damage"}},
            "40": {"required_level": 100, "stat_text": {"shield_crush_damage": "Deals 50 to 100 Physical Damage"}},
        },
        "static": {"quality_stats": [], "stats": [{"id": "is_area_damage", "value": 1, "type": "implicit"}, None]},
        "tooltip_order": ["shield_crush_damage"],
    }

    def test_keys_by_granted_effect_and_copies_only_the_named_converter_fields(self):
        entry, error = skill_entry(
            skill_row("ShieldCrushMercenary", supports=["WitherOnHitHigh", "LeechLow"]),
            lambda ge: self.CONVERTED,
            False,
        )

        self.assertIsNone(error)
        self.assertEqual(["WitherOnHitHigh", "LeechLow"], entry["possible_supports"])
        self.assertEqual("High", entry["support_count"])
        self.assertEqual("Art/2DArt/SkillIcons/ShieldCrushMercenary.dds", entry["icon"])
        self.assertEqual(
            ["active_skill", "cast_time", "per_level", "stat_translation_file", "static", "tooltip_order"],
            sorted(set(entry) & set(self.CONVERTED)),
        )
        self.assertNotIn("icon", entry["active_skill"])
        mercenary_skills.Model({"ShieldCrushMercenary": entry})

    def test_returns_a_conversion_error_instead_of_raising(self):
        def convert(ge):
            raise KeyError("ToxicRainMercenary")

        entry, error = skill_entry(skill_row("ToxicRainMercenary", "Toxic Rain"), convert, False)

        self.assertEqual("KeyError: 'ToxicRainMercenary'", error)
        self.assertNotIn("per_level", entry)
        mercenary_skills.Model({"ToxicRainMercenary": entry})

    def test_raises_on_a_conversion_error_when_fail_fast(self):
        def convert(ge):
            raise KeyError("ToxicRainMercenary")

        with self.assertRaises(KeyError):
            skill_entry(skill_row("ToxicRainMercenary", "Toxic Rain"), convert, True)

    def test_raises_on_a_row_with_no_granted_effect(self):
        with self.assertRaises(ValueError):
            skill_entry(skill_row("x", "Broken", granted_effect=False), lambda ge: {}, False)


class SupportEntryTest(unittest.TestCase):
    def row(self, stats, values):
        return {
            "Id": "WitherOnHitHigh",
            "Name": "Greater Wither on Hit",
            "Tier": 3,
            "SupportFamily": ref("WitherOnHit"),
            "GemIcon": "Art/2DItems/Gems/Support/WitherGemSupport.dds",
            "Stats": [ref(s) for s in stats],
            "StatValues": values,
        }

    def test_renders_stat_text_keyed_by_the_stats_each_line_shows(self):
        def translate(values):
            self.assertEqual({"withered_on_hit_chance_%": 45, "support_withered_base_duration_ms": 2000}, values)
            return translation(
                [["withered_on_hit_chance_%"], ["support_withered_base_duration_ms", "unused_zero_stat"]],
                ["Supported Skills have 45% chance to inflict Withered on Hit", "Withered lasts 2 seconds"],
            )

        entry = support_entry(
            self.row(
                ["withered_on_hit_chance_%", "support_withered_base_duration_ms", "unused_zero_stat"], [45, 2000, 0]
            ),
            translate,
        )

        self.assertEqual(
            {
                "withered_on_hit_chance_%": "Supported Skills have 45% chance to inflict Withered on Hit",
                "support_withered_base_duration_ms": "Withered lasts 2 seconds",
            },
            entry["stat_text"],
        )
        self.assertEqual({"id": "unused_zero_stat", "value": 0}, entry["stats"][2])
        self.assertEqual(("WitherOnHit", 3), (entry["family"], entry["tier"]))
        mercenary_supports.Model({"WitherOnHitHigh": entry})

    def test_writes_no_stat_text_for_a_support_with_no_stats_without_translating(self):
        def translate(values):
            raise AssertionError("translate called with no stats")

        self.assertEqual({}, support_entry(self.row([], []), translate)["stat_text"])

    def test_raises_when_stats_and_values_differ(self):
        with self.assertRaises(ValueError):
            support_entry(self.row(["stat_a"], [1, 2]), lambda values: translation([], []))


class FlavourTextAndInventoryTest(unittest.TestCase):
    def test_zips_tags_with_weights(self):
        row = {
            "Id": "NonEleBowRanger1",
            "Description": "Even a lawless land needs rules.",
            "Tags": [ref("mercenary_noble_born"), ref("mercenary_non_ele_ranger")],
            "TagWeight": [0, 1000],
        }

        entry = flavour_text_entry(row)

        self.assertEqual(
            [{"tag": "mercenary_noble_born", "weight": 0}, {"tag": "mercenary_non_ele_ranger", "weight": 1000}],
            entry["tag_weights"],
        )
        mercenary_flavour_text.Model({"NonEleBowRanger1": entry})

    def test_raises_when_tags_and_weights_differ(self):
        with self.assertRaises(ValueError):
            flavour_text_entry({"Id": "x", "Description": "", "Tags": [ref("a")], "TagWeight": []})

    def test_keeps_the_slot_position(self):
        entry = inventory_entry({"PositionX": 252, "PositionY": 185})

        self.assertEqual({"position_x": 252, "position_y": 185}, entry)
        mercenary_inventories.Model({"BodyArmour1": entry})


class ExportIconsTest(unittest.TestCase):
    SKILLS = {
        "ShieldCrushMercenary": {
            "icon": "Art/2DArt/SkillIcons/ShieldCrush.dds",
            "house_icon": "Art/2DArt/SkillIcons/HouseAzadiSkill.dds",
        },
        "DoLiterallyNothing": {"icon": "", "house_icon": ""},
        "FireAegisMercenary": {"icon": "Art/2DArt/BuffIcons/FireAegis.dds", "house_icon": ""},
    }
    SUPPORTS = {
        "WitherOnHitHigh": {"icon": "Art/2DItems/Gems/Support/WitherGemSupport.dds"},
        "SparkSpecificNovaHigh": {"icon": "Art/2DItems/Gems/Support/MercGoldSupportGem.dds"},
        "LightningDamageMid": {"icon": "Art/2DItems/Gems/Support/MercGoldSupportGem.dds"},
    }

    def export(self, found):
        """The export_image calls and the printed lines of one _export_icons run."""
        module = mercenaries(SimpleNamespace(), "out/", None, "English", {})
        with mock.patch("RePoE.parser.modules.mercenaries.export_image", side_effect=found) as export_image:
            with mock.patch("builtins.print") as printed:
                module._export_icons(self.SKILLS, self.SUPPORTS)
        return export_image, [call.args[0] for call in printed.call_args_list]

    def test_exports_every_skill_and_support_icon_once_and_skips_empty_paths(self):
        export_image, _ = self.export(lambda path, data_path, file_system: True)

        self.assertEqual(
            [
                "Art/2DArt/BuffIcons/FireAegis.dds",
                "Art/2DArt/SkillIcons/HouseAzadiSkill.dds",
                "Art/2DArt/SkillIcons/ShieldCrush.dds",
                "Art/2DItems/Gems/Support/MercGoldSupportGem.dds",
                "Art/2DItems/Gems/Support/WitherGemSupport.dds",
            ],
            sorted(call.args[0] for call in export_image.call_args_list),
        )
        self.assertEqual({"out/"}, {call.args[1] for call in export_image.call_args_list})

    def test_reports_the_icons_the_client_does_not_have(self):
        _, lines = self.export(lambda path, data_path, file_system: "Wither" not in path)

        self.assertEqual(
            ["mercenaries: 1 of 5 icons not found", "  Art/2DItems/Gems/Support/WitherGemSupport.dds"], lines
        )


class WriteTest(unittest.TestCase):
    def reader(self):
        class_row = {
            "Id": "PhysicalDuelist",
            "HouseName": "House Azadi",
            "Attribute": ref("StrDex", Name="Str / Dex", Tags=[]),
            "MonsterVariety": None,
            "MonsterVarietyAllied": None,
            "TerrainFeature": None,
            "HouseSpawnChanceStats": [],
            "AttributeSpawnChanceStats": [],
            "ClassIcon": "",
            "HouseIcon": "",
            "HouseBuffIcon": "",
        }
        support_row = {
            "Id": "WitherOnHitHigh",
            "Name": "Greater Wither on Hit",
            "Tier": 3,
            "SupportFamily": None,
            "GemIcon": "",
            "Stats": [],
            "StatValues": [],
        }
        flavour_row = {"Id": "NonEleBowRanger1", "Description": "", "Tags": [], "TagWeight": []}
        inventory_row = {"Id": ref("BodyArmour1"), "PositionX": 0, "PositionY": 0}
        return {
            "MercenaryBuildVisualOverrides.dat64": [],
            "MercenaryBuilds.dat64": [build_row()],
            "MercenarySkills.dat64": [skill_row("ShieldCrushMercenary")],
            "MercenarySupports.dat64": [support_row],
            "MercenaryClasses.dat64": [class_row],
            "MercenaryFlavourText.dat64": [flavour_row],
            "MercenaryInventories.dat64": [inventory_row],
        }

    def write(self):
        """Runs mercenaries.write() against the fake reader and a translation cache
        whose only key is mercenary_support_stat_descriptions.txt, and returns the
        written files keyed by name."""
        translations = {"mercenary_support_stat_descriptions.txt": object()}
        module = mercenaries(SimpleNamespace(), "out/", self.reader(), "French", {TranslationFileCache: translations})
        written = {}
        with mock.patch("RePoE.parser.modules.mercenaries.GemConverter") as gem_converter:
            gem_converter.return_value.convert.return_value = {}
            with mock.patch(
                "RePoE.parser.modules.mercenaries.write_json",
                side_effect=lambda data, path, name: written.__setitem__(name, data),
            ):
                with mock.patch("builtins.print"):
                    module.write()
        return written

    def test_keys_skills_by_granted_effect_id(self):
        written = self.write()

        self.assertEqual(["ShieldCrushMercenary"], list(written["mercenary_skills"]))

    def test_every_support_names_its_stat_translation_file(self):
        reader = self.reader()
        second = dict(reader["MercenarySupports.dat64"][0], Id="WitherOnHitLow", Tier=1)
        reader["MercenarySupports.dat64"].append(second)
        self.reader = lambda: reader

        supports = self.write()["mercenary_supports"]

        self.assertEqual(
            {
                "WitherOnHitHigh": "stat_translations/mercenary_support",
                "WitherOnHitLow": "stat_translations/mercenary_support",
            },
            {support_id: support.get("stat_translation_file") for support_id, support in supports.items()},
        )
        mercenary_supports.Model(supports)

    def test_raises_when_the_support_translation_file_is_missing(self):
        translations = {"gem_stat_descriptions.txt": object()}
        module = mercenaries(SimpleNamespace(), "out/", self.reader(), "French", {TranslationFileCache: translations})

        with self.assertRaises(KeyError):
            with mock.patch("RePoE.parser.modules.mercenaries.GemConverter"):
                with mock.patch("RePoE.parser.modules.mercenaries.write_json"):
                    with mock.patch("builtins.print"):
                        module.write()


class KeyedTest(unittest.TestCase):
    def test_raises_on_a_duplicate_id(self):
        with self.assertRaises(ValueError):
            keyed([("a", {}), ("a", {})], "MercenarySupports")


if __name__ == "__main__":
    unittest.main()
