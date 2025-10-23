"""Application services for the recipe web interface."""
from __future__ import annotations

from typing import Optional

from .models import PaginatedResult, RecipeDetail
from .repository import RecipeQueryRepository


class RecipeService:
    """Coordinates read-only recipe use cases."""

    def __init__(self, repository: RecipeQueryRepository, page_size: int) -> None:
        self._repository = repository
        self._page_size = page_size

    def search(self, query: Optional[str], page: int) -> PaginatedResult:
        normalized_query = query.strip() if query else None
        if normalized_query == "":
            normalized_query = None
        return self._repository.search(normalized_query, page, self._page_size)

    def get(self, recipe_id: int) -> Optional[RecipeDetail]:
        return self._repository.get(recipe_id)
