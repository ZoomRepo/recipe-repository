"""Application services for the recipe web interface."""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence, Tuple

from .filter_options import (
    CUISINE_OPTIONS,
    DIET_LOOKUP,
    MEAL_LOOKUP,
    FilterOption,
    build_dynamic_cuisine_options,
    build_lookup,
    merge_options,
    normalize_selection,
)
from .models import PaginatedResult, RecipeDetail
from .repository import RecipeQueryRepository


class RecipeService:
    """Coordinates read-only recipe use cases."""

    def __init__(self, repository: RecipeQueryRepository, page_size: int) -> None:
        self._repository = repository
        self._page_size = page_size
        self._cuisine_options: Optional[Tuple[FilterOption, ...]] = None
        self._cuisine_lookup: Optional[Mapping[str, FilterOption]] = None

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

        cuisine_lookup = self.cuisine_lookup()
        normalized_cuisines = normalize_selection(cuisines or [], cuisine_lookup)
        if cuisines and len(normalized_cuisines) < len(cuisines):
            # New cuisines may have been added since the options were loaded
            self.refresh_cuisine_filters()
            cuisine_lookup = self.cuisine_lookup()
            normalized_cuisines = normalize_selection(cuisines or [], cuisine_lookup)
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
            cuisine_lookup=cuisine_lookup,
        )

    def get(self, recipe_id: int) -> Optional[RecipeDetail]:
        return self._repository.get(recipe_id)

    def cuisine_options(self) -> Tuple[FilterOption, ...]:
        self._ensure_cuisine_filters()
        assert self._cuisine_options is not None
        return self._cuisine_options

    def cuisine_lookup(self) -> Mapping[str, FilterOption]:
        self._ensure_cuisine_filters()
        assert self._cuisine_lookup is not None
        return self._cuisine_lookup

    def refresh_cuisine_filters(self) -> None:
        self._cuisine_options = None
        self._cuisine_lookup = None
        self._ensure_cuisine_filters()

    def _ensure_cuisine_filters(self) -> None:
        if self._cuisine_options is not None and self._cuisine_lookup is not None:
            return
        dynamic_labels = self._repository.list_cuisine_labels()
        dynamic_options = build_dynamic_cuisine_options(dynamic_labels, CUISINE_OPTIONS)
        combined = merge_options(CUISINE_OPTIONS, tuple(dynamic_options))
        self._cuisine_options = combined
        self._cuisine_lookup = build_lookup(combined)
