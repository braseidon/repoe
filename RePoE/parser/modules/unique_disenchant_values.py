from RePoE.parser.util import call_with_default_args, write_json
from RePoE.parser import Parser_Module


def disenchant_entry(row) -> dict:
    """One VillageUniqueDisenchantValues.dat row as {name, value, ruthless_value}.

    The unique's name is the Words row's Text2 column: Text carries the internal
    spelling (curly apostrophes, typos, a different name on some rows), Text2 the
    name the item shows in game. A row with no Words reference or an empty Text2
    raises instead of exporting a nameless value.
    """
    words = row["UniqueName"]
    if words is None:
        raise ValueError(f"VillageUniqueDisenchantValues row {row.rowid} has no UniqueName")
    name = words["Text2"]
    if not name:
        raise ValueError(
            f"VillageUniqueDisenchantValues row {row.rowid}: Words row {words.rowid} ({words['Text']!r}) has no Text2"
        )
    return {"name": name, "value": row["Value"], "ruthless_value": row["RuthlessValue"]}


class unique_disenchant_values(Parser_Module):
    """One entry per VillageUniqueDisenchantValues.dat row, keyed by row index: the
    unique's name and its disenchant value multipliers (standard and Ruthless).

    Rows are not keyed by name because two rows can share one Text2. Values are
    the stored float32 multipliers, unrounded."""

    def write(self) -> None:
        root = {}
        for row in self.relational_reader["VillageUniqueDisenchantValues.dat64"]:
            root[str(row.rowid)] = disenchant_entry(row)
        write_json(root, self.data_path, "unique_disenchant_values")


if __name__ == "__main__":
    call_with_default_args(unique_disenchant_values)
