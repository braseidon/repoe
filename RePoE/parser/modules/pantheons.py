from PyPoE.poe.file.idl import IDLFile
from PyPoE.poe.file.translations import TranslationFileCache
from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json

# Pantheon effect text uses the generic player stat description file, the same one
# Path of Building loads in src/Export/Scripts/pantheons.lua before reading this table.
STAT_FILE = "stat_descriptions.txt"

# Effect1..Effect4 / GodName1..GodName4 are the four soul slots of a god panel.
# Slot 1 is the base soul (granted by the campaign kill in PantheonPanelLayout.QuestFlag);
# slots 2-4 are the map-captured upgrades and are the only ones with a PantheonSouls row.
SLOTS = (1, 2, 3, 4)

# Art/UIImages1.txt destination stems referenced by CoverImage / SelectionImage.
UI_IMAGE_LIST = "Art/UIImages1.txt"


class pantheons(Parser_Module):
    """The Pantheon panel: gods, their four soul slots, rendered effect text, unlock source.

    Two tables, joined on PantheonSouls.PanelLayout (a ref|out to PantheonPanelLayout):

      PantheonPanelLayout  one row per panel slot. 12 rows have IsDisabled false (4 major,
                           8 minor); the rest are unnamed "Minor God N" placeholders with
                           empty GodName/Effect columns. Carries GodName1..4 and
                           Effect1..4_StatsKeys / Effect1..4_Values.
      PantheonSouls        one row per CAPTURABLE upgrade soul (20: 4 major x 3 + 8 minor x 1).
                           Carries the map, the boss and the Captured Soul vessel item.
                           There is no row for slot 1 -- the base soul is not captured.

    Slot resolution is proven twice per row and the module refuses to guess:
      * PantheonSouls.QuestFlagDowngrade equals PantheonPanelLayout.DowngradeFlag{slot-1}
      * PantheonSouls.Unknown0 equals PantheonPanelLayout.LeagueQuestFlag{slot-1}
        (Unknown0 is a quest-flag id in the 1324-1343 range, NOT a slot index)
    Both must resolve to the same slot or the row is a hard error. As a third, semantic
    confirmation the resolved slot's GodName equals MonsterVarieties.Name of the row's
    CapturedMonster for all 20 rows.

    There is NO god display-name column. GodName1 ("Soul of the Brine King") is the closest
    thing the data carries and is emitted as souls[0].name; nothing here synthesises a
    shorter "The Brine King" form.

    CoverImage / SelectionImage are Art/UIImages1.txt destination stems, not .dds paths, and
    they are panel CHROME keyed by panel size and position -- the four majors get the four
    CoverLarge* frames, all eight minors share CoverSmall. They are not god portraits; no
    per-god art exists in this table. Paths are emitted, never exported: append .webp after
    running the ui_images module to get the file on disk.
    """

    def write(self) -> None:
        self.tc: TranslationFileCache = self.get_cache(TranslationFileCache)
        translation_file = self.tc[STAT_FILE]

        idl = IDLFile()
        idl.read(self.file_system.get_file(UI_IMAGE_LIST))
        ui_image_destinations = {record.destination for record in idl}

        souls_by_god = self._index_souls()

        root = {}
        for god in self.relational_reader["PantheonPanelLayout.dat64"]:
            if god["IsDisabled"]:
                continue

            god_id = god["Id"]
            unlocks = souls_by_god.pop(god_id, {})

            souls = []
            for slot in SLOTS:
                stat_keys = god[f"Effect{slot}_StatsKeys"]
                if not stat_keys:
                    continue

                values = list(god[f"Effect{slot}_Values"])
                stat_ids = [stat["Id"] for stat in stat_keys]
                if len(stat_ids) != len(values):
                    raise ValueError(f"{god_id} slot {slot}: {len(stat_ids)} stat keys but {len(values)} values")

                translation = translation_file.get_translation(stat_ids, values, full_result=True, lang=self.language)
                if translation.missing_ids:
                    raise ValueError(
                        f"{god_id} slot {slot}: no {STAT_FILE} translation for {sorted(translation.missing_ids)}"
                    )

                souls.append(
                    {
                        "name": god[f"GodName{slot}"],
                        "stats": [{"id": stat_id, "value": value} for stat_id, value in zip(stat_ids, values)],
                        "lines": translation.lines,
                        "unlock": self._unlock(god_id, slot, unlocks.pop(slot, None)),
                    }
                )

            if unlocks:
                raise ValueError(
                    f"{god_id}: PantheonSouls rows for slots {sorted(unlocks)} have no populated"
                    " Effect columns on the panel row"
                )

            for column in ("CoverImage", "SelectionImage"):
                if god[column] not in ui_image_destinations:
                    raise ValueError(f"{god_id}: {column} {god[column]!r} is not a {UI_IMAGE_LIST} destination")

            root[god_id] = {
                "id": god_id,
                "is_major_god": god["IsMajorGod"],
                "is_disabled": god["IsDisabled"],
                "cover_image": god["CoverImage"],
                "selection_image": god["SelectionImage"],
                "souls": souls,
            }

        if souls_by_god:
            raise ValueError(f"PantheonSouls rows point at disabled or unknown gods: {sorted(souls_by_god)}")

        write_json(root, self.data_path, "pantheons")

    def _index_souls(self) -> dict[str, dict[int, object]]:
        index: dict[str, dict[int, object]] = {}
        for row in self.relational_reader["PantheonSouls.dat64"]:
            god = row["PanelLayout"]
            if god is None:
                raise ValueError(f"PantheonSouls row {row.rowid} has no PanelLayout")

            slot = self._resolve_slot(god, row)
            by_slot = index.setdefault(god["Id"], {})
            if slot in by_slot:
                raise ValueError(f"{god['Id']}: two PantheonSouls rows resolve to slot {slot}")
            by_slot[slot] = row
        return index

    def _resolve_slot(self, god, row) -> int:
        """Slot number (2-4) for a PantheonSouls row, agreed by two independent columns."""
        downgrade = row["QuestFlagDowngrade"]
        by_downgrade = next(
            (
                offset + 1
                for offset in (1, 2, 3)
                if downgrade is not None
                and god[f"DowngradeFlag{offset}"] is not None
                and god[f"DowngradeFlag{offset}"]["Id"] == downgrade["Id"]
            ),
            None,
        )
        by_quest_flag = next(
            (offset + 1 for offset in (1, 2, 3) if god[f"LeagueQuestFlag{offset}"] == row["Unknown0"]),
            None,
        )
        if by_downgrade is None or by_quest_flag is None or by_downgrade != by_quest_flag:
            raise ValueError(
                f"PantheonSouls row {row.rowid} ({god['Id']}): cannot agree on a slot --"
                f" QuestFlagDowngrade says {by_downgrade}, Unknown0 says {by_quest_flag}"
            )
        return by_downgrade

    def _unlock(self, god_id: str, slot: int, row):
        if slot == 1:
            if row is not None:
                raise ValueError(f"{god_id}: slot 1 is the base soul and must not have a PantheonSouls row")
            return None
        if row is None:
            raise ValueError(f"{god_id}: slot {slot} is an upgrade soul with no PantheonSouls row")

        world_area = row["WorldArea"]
        if world_area is None:
            raise ValueError(f"{god_id} slot {slot}: PantheonSouls row has no WorldArea")

        monsters = row["CapturedMonster"] or []
        if len(monsters) != 1:
            raise ValueError(
                f"{god_id} slot {slot}: CapturedMonster holds {len(monsters)} entries;"
                " the flat monster_id/monster_name pair can only carry one"
            )

        vessel = row["CapturedVessel"]
        if vessel is None:
            raise ValueError(f"{god_id} slot {slot}: PantheonSouls row has no CapturedVessel")

        return {
            "world_area_id": world_area["Id"],
            "world_area_name": world_area["Name"],
            "monster_id": monsters[0]["Id"],
            "monster_name": monsters[0]["Name"],
            "description": row["CapturedMonsterDescription"],
            "vessel_id": vessel["Id"],
            "vessel_name": vessel["Name"],
            "vessel_dds_file": vessel["ItemVisualIdentity"]["DDSFile"],
        }


if __name__ == "__main__":
    call_with_default_args(pantheons)
