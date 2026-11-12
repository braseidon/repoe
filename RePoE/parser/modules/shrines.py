from PyPoE.poe.file.translations import TranslationFileCache
from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, export_icon, write_json

# Shrine buff stats are ordinary player stats; the generic description file words them.
STAT_FILE = "stat_descriptions.txt"


class shrines(Parser_Module):
    """Shrines and the buff each one grants a player, from Shrines.dat.

    One entry per Shrines row, keyed by Id. The join for the player buff is

      Shrines.Player_ShrineBuffsKey -> BuffTemplates   (Buff_StatValues)
      BuffTemplates.BuffDefinitionsKey -> BuffDefinitions (Name, Description, StatsKeys)
      BuffDefinitions.BuffVisualsKey -> BuffVisuals    (BuffDDSFile)

    Stat values pair with BuffDefinitions.StatsKeys by position: BuffTemplates.StatsKey is
    empty on shrine templates. A count mismatch between the two is a hard error.

    Every row is exported, PvP and Royale rows included. IsPVPOnly is not a complete
    marker for them (the three PVP* rows carry false), so `id`, `duration` and
    `timeout_in_seconds` are emitted for a consumer to filter on.

    `name` and `description` are the Shrines row's own strings (the description is the
    flavour line shown on the shrine). The buff carries its own name and description,
    which can differ: the lesser shrines share the full shrine's buff name, and the
    "Charged Shrine" row grants a buff named "Resonating Shrine".

    `lines` are the buff's stats rendered through stat_descriptions.txt. Stats at value 0
    are left out before rendering, since the game shows nothing for them and several
    descriptions would otherwise print a "+0%" line. Stats with no description in that
    file (has_shrine_effect, the Echoing Shrine speed stats and others) are listed in
    `untranslated_stats` instead. `stats` always holds every stat, zeros included, in
    data order; `lines` is not 1:1 with it.

    `icon` is the BuffVisuals .dds path. The icon is exported with its 4K copy when the
    client ships one.
    """

    def write(self) -> None:
        self.tc: TranslationFileCache = self.get_cache(TranslationFileCache)
        translation_file = self.tc[STAT_FILE]

        root = {}
        for row in self.relational_reader["Shrines.dat64"]:
            shrine_id = row["Id"]
            if shrine_id in root:
                raise ValueError(f"duplicate Shrines row for {shrine_id!r}")

            root[shrine_id] = {
                "id": shrine_id,
                "name": row["Name"]["Text"] if row["Name"] else None,
                "description": row["Description"]["Text"] if row["Description"] else None,
                "is_lesser_shrine": row["IsLesserShrine"],
                "is_pvp_only": row["IsPVPOnly"],
                "duration": row["Duration"],
                "timeout_in_seconds": row["TimeoutInSeconds"],
                "player_buff": self._buff(shrine_id, row["Player_ShrineBuffsKey"], translation_file),
            }

        write_json(root, self.data_path, "shrines")

    def _buff(self, shrine_id: str, template, translation_file):
        if template is None:
            return None

        definition = template["BuffDefinitionsKey"]
        if definition is None:
            raise ValueError(f"{shrine_id}: buff template {template['Id']!r} has no BuffDefinitions row")

        stat_ids = [stat["Id"] for stat in definition["StatsKeys"]]
        values = list(template["Buff_StatValues"])
        if len(stat_ids) != len(values):
            raise ValueError(
                f"{shrine_id}: template {template['Id']!r} has {len(values)} values"
                f" for {len(stat_ids)} stats on {definition['Id']!r}"
            )

        shown = [(stat_id, value) for stat_id, value in zip(stat_ids, values) if value != 0]
        lines: list[str] = []
        untranslated: list[str] = []
        if shown:
            translation = translation_file.get_translation(
                [stat_id for stat_id, _ in shown],
                [value for _, value in shown],
                full_result=True,
                lang=self.language,
            )
            lines = list(translation.lines)
            untranslated = [stat_id for stat_id, _ in shown if stat_id in set(translation.missing_ids)]

        icon = None
        visual = definition["BuffVisualsKey"]
        if visual is not None and visual["BuffDDSFile"]:
            icon = visual["BuffDDSFile"]
            if self.language == "English":
                export_icon(icon, self.data_path, self.file_system)

        return {
            "template_id": template["Id"],
            "id": definition["Id"],
            "name": definition["Name"],
            "description": definition["Description"],
            "icon": icon,
            "stats": [{"id": stat_id, "value": value} for stat_id, value in zip(stat_ids, values)],
            "lines": lines,
            "untranslated_stats": untranslated,
        }


if __name__ == "__main__":
    call_with_default_args(shrines)
