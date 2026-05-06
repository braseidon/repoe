"""Extract curated UI image bundles from Art/UIImages1.txt as cropped WebPs.

Reads the IDL, looks up each curated destination path, slices the source DDS
atlas to that record's bounding box, and saves it as a .webp under the bundle's
output directory. Bundles are defined either as explicit destination lists or
as a path prefix that is expanded against the IDL at runtime.

Configure paths via env vars:
    POE_GAME_PATH  Path to the Path of Exile install (default: Steam Windows path)
    OUT_ROOT       Root for extracted bundles         (default: ./out/ui-extract)
"""

import os
from io import BytesIO

from PIL import Image

from PyPoE.poe.file.file_system import FileSystem
from PyPoE.poe.file.idl import IDLFile

GAME_PATH = os.environ.get(
    "POE_GAME_PATH",
    "C:/Program Files (x86)/Steam/steamapps/common/Path of Exile/",
)
OUT_ROOT = os.environ.get("OUT_ROOT", "./out/ui-extract")

_CLASS_ICONS = [
    # attr, ascendancy_suffix or "" for the base class icon
    ("Str", ""), ("Str", "Berserker"), ("Str", "Chieftain"), ("Str", "Juggernaut"),
    ("Dex", ""), ("Dex", "Deadeye"), ("Dex", "Pathfinder"), ("Dex", "Raider"),
    ("Int", ""), ("Int", "Elementalist"), ("Int", "Necromancer"), ("Int", "Occultist"),
    ("StrDex", ""), ("StrDex", "Champion"), ("StrDex", "Gladiator"), ("StrDex", "Slayer"),
    ("StrInt", ""), ("StrInt", "Guardian"), ("StrInt", "Hierophant"), ("StrInt", "Inquisitor"),
    ("DexInt", ""), ("DexInt", "Assassin"), ("DexInt", "Saboteur"), ("DexInt", "Trickster"),
    ("StrDexInt", ""), ("StrDexInt", "Ascendant"), ("StrDexInt", "Reliquarian"),
]


def _icon_dest(prefix: str, attr: str, suffix: str) -> str:
    name = f"Icon{attr}_{suffix}" if suffix else f"Icon{attr}"
    return f"Art/2DArt/UIImages/Common/{prefix}{name}"


# Bundles defined by path prefix — expanded against the IDL at runtime.
PREFIX_BUNDLES: dict[str, str] = {
    "archetype-custom-portraits": "Art/2DArt/UIImages/InGame/ArchetypeSelect/Custom/",
    "archetype-class-icons": "Art/2DArt/UIImages/Common/Archetypes/",
}

