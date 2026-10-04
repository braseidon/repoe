from RePoE.parser.util import call_with_default_args, export_image, write_json
from RePoE.parser import Parser_Module

# MapSeries.dat icon columns -> output key. The base icon is the blank map the game
# draws a map's own art (MapNumbersN, a symbol, unique art) on top of; the others are
# the per-variant blanks of the same series.
ICON_COLUMNS = {
    "BaseIcon_DDSFile": "base",
    "Infected_DDSFile": "infected",
    "Shaper_DDSFile": "shaper",
    "Elder_DDSFile": "elder",
    "Drawn_DDSFile": "drawn",
    "Delirious_DDSFile": "delirious",
    "UberBlight_DDSFile": "uber_blight",
    "Purple_DDSFile": "purple",
    "Memory_DDSFile": "memory",
    "UberMemory_DDSFile": "uber_memory",
    "Mirage_DDSFile": "mirage",
}


class map_series(Parser_Module):
    """One entry per MapSeries.dat row (one per atlas map series / league), keyed by
    row index, with the series' blank map icons. Every non-empty icon is exported."""

    def write(self) -> None:
        root = {}
        for row in self.relational_reader["MapSeries.dat64"]:
            icons = {}
            for column, key in ICON_COLUMNS.items():
                ddsfile = row[column] or None
                icons[key] = ddsfile
                if ddsfile and self.language == "English":
                    export_image(ddsfile, self.data_path, self.file_system)
            root[str(row.rowid)] = {"id": row["Id"], "name": row["Name"], "icons": icons}
        write_json(root, self.data_path, "map_series")


if __name__ == "__main__":
    call_with_default_args(map_series)
