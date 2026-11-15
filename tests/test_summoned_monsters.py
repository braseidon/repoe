import unittest

from RePoE.model import mercenary_minions
from RePoE.parser.modules.mercenaries import minion_entry
from RePoE.parser.summoned_monsters import summoned_varieties

RESISTANCES = {
    "Id": "MapBoss",
    "FireNormal": 15,
    "ColdNormal": 15,
    "LightningNormal": 15,
    "ChaosNormal": 7,
    "FireCruel": 30,
    "ColdCruel": 30,
    "LightningCruel": 30,
    "ChaosCruel": 20,
    "FireMerciless": 40,
    "ColdMerciless": 40,
    "LightningMerciless": 40,
    "ChaosMerciless": 25,
}
MONSTER_TYPE = {
    "Id": "SkeletonMapBoss",
    "Accuracy": 100,
    "IsPlayerMinion": False,
    "Armour": 50,
    "Evasion": 0,
    "EnergyShield": 0,
    "DamageSpread": 20,
    "Resistances": RESISTANCES,
    "AltLife1": False,
    "AltLife2": False,
    "BaseDamageIgnoresAttackSpeed": False,
}
VARIETY = {
    "Id": "Metadata/Monsters/Skeletons/MapSkeletonBossMeleeStandalone",
    "Name": "Pagan Bishop of Agony",
    "LifeMultiplier": 400,
    "DamageMultiplier": 187,
    "AttackSpeed": 1605,
    "MonsterTypesKey": MONSTER_TYPE,
    "ModsKeys": [{"Id": "MonsterMapBoss"}],
    "ModsKeys2": [],
    "GrantedEffectsKeys": [{"Id": "Melee"}, {"Id": "CurseNova"}],
}


def granted_effect(stats, values):
    stat_set = {"ConstantStats": [{"Id": s} for s in stats], "ConstantStatsValues": values}
    return {"Id": "SSMPaganBishopMercenary", "StatSet1": stat_set, "StatSet2": []}


class SummonedVarietiesTest(unittest.TestCase):
    links = {
        "DisplayMinionMonsterType.dat64": {},
        "SummonedSpecificMonsters.dat64": {671: {"MonsterVarietiesKey": VARIETY}},
    }

    def test_alternate_minion_resolves_its_variety(self):
        found = summoned_varieties(
            granted_effect(["summon_specific_monsters_in_front_offset", "alternate_minion"], [10, 671]), self.links
        )
        self.assertEqual([("alternate_minion", 671, VARIETY)], found)

    def test_a_value_with_no_row_raises(self):
        with self.assertRaises(ValueError):
            summoned_varieties(granted_effect(["alternate_minion"], [999]), self.links)


class MinionEntryTest(unittest.TestCase):
    def test_columns_as_stored(self):
        entry = minion_entry(VARIETY)
        mercenary_minions.Model({VARIETY["Id"]: entry})
        self.assertEqual(
            (400, 187, 1605), (entry["life_multiplier"], entry["damage_multiplier"], entry["attack_speed"])
        )
        self.assertEqual(["MonsterMapBoss"], entry["mods"])
        self.assertEqual(["Melee", "CurseNova"], entry["granted_effects"])
        self.assertEqual(50, entry["monster_type"]["armour"])
        self.assertEqual(20, entry["monster_type"]["damage_spread"])
        resistances = entry["monster_type"]["resistances"]
        self.assertEqual(
            ("MapBoss", 7, 30, 40),
            (
                resistances["id"],
                resistances["chaos_normal"],
                resistances["fire_cruel"],
                resistances["lightning_merciless"],
            ),
        )
        self.assertEqual(25, resistances["chaos_merciless"])


if __name__ == "__main__":
    unittest.main()
