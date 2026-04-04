from PyPoE.poe.file.translations import TranslationFileCache

from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json


def _icon_path(dds_path: str) -> str:
    """Convert .dds file path to .png for sprite sheet lookup."""
    if dds_path and dds_path.endswith(".dds"):
        return dds_path[:-4] + ".png"
    return dds_path


class cluster_jewel_notables(Parser_Module):
    def write(self) -> None:
        tf = self.get_cache(TranslationFileCache)["passive_skill_stat_descriptions.txt"]
        data = []
        for row in self.relational_reader["PassiveTreeExpansionSpecialSkills.dat64"]:
            ps = row["PassiveSkillsKey"]
            stats = {stat["Id"]: value for stat, value in ps["StatsZip"]}
            data.append(
                {
                    "id": ps["Id"],
                    "name": ps["Name"],
                    "icon": _icon_path(ps["Icon_DDSFile"]),
                    "is_keystone": ps["IsKeystone"],
                    "is_notable": ps["IsNotable"],
                    "jewel_stat": row["StatsKey"]["Id"],
                    "stats": stats,
                    "stat_text": tf.get_translation(stats.keys(), stats, lang=self.language),
                }
            )
        write_json(data, self.data_path, "cluster_jewel_notables")


if __name__ == "__main__":
    call_with_default_args(cluster_jewel_notables)
