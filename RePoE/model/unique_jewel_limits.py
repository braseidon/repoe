from __future__ import annotations

from typing import Dict

from pydantic import RootModel


class Model(RootModel[Dict[str, int]]):
    root: Dict[str, int]
