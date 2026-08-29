from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, RootModel


class ClusterJewelNotablesSchemaElement(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: str
    icon: str
    is_keystone: bool
    is_notable: bool
    jewel_stat: str
    stats: Dict[str, int]
    stat_text: List[str]


class Model(RootModel[List[ClusterJewelNotablesSchemaElement]]):
    root: List[ClusterJewelNotablesSchemaElement]
