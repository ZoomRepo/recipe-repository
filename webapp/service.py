"""Application services for the recipe web interface."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from .models import PaginatedResult, RecipeDetail, SourcePreference
from .filter_options import (
    CUISINE_LOOKUP,
    DIET_LOOKUP,
    MEAL_LOOKUP,
    normalize_selection,
)
from .repository import RecipeQueryRepository


class RecipeService:
    """Coordinates read-only recipe use cases."""

    def __init__(self, repository: RecipeQueryRepository, page_size: int) -> None:
        self._repository = repository
        self._page_size = page_size

    def search(
        self,
        query: Optional[str],
        page: int,
        ingredients: Optional[Iterable[str]] = None,
        cuisines: Optional[Sequence[str]] = None,
        meals: Optional[Sequence[str]] = None,
        diets: Optional[Sequence[str]] = None,
    ) -> PaginatedResult:
        normalized_query = query.strip() if query else None
        if normalized_query == "":
            normalized_query = None

        normalized_ingredients = None
        if ingredients:
            normalized_ingredients = []
            seen = set()
            for value in ingredients:
                if value is None:
                    continue
                cleaned = value.strip().lower()
                if not cleaned or cleaned in seen:
                    continue
                normalized_ingredients.append(cleaned)
                seen.add(cleaned)

        normalized_cuisines = normalize_selection(cuisines or [], CUISINE_LOOKUP)
        normalized_meals = normalize_selection(meals or [], MEAL_LOOKUP)
        normalized_diets = normalize_selection(diets or [], DIET_LOOKUP)

        return self._repository.search(
            normalized_query,
            normalized_ingredients,
            page,
            self._page_size,
            normalized_cuisines,
            normalized_meals,
            normalized_diets,
        )

    def get(self, recipe_id: int) -> Optional[RecipeDetail]:
        return self._repository.get(recipe_id)

    def list_source_preferences(self) -> list[SourcePreference]:
        return self._repository.list_source_preferences()

    def set_hotlink_preference(self, source_name: str, enabled: bool) -> None:
        normalized = (source_name or "").strip()
        if not normalized:
            raise ValueError("source_name must not be empty")
        self._repository.set_hotlink_preference(normalized, enabled)
