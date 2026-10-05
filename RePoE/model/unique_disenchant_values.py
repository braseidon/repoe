from __future__ import annotations

from typing import Dict

from pydantic import BaseModel, ConfigDict, RootModel


class UniqueDisenchantValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    value: float
    ruthless_value: float


class Model(RootModel[Dict[str, UniqueDisenchantValue]]):
    root: Dict[str, UniqueDisenchantValue]
