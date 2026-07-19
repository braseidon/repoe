from RePoE.parser.util import call_with_default_args, export_image, get_id_or_none, write_json
from RePoE.parser import Parser_Module


class quests(Parser_Module):
    def write(self) -> None:
        quests = {}
        for quest in self.relational_reader["Quest.dat64"]:
            icon = quest["Icon_DDSFile"]
            if icon:
                export_image(icon, self.data_path, self.file_system)
            quests[quest.rowid] = {
                "id": quest["Id"],
                "name": quest["Name"],
                "act": quest["Act"],
                "type": get_id_or_none(quest["Type"]),
                "quest_id": quest["QuestId"],
                "icon": icon or None,
                "states": [],
            }

        for state in self.relational_reader["QuestStates.dat64"]:
            quest = state["Quest"]
            if quest is None or quest.rowid not in quests:
                continue
            quests[quest.rowid]["states"].append(
                {
                    "order": state["Order"],
                    "text": state["Text"] or None,
                    "message": state["Message"] or None,
                    "map_pin_texts": list(state["MapPinsTexts"] or []),
                    "flags_present": [get_id_or_none(f) for f in (state["FlagsPresent"] or [])],
                    "flags_missing": [get_id_or_none(f) for f in (state["FlagsMissing"] or [])],
                }
            )

        # QuestStates.Order counts *down* to completion, so descending order puts the
        # opening objective (the text shown before any progress) at states[0].
        for quest in quests.values():
            quest["states"].sort(key=lambda state: state["order"], reverse=True)

        data = sorted(quests.values(), key=lambda quest: (quest["act"], quest["quest_id"], quest["id"]))
        write_json(data, self.data_path, "quests")


if __name__ == "__main__":
    call_with_default_args(quests)
