from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Category = Literal[
    "policy",
    "fleet_aircraft",
    "leadership",
    "app",
    "website",
    "operations",
    "safety_regulatory",
    "financial_strategy",
    "customer_experience",
    "other",
]


class Source(BaseModel):
    name: str
    kind: Literal["feed", "news_page", "page", "app_store"]
    tier: Literal["regulator", "official", "industry", "media"] = "media"
    url: str
    topics: list[Category] = Field(default_factory=list)
    article_paths: list[str] = Field(default_factory=list)
    exclude_title_keywords: list[str] = Field(default_factory=list)
    max_items: int = Field(default=20, ge=1, le=100)


class Observation(BaseModel):
    source_name: str
    source_tier: str
    title: str
    url: str
    published_at: datetime | None = None
    collected_at: datetime
    body: str
    fingerprint: str


class Analysis(BaseModel):
    relevant: bool
    category: Category
    entities: list[str] = Field(default_factory=list)
    summary: str
    why_it_matters: str
    importance: int = Field(ge=1, le=5)
    effective_date: str | None = None
    confirmed: bool = True


class Finding(BaseModel):
    observation_id: int
    observation: Observation
    analysis: Analysis
