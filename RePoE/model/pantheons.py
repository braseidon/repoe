from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class PantheonsStat(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    value: int


class PantheonsUnlock(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    world_area_id: str
    world_area_name: str
    monster_id: str
    monster_name: str
    description: str
    vessel_id: str
    vessel_name: str
    vessel_dds_file: str


class PantheonsSoul(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    stats: List[PantheonsStat]
    lines: List[str]
    unlock: Optional[PantheonsUnlock] = None


class PantheonsSchemaValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    is_major_god: bool
    is_disabled: bool
    cover_image: str
    selection_image: str
    souls: List[PantheonsSoul]


class Model(RootModel[Dict[str, PantheonsSchemaValue]]):
    root: Dict[str, PantheonsSchemaValue]
