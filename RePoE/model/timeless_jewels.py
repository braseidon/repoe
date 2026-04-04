from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class Stat(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    min: Optional[int] = None
    max: Optional[int] = None


class Version(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    index: int
    are_small_attribute_passives_replaced: bool
    are_small_normal_passives_replaced: bool
    minimum_additions: int
    maximum_additions: int
    notable_replacement_spawn_weight: int


class Skill(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: str
    passive_type: List[int]
    is_keystone: bool
    is_notable: bool
    stats: List[Stat]
    stat_text: List[str]
    spawn_weight: int
    conqueror_index: int
    conqueror_version: int
    icon: Optional[str] = None
    flavour_text: Optional[str] = None
    random_min: Optional[int] = None
    random_max: Optional[int] = None


class Addition(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    passive_type: List[int]
    stats: List[Stat]
    stat_text: List[str]
    spawn_weight: int


class TimelessJewelsSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    versions: Dict[str, Version]
    skills: Dict[str, List[Skill]]
    additions: Dict[str, List[Addition]]


class Model(RootModel[TimelessJewelsSchema]):
    root: TimelessJewelsSchema
