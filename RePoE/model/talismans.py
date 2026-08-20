from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, RootModel


class TalismansSchemaElement(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    base_item: str
    mod: str


class Model(RootModel[List[TalismansSchemaElement]]):
    root: List[TalismansSchemaElement]
