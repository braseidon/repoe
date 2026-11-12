from RePoE.parser import Parser_Module
from RePoE.parser.util import call_with_default_args, write_json


class strongboxes(Parser_Module):
    """Strongboxes and the tags their mods spawn on, from Strongboxes.dat and Chests.dat.

    One entry per Strongboxes row, keyed by the Chests row's Id. A strongbox is a world
    object, not a base item, so base_items.json holds none of them; its rollable mods are
    the `chest` domain mods whose spawn weights match the tags listed here, the way an
    item's mods match its base's tags.

      Strongboxes.ChestsKey -> Chests (Name, TagsKeys, ModsKeys, MinLevel, MaxLevel)

    `tags` are Chests.TagsKeys in data order. `fixed_mods` are Chests.ModsKeys, the mods a
    box always carries. `spawn_weight` and `spawn_weight_hardmode` are the weights of the
    box itself among strongboxes, not of any mod. A Chests row two Strongboxes rows point
    at is a hard error.
    """

    def write(self) -> None:
        root = {}
        for row in self.relational_reader["Strongboxes.dat64"]:
            chest = row["ChestsKey"]
            if chest is None:
                raise ValueError(f"Strongboxes row {row.rowid} has no Chests row")

            chest_id = chest["Id"]
            if chest_id in root:
                raise ValueError(f"duplicate Strongboxes row for {chest_id!r}")

            root[chest_id] = {
                "id": chest_id,
                "name": chest["Name"] or None,
                "tags": [tag["Id"] for tag in chest["TagsKeys"]],
                "fixed_mods": [mod["Id"] for mod in chest["ModsKeys"]],
                "min_level": chest["MinLevel"],
                "max_level": chest["MaxLevel"],
                "inherits_from": chest["InheritsFrom"] or None,
                "is_hardmode": chest["IsHardmode"],
                "spawn_weight": row["SpawnWeight"],
                "spawn_weight_hardmode": row["SpawnWeightHardmode"],
            }

        write_json(root, self.data_path, "strongboxes")


if __name__ == "__main__":
    call_with_default_args(strongboxes)
