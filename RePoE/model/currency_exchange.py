from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class Exchange(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    category: Optional[str] = None
    sub_category: Optional[str] = None
    enabled_in_standard: bool
    enabled_in_challenge: bool


class BaseItemAffinity(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    affinity: str
    via: str


class Affinity(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    stash_type: Optional[str] = None
    data0: List[int]


class BaseItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    exchange: Optional[Exchange] = None
    affinities: Optional[List[BaseItemAffinity]] = None


class CurrencyExchangeSchema(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    exchange_categories: Dict[str, str]
    affinities: Dict[str, Affinity]
    item_class_category_affinities: Dict[str, str]
    base_items: Dict[str, BaseItem]


class Model(RootModel[CurrencyExchangeSchema]):
    root: CurrencyExchangeSchema
