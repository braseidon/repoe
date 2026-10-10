"""Export the UI sprites and minimap icons an image manifest names, as PNG master + WebP.

The manifest is a JSON file passed as the only argument:
{"images": {"<any key>": {"ui": "<IDL destination>"} | {"minimap": "<MinimapIcons Id>"} | ...}}.
Other entry keys (`art`, RePoE's own export) are ignored here.

  ui       the destination's crop of its atlas, from Art/UIImages1.txt or
           Art/UIDivinationImages.txt  ->  <OUT_ROOT>/<destination>.png/.webp
  minimap  cell N of Art/2DArt/Minimap/Player.dds (14 columns of 64 px), N being the
           Id's row in MinimapIcons.dat64  ->  <OUT_ROOT>/Minimap/<Id>.png/.webp

Same encoding as RePoE's export_image: PNG lossless master, WebP at WEBP_QUALITY.
Exits 1 when any named source is missing from the client.

Configure paths via env vars:
    POE_GAME_PATH  Path to the Path of Exile install (default: Steam Windows path)
    OUT_ROOT       Export root (default: ./out/ui-images)

Run: poetry --directory <this repo> run python extract_manifest_images.py <manifest.json>
"""

import json
import os
import sys
from collections import defaultdict
from io import BytesIO

from PIL import Image

from PyPoE.poe.file.dat import RelationalReader
from PyPoE.poe.file.file_system import FileSystem
from PyPoE.poe.file.idl import IDLFile
from PyPoE.poe.file.specification.data import generated

from RePoE.parser.util import WEBP_QUALITY

GAME_PATH = os.environ.get(
    "POE_GAME_PATH",
    "C:/Program Files (x86)/Steam/steamapps/common/Path of Exile/",
)
OUT_ROOT = os.environ.get("OUT_ROOT", "./out/ui-images")

IDL_FILES = ("Art/UIImages1.txt", "Art/UIDivinationImages.txt")
MINIMAP_SHEET = "Art/2DArt/Minimap/Player.dds"
MINIMAP_COLUMNS = 14
MINIMAP_CELL = 64


def save(image: Image.Image, dest: str) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    image.save(dest + ".png")
    image.save(dest + ".webp", quality=WEBP_QUALITY)


def load_dds(fs: FileSystem, path: str) -> Image.Image | None:
    data = fs.extract_dds(fs.get_file(path))
    if not data or data[:4] != b"DDS ":
        return None
    image = Image.open(BytesIO(data))
    image.load()
    return image


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: extract_manifest_images.py <image-manifest.json>")
    with open(sys.argv[1], encoding="utf-8") as f:
        images = json.load(f)["images"]

    ui = sorted({e["ui"] for e in images.values() if "ui" in e})
    minimap = sorted({e["minimap"] for e in images.values() if "minimap" in e})
    fs = FileSystem(GAME_PATH)
    missing: list[str] = []

    by_dest = {}
    for idl_path in IDL_FILES:
        idl = IDLFile()
        idl.read(file_path_or_raw=fs.get_file(idl_path))
        by_dest.update({r.destination: r for r in idl})

    by_atlas = defaultdict(list)
    for dest in ui:
        record = by_dest.get(dest)
        if record is None:
            missing.append(f"ui {dest}: not in {' or '.join(IDL_FILES)}")
        else:
            by_atlas[record.source].append(record)

    for atlas, records in sorted(by_atlas.items()):
        sheet = load_dds(fs, atlas)
        if sheet is None:
            missing.extend(f"ui {r.destination}: atlas {atlas} is not a DDS" for r in records)
            continue
        for r in records:
            save(sheet.crop((r.x1, r.y1, r.x2 + 1, r.y2 + 1)), os.path.join(OUT_ROOT, r.destination))

    if minimap:
        reader = RelationalReader(
            path_or_file_system=fs,
            specification=generated.specification,
            read_options={"use_dat_value": False, "auto_build_index": True, "x64": True},
            language="English",
        )
        index = {row["Id"]: i for i, row in enumerate(reader["MinimapIcons.dat64"])}
        sheet = load_dds(fs, MINIMAP_SHEET)
        if sheet is None:
            raise SystemExit(f"{MINIMAP_SHEET} is not a DDS")
        sheet = sheet.convert("RGBA")
        for icon_id in minimap:
            if icon_id not in index:
                missing.append(f"minimap {icon_id}: not in MinimapIcons.dat64")
                continue
            i = index[icon_id]
            x, y = (i % MINIMAP_COLUMNS) * MINIMAP_CELL, (i // MINIMAP_COLUMNS) * MINIMAP_CELL
            save(sheet.crop((x, y, x + MINIMAP_CELL, y + MINIMAP_CELL)), os.path.join(OUT_ROOT, "Minimap", icon_id))

    written = len(ui) + len(minimap) - len(missing)
    print(f"Exported {written} images to {OUT_ROOT} ({len(ui)} ui, {len(minimap)} minimap named)")
    if missing:
        print("\n".join(f"MISSING {m}" for m in missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
