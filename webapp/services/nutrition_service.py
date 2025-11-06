"""Helpers for enriching recipes with nutrition information."""
from __future__ import annotations

from collections import Counter
import re
from typing import Dict, Iterable, Mapping, Optional, Protocol, Sequence

SUPPORTED_NUTRIENTS: tuple[str, ...] = (
    "calories",
    "protein",
    "carbohydrates",
    "fat",
    "fiber",
    "sugar",
)


class NutritionDataSource(Protocol):
    """Protocol describing a provider of ingredient-level nutrition data."""

    def get_ingredient_nutrition(self, ingredient_name: str) -> Optional[Mapping[str, float]]:
        """Return nutrient data for *ingredient_name* or ``None`` if unavailable."""


class NutritionService:
    """Compute or retrieve nutrition information for recipes."""

    def __init__(
        self,
        data_source: Optional[NutritionDataSource] = None,
        supported_nutrients: Sequence[str] = SUPPORTED_NUTRIENTS,
    ) -> None:
        self._data_source = data_source
        self._supported_keys = tuple({key.lower() for key in supported_nutrients})

    def get_nutrition_for_recipe(self, recipe: object) -> Optional[Dict[str, float]]:
        """Return a nutrient breakdown for *recipe* if available."""

        if recipe is None:
            return None

        recipe_nutrients = getattr(recipe, "nutrients", None)
        normalized = self._normalize_nutrients(recipe_nutrients)
        if normalized:
            return normalized

        raw = getattr(recipe, "raw", None)
        raw_nutrients = None
        raw_ingredients: Optional[Iterable[str]] = None
        if isinstance(raw, Mapping):
            raw_nutrients = self._normalize_nutrients(raw.get("nutrition"))
            if not raw_nutrients:
                ingredients_candidate = raw.get("ingredients")
                if isinstance(ingredients_candidate, (list, tuple)):
                    raw_ingredients = [
                        str(item) for item in ingredients_candidate if isinstance(item, str)
                    ]

        if raw_nutrients:
            return raw_nutrients

        ingredient_list = getattr(recipe, "ingredients", None)
        if ingredient_list is None and raw_ingredients is not None:
            ingredient_list = raw_ingredients

        if not ingredient_list or self._data_source is None:
            return None

        totals: Counter[str] = Counter()
        found = False
        for ingredient in ingredient_list:
            if not isinstance(ingredient, str):
                continue
            normalized_name = self._normalize_ingredient_name(ingredient)
            if not normalized_name:
                continue
            nutrient_data = self._data_source.get_ingredient_nutrition(normalized_name)
            if not nutrient_data:
                continue
            found = True
            for key in self._supported_keys:
                value = nutrient_data.get(key)
                if value is None:
                    continue
                coerced = self._coerce_to_float(value)
                if coerced is None:
                    continue
                totals[key] += coerced

        if not found:
            return None

        return {key: round(totals[key], 2) for key in totals if totals[key]}

    def _normalize_nutrients(self, nutrients: object) -> Optional[Dict[str, float]]:
        if not nutrients:
            return None
        if not isinstance(nutrients, Mapping):
            return None

        normalized: Dict[str, float] = {}
        for key, value in nutrients.items():
            if not isinstance(key, str):
                continue
            key_lower = key.lower()
            if key_lower not in self._supported_keys:
                continue
            coerced = self._coerce_to_float(value)
            if coerced is None:
                continue
            normalized[key_lower] = round(coerced, 2)
        return normalized or None

    @staticmethod
    def _coerce_to_float(value: object) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip().lower()
            if not stripped:
                return None
            # Remove common unit suffixes such as "g", "mg", "kcal"
            cleaned = re.sub(r"(g|mg|kcal)$", "", stripped).strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    @staticmethod
    def _normalize_ingredient_name(raw_name: str) -> str:
        name = raw_name.lower()
        name = re.sub(r"\([^)]*\)", " ", name)
        name = re.sub(r"[^a-z\s]", " ", name)
        name = re.sub(r"\b(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|oz|ounces?|pounds?|lbs?|grams?|g|kg|ml|l|cloves?|slices?)\b", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip()
