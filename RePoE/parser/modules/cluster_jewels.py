from typing import Any, Dict, List

from PyPoE.poe.file.translations import TranslationFileCache

from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json


def _icon_path(dds_path: str) -> str:
    """Convert .dds file path to .png for sprite sheet lookup."""
    if dds_path and dds_path.endswith(".dds"):
        return dds_path[:-4] + ".png"
    return dds_path


class cluster_jewels(Parser_Module):
    def write(self) -> None:
        tf = self.get_cache(TranslationFileCache)["passive_skill_stat_descriptions.txt"]
        skills: Dict[str, List[Dict[str, Any]]] = {}
        for row in self.relational_reader["PassiveTreeExpansionSkills.dat64"]:
            size = row["PassiveTreeExpansionJewelSizesKey"]["Name"]
            if size not in skills:
                skills[size] = []

            stats = {stat["Id"]: value for stat, value in row["PassiveSkillsKey"]["StatsZip"]}
            stat_text = tf.get_translation(stats.keys(), stats, lang=self.language)
            mastery = row["Mastery_PassiveSkillsKey"]
            skills[size].append(
                {
                    "id": row["PassiveSkillsKey"]["Id"],
                    "name": row["PassiveSkillsKey"]["Name"],
                    "icon": _icon_path(row["PassiveSkillsKey"]["Icon_DDSFile"]),
                    "mastery_icon": _icon_path(mastery["Icon_DDSFile"]) if mastery else None,
                    "stats": stats,
                    "stat_text": stat_text,
                    "enchant": ["Added Small Passive Skills grant: " + line for line in stat_text],
                    "tag": row["TagsKey"]["Id"],
                }
            )

        # Orbit offsets: which tree positions each jewel socket's cluster nodes occupy
        # Only include slots that have orbit data (cluster-capable sockets)
        orbit_offsets = {}
        for row in self.relational_reader["PassiveJewelSlots.dat64"]:
            indices = row["StartIndices"]
            if indices:
                node_id = str(row["Slot"]["PassiveSkillGraphId"])
                orbit_offsets[node_id] = indices

        # Keystones that can appear on cluster jewels
        keystones = []
        for row in self.relational_reader["PassiveTreeExpansionSpecialSkills.dat64"]:
            ps = row["PassiveSkillsKey"]
            if ps["IsKeystone"]:
                keystones.append(ps["Name"])

        # Notable sort order: stat row index used by PoB for deterministic ordering
        notable_sort_order = {}
        for row in self.relational_reader["PassiveTreeExpansionSpecialSkills.dat64"]:
            ps = row["PassiveSkillsKey"]
            if ps["IsNotable"]:
                notable_sort_order[ps["Name"]] = row["StatsKey"].rowid

        data = {}
        for row in self.relational_reader["PassiveTreeExpansionJewels.dat64"]:
            size = row["PassiveTreeExpansionJewelSizesKey"]["Name"]
            data[row["BaseItemTypesKey"]["Id"]] = {
                "name": row["BaseItemTypesKey"]["Name"],
                "size": size,
                "min_skills": row["MinNodes"],
                "max_skills": row["MaxNodes"],
                "small_indices": row["SmallIndices"],
                "notable_indices": row["NotableIndices"],
                "socket_indices": row["SocketIndices"],
                "total_indices": row["TotalIndices"],
                "passive_skills": skills[size],
            }

        result = {
            "jewels": data,
            "keystones": keystones,
            "notable_sort_order": notable_sort_order,
            "orbit_offsets": orbit_offsets,
        }
        write_json(result, self.data_path, "cluster_jewels")


if __name__ == "__main__":
    call_with_default_args(cluster_jewels)