BUNDLES: dict[str, list[str]] = {
    "ascendancy-icons": [_icon_dest("", a, s) for a, s in _CLASS_ICONS],
    "ascendancy-icons-4k": [_icon_dest("4K/", a, s) for a, s in _CLASS_ICONS],
    "corpse-eaters": [
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterConstruct",
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterBeasts",
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterDemon",
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterEldritch",
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterHumanoid",
        "Art/2DArt/UIImages/InGame/Azmeri/CorpseEaterUndead",
    ],
    "class-portraits": [
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Str/MarauderBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Str/Berserker",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Str/Chieftain",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Str/Juggernaut",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Dex/RangerBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Dex/Deadeye",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Dex/Pathfinder",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Dex/Raider",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Int/WitchBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Int/Elementalist",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Int/Necromancer",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/Int/Occulist",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrDex/DuelistBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrDex/Gladiator",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrDex/Champion",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrDex/Slayer",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrInt/TemplarBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrInt/Hierophant",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrInt/Inquisitor",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/StrInt/Guardian",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/DexInt/ShadowBG",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/DexInt/Trickster",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/DexInt/Assasin",
        "Art/2DArt/UIImages/InGame/ArchetypeSelect/DexInt/Saboteur",
    ],
    "tree-backgrounds": [
        "Art/2DArt/UIImages/InGame/Classes/Dex/Deadeye/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Dex/Pathfinder/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Dex/Raider/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Dex/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/DexInt/Assassin/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/DexInt/Saboteur/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/DexInt/Trickster/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/DexInt/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/Int/Elementalist/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Int/Necromancer/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Int/Occultist/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Int/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/Str/Berserker/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Str/Chieftain/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Str/Juggernaut/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/Str/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDex/Champion/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDex/Gladiator/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDex/Slayer/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDex/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDexInt/Ascendant/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrDexInt/PassiveSkillScreenStartNodeBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrInt/Guardian/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrInt/Hierophant/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrInt/Inquisitor/PassiveSkillScreenBackground",
        "Art/2DArt/UIImages/InGame/Classes/StrInt/PassiveSkillScreenStartNodeBackground",
    ],
    "item-symbols": [
        "Art/2DArt/UIImages/InGame/ShaperItemSymbol",
        "Art/2DArt/UIImages/InGame/ElderItemSymbol",
        "Art/2DArt/UIImages/InGame/CrusaderItemSymbol",
        "Art/2DArt/UIImages/InGame/EyrieItemSymbol",
        "Art/2DArt/UIImages/InGame/BasiliskItemSymbol",
        "Art/2DArt/UIImages/InGame/JudicatorItemSymbol",
        "Art/2DArt/UIImages/InGame/CleansingFireItemSymbol",
        "Art/2DArt/UIImages/InGame/TangledItemSymbol",
        "Art/2DArt/UIImages/InGame/VeiledItemSymbol",
        "Art/2DArt/UIImages/InGame/SynthesisedItemSymbol",
        "Art/2DArt/UIImages/InGame/FracturedItemSymbol",
        "Art/2DArt/UIImages/InGame/BreachItemSymbol",
        "Art/2DArt/UIImages/InGame/ArchnemesisItemSymbol",
        "Art/2DArt/UIImages/InGame/RosePetalInfluencedItemSymbol",
        "Art/2DArt/UIImages/InGame/ExperimentedUniqueSymbol",
        "Art/2DArt/UIImages/InGame/Heist/StolenItemSymbol",
        "Art/2DArt/UIImages/InGame/4K/BreachItemSymbol",
        "Art/2DArt/UIImages/Misc/ShaperItemMask",
        "Art/2DArt/UIImages/Misc/ElderItemBackground",
    ],
}


def extract_record(fs: FileSystem, record, out_path: str) -> None:
    dds_bytes = fs.extract_dds(fs.get_file(record.source))
    if not dds_bytes or dds_bytes[:4] != b"DDS ":
        print(f"  SKIP (not a DDS): {record.source}")
        return
    with Image.open(BytesIO(dds_bytes)) as img:
        cropped = img.crop((record.x1, record.y1, record.x2 + 1, record.y2 + 1))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        cropped.save(out_path + ".webp", "WEBP", quality=95, method=6)


def main() -> None:
    fs = FileSystem(GAME_PATH)
    idl = IDLFile()
    idl.read(file_path_or_raw=fs.get_file("Art/UIImages1.txt"))
    # index by destination for O(1) lookup
    by_dest = {r.destination: r for r in idl}

    # Expand prefix bundles into explicit destination lists.
    bundles = dict(BUNDLES)
    for bundle_name, prefix in PREFIX_BUNDLES.items():
        bundles[bundle_name] = sorted(d for d in by_dest if d.startswith(prefix))

    total = 0
    missing: list[str] = []
    for bundle_name, destinations in bundles.items():
        print(f"\n== {bundle_name} ({len(destinations)} targets) ==")
        for dest in destinations:
            record = by_dest.get(dest)
            if record is None:
                print(f"  MISSING: {dest}")
                missing.append(dest)
                continue
            # Use the tail of the destination (after InGame/ or Misc/) as the filename
            # but keep class attribute subdir structure for readability.
            tail = dest.split("/InGame/", 1)[-1]
            if tail == dest:
                tail = dest.split("/UIImages/", 1)[-1]
            out_path = os.path.join(OUT_ROOT, bundle_name, tail)
            extract_record(fs, record, out_path)
            total += 1
            print(f"  OK  {tail}.webp  ({record.x2 - record.x1 + 1}x{record.y2 - record.y1 + 1})")
    print(f"\nExtracted {total} images to {OUT_ROOT}")
    if missing:
        print(f"Missing {len(missing)} entries — check spelling of destination paths.")


if __name__ == "__main__":
    main()
