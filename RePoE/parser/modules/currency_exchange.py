from RePoE.parser.util import call_with_default_args, write_json
from RePoE.parser import Parser_Module

# Per-category stash tab layout tables -> the stash affinity (StashTabAffinities.Id)
# whose tab holds the layout's items.
LAYOUT_AFFINITIES = {
    "CurrencyStashTabLayout.dat64": "CurrencyItems",
    "FragmentStashTabLayout.dat64": "Fragments",
    "EssenceStashTabLayout.dat64": "Essences",
    "DelveStashTabLayout.dat64": "DelveItems",
    "BlightStashTabLayout.dat64": "BlightItems",
    "DeliriumStashTabLayout.dat64": "DeliriumItems",
    "DivinationCardStashTabLayout.dat64": "DivinationCards",
    "MetamorphosisStashTabLayout.dat64": "UltimatumItems",
}


class currency_exchange(Parser_Module):
    """The in-game Currency Exchange groups per base item, plus the stash affinities.

    CurrencyExchange.dat rows give each exchange-listed base item its Category and
    SubCategory (both rows of CurrencyExchangeCategories.dat) and two league flags.
    The affinity half joins the stash tab layouts, StashTabAffinityByBaseItemType and
    StashtabAffinityByItemClassCategory: which stash affinity (tab) a base item sorts to.

    Output keys: exchange_categories (category id -> name), affinities (affinity id ->
    name, stash type, raw Data0 list), item_class_category_affinities (item class
    category id -> affinity id), base_items (base item id -> name, optional exchange,
    optional affinities).

    A base item with two CurrencyExchange rows raises: the export keys one exchange
    entry per base item and would otherwise overwrite silently.
    """

    def write(self) -> None:
        reader = self.relational_reader

        stash_types = [row["Id"] for row in reader["StashType.dat64"]]

        categories = {row["Id"]: row["Name"] for row in reader["CurrencyExchangeCategories.dat64"]}

        affinities = {}
        for row in reader["StashTabAffinities.dat64"]:
            data0 = list(row["Data0"])
            stash_type_index = data0[-1] if data0 else None
            affinities[row["Id"]["Id"]] = {
                "name": row["Name"],
                "stash_type": (
                    stash_types[stash_type_index]
                    if stash_type_index is not None and stash_type_index < len(stash_types)
                    else None
                ),
                "data0": data0,
            }

        class_category_affinities = {
            row["ItemClassCategory"]["Id"]: row["StashTabAffinityId"]["Id"]
            for row in reader["StashtabAffinityByItemClassCategory.dat64"]
        }

        base_items = {}

        def entry(base):
            return base_items.setdefault(base["Id"], {"name": base["Name"]})

        for row in reader["CurrencyExchange.dat64"]:
            if row["Item"] is None:
                continue
            item = entry(row["Item"])
            if "exchange" in item:
                raise ValueError(f"CurrencyExchange.dat has two rows for {row['Item']['Id']}")
            item["exchange"] = {
                "category": row["Category"]["Id"] if row["Category"] else None,
                "sub_category": row["SubCategory"]["Id"] if row["SubCategory"] else None,
                "enabled_in_standard": row["EnabledInStandardLeague"],
                "enabled_in_challenge": row["EnabledInChallengeLeague"],
            }

        for table, affinity in LAYOUT_AFFINITIES.items():
            via = "layout:" + table.replace("StashTabLayout.dat64", "")
            for row in reader[table]:
                if "StoredItems" in row.keys():
                    stored = [x for x in (row["StoredItems"] or []) if x is not None]
                elif row["StoredItem"] is not None:
                    stored = [row["StoredItem"]]
                else:
                    stored = []
                for base in stored:
                    found = entry(base).setdefault("affinities", [])
                    if not any(a["affinity"] == affinity and a["via"] == via for a in found):
                        found.append({"affinity": affinity, "via": via})

        for row in reader["StashTabAffinityByBaseItemType.dat64"]:
            if row["BaseItemType"] is None:
                continue
            found = entry(row["BaseItemType"]).setdefault("affinities", [])
            for affinity in row["StashTabAffinityId"]:
                found.append({"affinity": affinity["Id"], "via": "base_item"})

        root = {
            "exchange_categories": categories,
            "affinities": affinities,
            "item_class_category_affinities": class_category_affinities,
            "base_items": dict(sorted(base_items.items())),
        }
        write_json(root, self.data_path, "currency_exchange")


if __name__ == "__main__":
    call_with_default_args(currency_exchange)
