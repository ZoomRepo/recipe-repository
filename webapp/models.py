"""Domain models for the recipe web application."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class RecipeSummary:
    """Light-weight representation used on listing pages."""

    id: int
    title: Optional[str]
    source_name: str
    source_url: str
    description: Optional[str]
    image: Optional[str]
    updated_at: Optional[datetime]


@dataclass(frozen=True)
class RecipeDetail(RecipeSummary):
    """Complete recipe representation."""

    ingredients: List[str]
    instructions: List[str]
    prep_time: Optional[str]
    cook_time: Optional[str]
    total_time: Optional[str]
    servings: Optional[str]
    author: Optional[str]
    categories: List[str]
    tags: List[str]
    raw: Optional[dict]


@dataclass(frozen=True)
class PaginatedResult:
    """Container holding paginated recipe summaries."""

    items: List[RecipeSummary]
    total: int
    page: int
    page_size: int
    query: Optional[str] = None

    @property
    def total_pages(self) -> int:
        if self.total == 0:
            return 1
        quotient, remainder = divmod(self.total, self.page_size)
        return quotient + (1 if remainder else 0)

    def iter_pages(self) -> Iterable[int]:
        return range(1, self.total_pages + 1)
