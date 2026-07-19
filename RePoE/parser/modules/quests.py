from collections import defaultdict

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
                "npcs": [],
                "rewards": [],
                "static_rewards": [],
                "states": [],
            }

        # Reward offers are the join hub: rewards and reward-giver NPCs both hang off
        # QuestRewardOffers rather than referencing Quest.dat64 directly.
        offer_to_quest = {}
        for offer in self.relational_reader["QuestRewardOffers.dat64"]:
            quest = offer["QuestKey"]
            if quest is not None and quest.rowid in quests:
                offer_to_quest[offer.rowid] = quest.rowid

        npcs = defaultdict(set)
        for talk in self.relational_reader["NPCTalk.dat64"]:
            offer, npc = talk["QuestRewardOffersKey"], talk["NPCKey"]
            if offer is None or npc is None or not npc["Name"]:
                continue
            quest_rowid = offer_to_quest.get(offer.rowid)
            if quest_rowid is not None:
                npcs[quest_rowid].add(npc["Name"])
        for quest_rowid, names in npcs.items():
            quests[quest_rowid]["npcs"] = sorted(names)

        for reward in self.relational_reader["QuestRewards.dat64"]:
            offer, item = reward["RewardOffer"], reward["Reward"]
            if offer is None or item is None:
                continue
            quest_rowid = offer_to_quest.get(offer.rowid)
            if quest_rowid is None:
                continue
            # Empty classes = granted to every class (skill books); a populated list is
            # the per-class gem reward split.
            quests[quest_rowid]["rewards"].append(
                {
                    "item": item["Name"],
                    "item_id": item["Id"],
                    "classes": sorted(c["Name"] for c in (reward["Characters"] or []) if c["Name"]),
                    "level": reward["RewardLevel"],
                    "stack": reward["RewardStack"],
                }
            )

        # Stat grants that aren't items: bandit choices, Kitava's resistance penalties.
        for row in self.relational_reader["QuestStaticRewards.dat64"]:
            quest = row["QuestKey"]
            if quest is None or quest.rowid not in quests:
                continue
            values = row["StatValues"] or []
            stats = [
                {"id": stat["Id"], "value": values[i] if i < len(values) else None}
                for i, stat in enumerate(row["StatsKeys"] or [])
            ]
            if not stats:
                continue
            client_string = row["ClientStringsKey"]
            quests[quest.rowid]["static_rewards"].append(
                {
                    "stats": stats,
                    "description": client_string["Text"] if client_string is not None else None,
                }
            )

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
