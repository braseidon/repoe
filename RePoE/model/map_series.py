from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class MapSeriesIcons(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    base: Optional[str] = None
    infected: Optional[str] = None
    shaper: Optional[str] = None
    elder: Optional[str] = None
    drawn: Optional[str] = None
    delirious: Optional[str] = None
    uber_blight: Optional[str] = None
    purple: Optional[str] = None
    memory: Optional[str] = None
    uber_memory: Optional[str] = None
    mirage: Optional[str] = None


class MapSeriesSchemaValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    name: str
    icons: MapSeriesIcons


class Model(RootModel[Dict[str, MapSeriesSchemaValue]]):
    root: Dict[str, MapSeriesSchemaValue]
