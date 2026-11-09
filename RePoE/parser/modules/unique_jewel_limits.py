from RePoE.parser.util import call_with_default_args, write_json
from RePoE.parser import Parser_Module


class unique_jewel_limits(Parser_Module):
    """Unique jewel name -> "Limited to: N" count, from UniqueJewelLimits.dat.

    Each row references the jewel's name in Words.dat (JewelName) and carries the
    number of copies that may be socketed at once (Limit). The name is the Words.dat
    Text, the same string uniques.json uses as a unique's id.

    Two rows for one jewel name raise ValueError instead of overwriting.
    """

    def write(self) -> None:
        root = {}
        for row in self.relational_reader["UniqueJewelLimits.dat64"]:
            name = row["JewelName"]["Text"]
            if name in root:
                raise ValueError(f"duplicate UniqueJewelLimits row for {name!r}")
            root[name] = row["Limit"]

        write_json(dict(sorted(root.items())), self.data_path, "unique_jewel_limits")


if __name__ == "__main__":
    call_with_default_args(unique_jewel_limits)
