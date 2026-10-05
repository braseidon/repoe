import unittest

from RePoE.model import unique_disenchant_values
from RePoE.parser.modules.unique_disenchant_values import disenchant_entry


class Row(dict):
    def __init__(self, rowid, **columns):
        super().__init__(columns)
        self.rowid = rowid


def words(text, text2, rowid=7):
    return Row(rowid, Text=text, Text2=text2)


def disenchant_row(word_row, value=891.1599731445312, ruthless=21.260000228881836, rowid=3):
    return Row(rowid, UniqueName=word_row, Value=value, RuthlessValue=ruthless)


class DisenchantEntryTest(unittest.TestCase):
    def test_names_the_unique_by_text2_not_text(self):
        entry = disenchant_entry(disenchant_row(words("Broken Elegy", "The Broken Elegy"), value=4.5, ruthless=1.0))

        self.assertEqual({"name": "The Broken Elegy", "value": 4.5, "ruthless_value": 1.0}, entry)

    def test_keeps_the_stored_value_unrounded(self):
        entry = disenchant_entry(disenchant_row(words("Mageblood", "Mageblood")))

        self.assertEqual(891.1599731445312, entry["value"])
        self.assertEqual(21.260000228881836, entry["ruthless_value"])

    def test_raises_on_a_row_with_no_unique_name(self):
        with self.assertRaisesRegex(ValueError, "row 3 has no UniqueName"):
            disenchant_entry(disenchant_row(None))

    def test_raises_on_an_empty_text2(self):
        with self.assertRaisesRegex(ValueError, r"Words row 7 \('Mageblood'\) has no Text2"):
            disenchant_entry(disenchant_row(words("Mageblood", "")))

    def test_the_model_accepts_entries_keyed_by_row_index(self):
        entry = disenchant_entry(disenchant_row(words("Mageblood", "Mageblood")))

        model = unique_disenchant_values.Model({"3": entry})

        self.assertEqual("Mageblood", model.root["3"].name)


if __name__ == "__main__":
    unittest.main()
