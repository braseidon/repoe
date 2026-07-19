from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class QuestState(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    order: int
    text: Optional[str] = None
    message: Optional[str] = None
    map_pin_texts: List[str]
    flags_present: List[str]
    flags_missing: List[str]


class QuestReward(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    item: str
    item_id: str
    classes: List[str]
    level: int
    stack: int


class QuestStaticRewardStat(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    value: Optional[int] = None


class QuestStaticReward(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    stats: List[QuestStaticRewardStat]
    description: Optional[str] = None


class QuestsSchemaElement(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: str
    act: int
    type: Optional[str] = None
    quest_id: int
    icon: Optional[str] = None
    npcs: List[str]
    rewards: List[QuestReward]
    static_rewards: List[QuestStaticReward]
    states: List[QuestState]


class Model(RootModel[List[QuestsSchemaElement]]):
    root: List[QuestsSchemaElement]
