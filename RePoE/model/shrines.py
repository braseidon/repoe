from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class ShrinesStat(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    value: int


class ShrinesBuff(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    template_id: str
    id: str
    name: str
    description: str
    icon: Optional[str] = None
    stats: List[ShrinesStat]
    lines: List[str]
    untranslated_stats: List[str]


class ShrinesSchemaValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_lesser_shrine: bool
    is_pvp_only: bool
    duration: int
    timeout_in_seconds: int
    player_buff: Optional[ShrinesBuff] = None


class Model(RootModel[Dict[str, ShrinesSchemaValue]]):
    root: Dict[str, ShrinesSchemaValue]
