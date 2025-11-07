"""Domain models for the recipe web application."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional


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
    ingredients: List[str]
    raw: Optional[dict]
    nutrients: Optional[Dict[str, float]]


@dataclass(frozen=True)
class RecipeDetail(RecipeSummary):
    """Complete recipe representation."""

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
        """Iterate over page numbers with an initial block then a sliding window."""

        total_pages = self.total_pages

        if total_pages <= 10:
            return range(1, total_pages + 1)

        if self.page < 10:
            return range(1, 11)

        start = max(1, self.page - 5)
        end = min(total_pages, self.page + 5)

        if end - start < 10 and start > 1:
            start = max(1, end - 10)

        return range(start, end + 1)
