from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class StrongboxesSchemaValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: Optional[str] = None
    tags: List[str]
    fixed_mods: List[str]
    min_level: int
    max_level: int
    inherits_from: Optional[str] = None
    is_hardmode: bool
    spawn_weight: int
    spawn_weight_hardmode: int


class Model(RootModel[Dict[str, StrongboxesSchemaValue]]):
    root: Dict[str, StrongboxesSchemaValue]
