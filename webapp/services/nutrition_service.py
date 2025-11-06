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
            if raw_nutrients:
                return raw_nutrients

            raw_ingredients_data = raw.get("ingredients")
            (
                raw_ingredients,
                aggregated_from_raw,
            ) = self._normalize_raw_ingredients(raw_ingredients_data)
            if aggregated_from_raw:
                return aggregated_from_raw

        ingredient_list = getattr(recipe, "ingredients", None)
        if ingredient_list is None and raw_ingredients:
            ingredient_list = list(raw_ingredients)

        if not ingredient_list:
            return None

        if self._data_source is None:
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

        if isinstance(nutrients, Mapping):
            normalized: Dict[str, float] = {}
            for key, value in nutrients.items():
                if not isinstance(key, str):
                    continue
                key_lower = key.lower()
                if key_lower == "nutrients":
                    nested = self._normalize_nutrients(value)
                    if nested:
                        normalized.update(nested)
                    continue
                alias = self._canonical_key(key_lower)
                if not alias:
                    continue
                coerced = self._coerce_nested_value(value)
                if coerced is None:
                    continue
                normalized[alias] = round(coerced, 2)
            return normalized or None

        if isinstance(nutrients, Sequence):
            normalized: Dict[str, float] = {}
            for entry in nutrients:
                if not isinstance(entry, Mapping):
                    continue
                name = entry.get("name") or entry.get("title") or entry.get("label")
                if not isinstance(name, str):
                    continue
                alias = self._canonical_key(name.lower())
                if not alias:
                    continue
                value = entry.get("amount")
                if value is None:
                    value = entry.get("value")
                if value is None and "unit" in entry:
                    value = entry.get("quantity")
                coerced = self._coerce_nested_value(value)
                if coerced is None:
                    coerced = self._coerce_nested_value(entry)
                if coerced is None:
                    continue
                normalized[alias] = round(coerced, 2)
            return normalized or None

        return None

    def _normalize_raw_ingredients(
        self, raw_ingredients: object
    ) -> tuple[list[str], Optional[Dict[str, float]]]:
        if not isinstance(raw_ingredients, Sequence):
            return ([], None)

        collected: list[str] = []
        totals: Counter[str] = Counter()
        found = False
        for entry in raw_ingredients:
            if isinstance(entry, str):
                collected.append(entry)
                continue
            if not isinstance(entry, Mapping):
                continue
            name = (
                entry.get("original")
                or entry.get("originalString")
                or entry.get("text")
                or entry.get("name")
                or entry.get("ingredient")
            )
            if isinstance(name, str):
                collected.append(name)
            ingredient_nutrients = None
            if "nutrition" in entry:
                ingredient_nutrients = self._normalize_nutrients(entry.get("nutrition"))
            if not ingredient_nutrients and "nutrients" in entry:
                ingredient_nutrients = self._normalize_nutrients(entry.get("nutrients"))
            if not ingredient_nutrients:
                continue
            found = True
            for key, value in ingredient_nutrients.items():
                totals[key] += value
        aggregated = (
            {key: round(totals[key], 2) for key in totals if totals[key]}
            if found
            else None
        )
        return collected, aggregated

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

    def _coerce_nested_value(self, value: object) -> Optional[float]:
        coerced = self._coerce_to_float(value)
        if coerced is not None:
            return coerced
        if isinstance(value, Mapping):
            if "amount" in value:
                coerced = self._coerce_to_float(value.get("amount"))
                if coerced is not None:
                    return coerced
            if "value" in value:
                coerced = self._coerce_to_float(value.get("value"))
                if coerced is not None:
                    return coerced
        return None

    def _canonical_key(self, key: str) -> Optional[str]:
        normalized = key.strip().lower()
        aliases = {
            "calories": "calories",
            "energy": "calories",
            "kilocalories": "calories",
            "kcal": "calories",
            "protein": "protein",
            "proteins": "protein",
            "carbohydrates": "carbohydrates",
            "carbs": "carbohydrates",
            "carbohydrate": "carbohydrates",
            "fat": "fat",
            "fats": "fat",
            "lipid": "fat",
            "fiber": "fiber",
            "fibre": "fiber",
            "dietary fiber": "fiber",
            "sugar": "sugar",
            "sugars": "sugar",
        }
        resolved = aliases.get(normalized)
        if resolved and resolved in self._supported_keys:
            return resolved
        if normalized in self._supported_keys:
            return normalized
        return None

    @staticmethod
    def _normalize_ingredient_name(raw_name: str) -> str:
        name = raw_name.lower()
        name = re.sub(r"\([^)]*\)", " ", name)
        name = re.sub(r"[^a-z\s]", " ", name)
        name = re.sub(r"\b(?:cups?|tablespoons?|teaspoons?|tbsp|tsp|oz|ounces?|pounds?|lbs?|grams?|g|kg|ml|l|cloves?|slices?)\b", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name.strip()
