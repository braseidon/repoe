"""The monsters a granted effect summons, named by the value of one of its constant stats.

display_minion_monster_type is a DisplayMinionMonsterType row id and alternate_minion a
SummonedSpecificMonsters row id; both rows point at MonsterVarieties.
"""

from typing import Any, Dict, List, Tuple

# Constant stats whose value names the monster a skill summons, and the table that value
# is a row id of.
MINION_LINK_STATS = {
    "display_minion_monster_type": "DisplayMinionMonsterType.dat64",
    "alternate_minion": "SummonedSpecificMonsters.dat64",
}


def link_tables(reader: Any) -> Dict[str, Dict[int, Any]]:
    """The rows of each MINION_LINK_STATS table, keyed by their Id column."""
    return {table: {row["Id"]: row for row in reader[table]} for table in MINION_LINK_STATS.values()}


def granted_effect_stat_sets(granted_effect: Any) -> List[Any]:
    return [s for s in [granted_effect["StatSet1"], *(granted_effect["StatSet2"] or [])] if s is not None]


def summoned_varieties(granted_effect: Any, links: Dict[str, Dict[int, Any]]) -> List[Tuple[str, int, Any]]:
    """(stat id, stat value, MonsterVarieties row) for each link stat among the granted
    effect's constant stats. A value with no row in its table, or a row with no
    MonsterVarietiesKey, raises: the link would otherwise be lost without a trace."""
    found: List[Tuple[str, int, Any]] = []
    for stat_set in granted_effect_stat_sets(granted_effect):
        for stat, value in zip(stat_set["ConstantStats"], stat_set["ConstantStatsValues"]):
            table = MINION_LINK_STATS.get(stat["Id"])
            if table is None:
                continue
            link = links[table].get(value)
            if link is None:
                raise ValueError(f"{granted_effect['Id']}: {stat['Id']} {value} has no {table} row")
            variety = link["MonsterVarietiesKey"]
            if variety is None:
                raise ValueError(f"{granted_effect['Id']}: {table} row {value} has no MonsterVarietiesKey")
            found.append((stat["Id"], value, variety))
    return found
