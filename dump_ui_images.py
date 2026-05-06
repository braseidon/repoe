"""Dump Art/UIImages*.txt IDL files as TSV so sprite categories can be grepped.

Each IDL record (destination path, source DDS, x1/y1/x2/y2, computed width/height)
is written as a row. Useful for discovering what UI image bundles exist before
running an extraction pass.

Configure paths via env vars:
    POE_GAME_PATH  Path to the Path of Exile install (default: Steam Windows path)
    OUT_DIR        Where the .tsv files are written  (default: ./out/idl-dumps)
"""

import os
import sys

from PyPoE.poe.file.file_system import FileSystem
from PyPoE.poe.file.idl import IDLFile

GAME_PATH = os.environ.get(
    "POE_GAME_PATH",
    "C:/Program Files (x86)/Steam/steamapps/common/Path of Exile/",
)
OUT_DIR = os.environ.get("OUT_DIR", "./out/idl-dumps")

CANDIDATE_IDLS = [
    "Art/UIImages1.txt",
    "Art/UIImages2.txt",
    "Art/UIImages3.txt",
    "Art/UIImages4.txt",
    "Art/UIImages5.txt",
    "Art/UIShop.txt",
    "Art/UIDivinationImages.txt",
    "Art/UIShapeShift.txt",
    "Art/ItemVisualEffect.txt",
    "Art/Items.txt",
]


def dump(idl_path: str, fs: FileSystem) -> int:
    try:
        raw = fs.get_file(idl_path)
    except Exception:
        return 0
    if not raw:
        return 0
    idl = IDLFile()
    try:
        idl.read(file_path_or_raw=raw)
    except Exception as e:
        print(f"  Failed to parse {idl_path}: {e}")
        return 0
    out_name = os.path.basename(idl_path).replace(".txt", ".tsv")
    out_path = os.path.join(OUT_DIR, "idl-" + out_name)
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("destination\tsource\tx1\ty1\tx2\ty2\twidth\theight\n")
        for record in idl:
            out.write(
                f"{record.destination}\t{record.source}\t{record.x1}\t{record.y1}\t"
                f"{record.x2}\t{record.y2}\t{record.x2 - record.x1 + 1}\t{record.y2 - record.y1 + 1}\n"
            )
    print(f"  Wrote {len(idl)} records from {idl_path} -> {out_path}")
    return len(idl)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    fs = FileSystem(GAME_PATH)
    total = 0
    for p in CANDIDATE_IDLS:
        total += dump(p, fs)
    print(f"Total records dumped: {total}")


if __name__ == "__main__":
    main()
