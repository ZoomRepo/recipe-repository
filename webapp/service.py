"""Application services for the recipe web interface."""
from __future__ import annotations

from dataclasses import replace
import logging
from typing import Iterable, Optional, Sequence

from .models import PaginatedResult, RecipeDetail
from .filter_options import (
    CUISINE_LOOKUP,
    DIET_LOOKUP,
    MEAL_LOOKUP,
    normalize_selection,
)
from .repository import RecipeQueryRepository
from .search.repository import SearchRepository
from .services import NutritionService


logger = logging.getLogger(__name__)


class RecipeService:
    """Coordinates read-only recipe use cases."""

    def __init__(
        self,
        search_repository: SearchRepository,
        detail_repository: RecipeQueryRepository,
        page_size: int,
        nutrition_service: Optional[NutritionService] = None,
    ) -> None:
        self._search_repository = search_repository
        self._detail_repository = detail_repository
        self._page_size = page_size
        self._nutrition_service = nutrition_service

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

        try:
            results = self._search_repository.search(
                normalized_query,
                normalized_ingredients,
                page,
                self._page_size,
                normalized_cuisines,
                normalized_meals,
                normalized_diets,
            )
        except Exception:  # noqa: BLE001
            logger.exception("Primary search repository failed; falling back to SQL")
            results = self._detail_repository.search(
                normalized_query,
                normalized_ingredients,
                page,
                self._page_size,
                normalized_cuisines,
                normalized_meals,
                normalized_diets,
            )

        return self._with_nutrition(results)

    def get(self, recipe_id: int) -> Optional[RecipeDetail]:
        recipe = self._detail_repository.get(recipe_id)
        if recipe is None:
            return None
        if not self._nutrition_service:
            return recipe
        nutrients = self._nutrition_service.get_nutrition_for_recipe(recipe)
        if nutrients is None:
            return recipe
        return replace(recipe, nutrients=nutrients)

    def _with_nutrition(self, results: PaginatedResult) -> PaginatedResult:
        if not self._nutrition_service:
            return results

        enriched_items = []
        for item in results.items:
            nutrients = self._nutrition_service.get_nutrition_for_recipe(item)
            if nutrients is None:
                enriched_items.append(item)
            else:
                enriched_items.append(replace(item, nutrients=nutrients))
        return PaginatedResult(
            items=enriched_items,
            total=results.total,
            page=results.page,
            page_size=results.page_size,
            query=results.query,
            backend=results.backend,
        )
