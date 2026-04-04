from typing import Any

from PyPoE.poe.file.translations import TranslationFileCache

from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json


class timeless_jewels(Parser_Module):
    """Extracts timeless jewel data from AlternatePassiveSkills, AlternatePassiveAdditions,
    and AlternateTreeVersions dat64 tables.

    Produces timeless_jewels.json with:
    - versions: jewel type definitions (Glorious Vanity, Lethal Pride, etc.)
    - skills: replacement notables/keystones grouped by jewel type
    - additions: small node additions grouped by jewel type
    """

    def write(self) -> None:
        tf = self.get_cache(TranslationFileCache)["passive_skill_stat_descriptions.txt"]

        # 1. Extract jewel type versions with config fields
        # Field mapping (from Vilsol/go-pob-data):
        #   Flag0 = AreSmallAttributePassiveSkillsReplaced
        #   Flag1 = AreSmallNormalPassiveSkillsReplaced
        #   Unknown2 (Var5) = MinimumAdditions
        #   Unknown3 (Var6) = MaximumAdditions
        #   Unknown6 (Var9) = NotableReplacementSpawnWeight
        versions: dict[str, dict[str, Any]] = {}
        version_id_lookup: dict[int, str] = {}
        for row in self.relational_reader["AlternateTreeVersions.dat64"]:
            version_id = row["Id"]
            version_id_lookup[row.rowid] = version_id
            versions[version_id] = {
                "id": version_id,
                "index": row.rowid,
                "are_small_attribute_passives_replaced": row["Flag0"],
                "are_small_normal_passives_replaced": row["Flag1"],
                "minimum_additions": row["Unknown2"],
                "maximum_additions": row["Unknown3"],
                "notable_replacement_spawn_weight": row["Unknown6"],
            }

        # 2. Extract replacement skills (notables + keystones)
        skills: dict[str, list[dict[str, Any]]] = {v: [] for v in versions}
        for row in self.relational_reader["AlternatePassiveSkills.dat64"]:
            version_key = row["AlternateTreeVersionsKey"]
            if version_key is None:
                continue
            version_id = version_key["Id"]

            stats = self._extract_stats(row)
            stat_text = self._get_stat_text(tf, row, stats)

            passive_types = list(row["PassiveType"])
            is_keystone = 4 in passive_types
            is_notable = 3 in passive_types

            # Conqueror fields (Unknown8 = ConquerorIndex, Unknown9 = ConquerorVersion)
            conqueror_index = row["Unknown8"]
            conqueror_version = row["Unknown9"]

            entry: dict[str, Any] = {
                "id": row["Id"],
                "name": row["Name"],
                "passive_type": passive_types,
                "is_keystone": is_keystone,
                "is_notable": is_notable,
                "stats": stats,
                "stat_text": stat_text,
                "spawn_weight": row["SpawnWeight"],
                "conqueror_index": conqueror_index,
                "conqueror_version": conqueror_version,
            }

            if row["DDSIcon"]:
                entry["icon"] = row["DDSIcon"]
            if row["FlavourText"]:
                entry["flavour_text"] = row["FlavourText"]
            if row["RandomMin"] != 0 or row["RandomMax"] != 0:
                entry["random_min"] = row["RandomMin"]
                entry["random_max"] = row["RandomMax"]

            skills[version_id].append(entry)

        # 3. Extract additions (small node mods)
        additions: dict[str, list[dict[str, Any]]] = {v: [] for v in versions}
        for row in self.relational_reader["AlternatePassiveAdditions.dat64"]:
            version_key = row["AlternateTreeVersionsKey"]
            if version_key is None:
                continue
            version_id = version_key["Id"]

            stats = self._extract_stats(row)
            stat_text = self._get_stat_text(tf, row, stats)

            passive_types = list(row["PassiveType"])

            entry = {
                "id": row["Id"],
                "passive_type": passive_types,
                "stats": stats,
                "stat_text": stat_text,
                "spawn_weight": row["SpawnWeight"],
            }

            additions[version_id].append(entry)

        # 4. Write output
        data = {
            "versions": versions,
            "skills": skills,
            "additions": additions,
        }
        write_json(data, self.data_path, "timeless_jewels")

    def _get_stat_text(self, tf: Any, row: Any, stats: list[dict[str, Any]]) -> list[str]:
        """Generate stat description text using min values for translation."""
        stat_values = {}
        for s in stats:
            # Use min value for translation
            stat_values[s["id"]] = s.get("min", 1)
        raw = tf.get_translation(
            stat_values.keys(), stat_values, lang=self.language
        )
        # Translation may return multi-line strings for single stats (e.g. keystones)
        # Split into individual lines for consistency with PoB's format
        lines = []
        for text in raw:
            for line in text.split("\n"):
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
        return lines

    @staticmethod
    def _extract_stats(row: Any) -> list[dict[str, Any]]:
        """Extract stats with min/max ranges from a dat row.

        Stats are stored as StatsKeys (list of FK refs) with corresponding
        Stat1Min/Stat1Max, Stat2Min/Stat2Max field pairs.
        """
        stats = []
        for i, stat in enumerate(row["StatsKeys"]):
            idx = i + 1
            min_key = f"Stat{idx}Min"
            max_key = f"Stat{idx}Max"

            stat_entry: dict[str, Any] = {
                "id": stat["Id"],
            }

            # Try to read min/max fields (Stat1Min, Stat1Max, Stat2Min, etc.)
            try:
                stat_entry["min"] = row[min_key]
                stat_entry["max"] = row[max_key]
            except (KeyError, IndexError):
                pass

            stats.append(stat_entry)
        return stats


if __name__ == "__main__":
    call_with_default_args(timeless_jewels)
