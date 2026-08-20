from RePoE.parser.util import call_with_default_args, write_json
from RePoE.parser import Parser_Module


class talismans(Parser_Module):
    """The base item to talisman-enchantment link, from BaseItemTypes.TalismanEnchants.

    Nothing else in the dump carries this edge: every TalismanEnchant* mod has empty
    spawn_weights, so no tag reaches them from mods_by_base, and base_items.json lists
    the reworked talisman bases with implicits: [].

    The link used to live in Talismans.dat (BaseItemTypesKey/ModsKey/SpawnWeight/Tier).
    That table is GONE from the client -- PyPoE's generated.py still specs it, but
    Data/Talismans.datc64 is absent from the index, so reading it raises FileNotFoundError.
    GGG moved the edge onto BaseItemTypes as a ref|list|ref|out column, which is why this
    module emits no spawn_weight or tier: those columns no longer exist anywhere.

    TalismanEnchants is a LIST, so a base may legitimately carry more than one
    enchantment. One row is emitted per (base item, mod) pair; consumers must not
    assume the mapping is 1:1 without checking.
    """

    def write(self) -> None:
        rows = []
        for base_item in self.relational_reader["BaseItemTypes.dat64"]:
            for mod in base_item["TalismanEnchants"] or []:
                rows.append(
                    {
                        "base_item": base_item["Id"],
                        "mod": mod["Id"],
                    }
                )

        rows.sort(key=lambda entry: (entry["base_item"], entry["mod"]))
        write_json(rows, self.data_path, "talismans")


if __name__ == "__main__":
    call_with_default_args(talismans)
