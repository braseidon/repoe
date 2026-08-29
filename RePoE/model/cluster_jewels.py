from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class PassiveSkill(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: str
    icon: str
    mastery_icon: Optional[str]
    stats: Dict[str, int]
    stat_text: List[str]
    enchant: List[str]
    tag: str


class JewelSize(Enum):
    Large = "Large"
    Medium = "Medium"
    Small = "Small"


class JewelEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    size: JewelSize
    min_skills: int
    max_skills: int
    small_indices: List[int]
    notable_indices: List[int]
    socket_indices: List[int]
    total_indices: int
    passive_skills: List[PassiveSkill]


class ClusterJewelsSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    jewels: Dict[str, JewelEntry]
    keystones: List[str]
    notable_sort_order: Dict[str, int]
    orbit_offsets: Dict[str, List[int]]


class Model(RootModel[ClusterJewelsSchema]):
    root: ClusterJewelsSchema
