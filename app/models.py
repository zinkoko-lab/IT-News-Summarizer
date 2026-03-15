from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Region = Literal["global", "japan"]


@dataclass(slots=True)
class Article:
    title: str
    url: str
    description: str
    source: str
    published_at: datetime
    region: Region


@dataclass(slots=True)
class RankedSummary:
    title: str
    url: str
    source: str
    published_at: datetime
    summary: str
    region: Region
