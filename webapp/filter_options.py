"""Filter option definitions for recipe search."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class FilterOption:
    """Represents a selectable filter with associated keyword triggers."""

    value: str
    label: str
    keywords: Tuple[str, ...]

    def normalized_keywords(self) -> Tuple[str, ...]:
        """Return the lower-case keywords used to match this option."""

        return tuple(sorted({keyword.strip().lower() for keyword in self.keywords if keyword}))


def _option(value: str, label: str, *keywords: str) -> FilterOption:
    return FilterOption(value=value, label=label, keywords=tuple(keywords))


CUISINE_OPTIONS: Tuple[FilterOption, ...] = (
    _option("american", "American", "american", "southern", "bbq", "barbecue", "tex-mex", "comfort food"),
    _option("british", "British", "british", "english", "uk", "united kingdom", "scottish", "welsh"),
    _option("chinese", "Chinese", "chinese", "szechuan", "cantonese", "dim sum", "stir-fry"),
    _option("french", "French", "french", "provencal", "bistro", "bourguignon"),
    _option("greek", "Greek", "greek", "souvlaki", "feta", "tzatziki", "gyro"),
    _option("indian", "Indian", "indian", "curry", "masala", "tikka", "dal", "biryani"),
    _option("italian", "Italian", "italian", "pasta", "risotto", "gnocchi", "antipasti"),
    _option("japanese", "Japanese", "japanese", "sushi", "ramen", "teriyaki", "tempura"),
    _option("mexican", "Mexican", "mexican", "taco", "enchilada", "quesadilla", "salsa"),
    _option("middle_eastern", "Middle Eastern", "middle eastern", "lebanese", "turkish", "persian", "shawarma", "falafel"),
    _option("spanish", "Spanish", "spanish", "paella", "tapas", "chorizo", "gazpacho"),
    _option("thai", "Thai", "thai", "lemongrass", "pad thai", "green curry", "massaman"),
    _option("mediterranean", "Mediterranean", "mediterranean", "mezze", "olive", "mediterranean diet"),
)

MEAL_OPTIONS: Tuple[FilterOption, ...] = (
    _option("breakfast", "Breakfast", "breakfast", "brunch", "morning", "pancake", "omelette"),
    _option("lunch", "Lunch", "lunch", "midday", "sandwich", "wrap", "salad"),
    _option("dinner", "Dinner", "dinner", "supper", "main course", "entree", "evening meal"),
    _option("starter", "Starter", "starter", "appetizer", "appetiser", "hors d'oeuvre", "snack"),
    _option("dessert", "Dessert", "dessert", "pudding", "sweet", "cake", "ice cream"),
    _option("drink", "Drink", "drink", "beverage", "cocktail", "smoothie", "juice"),
)

DIET_OPTIONS: Tuple[FilterOption, ...] = (
    _option("vegetarian", "Vegetarian", "vegetarian", "meatless", "veggie"),
    _option("vegan", "Vegan", "vegan", "plant-based", "plant based"),
    _option("gluten_free", "Gluten-Free", "gluten-free", "gluten free", "coeliac"),
    _option("keto", "Keto", "keto", "ketogenic", "low carb", "low-carb"),
    _option("paleo", "Paleo", "paleo", "primal"),
    _option("healthy", "Healthy", "healthy", "light", "wholesome", "clean eating", "low-fat", "low fat"),
)


def _build_lookup(options: Sequence[FilterOption]) -> Mapping[str, FilterOption]:
    return {option.value: option for option in options}


CUISINE_LOOKUP = _build_lookup(CUISINE_OPTIONS)
MEAL_LOOKUP = _build_lookup(MEAL_OPTIONS)
DIET_LOOKUP = _build_lookup(DIET_OPTIONS)


def normalize_selection(values: Iterable[str], lookup: Mapping[str, FilterOption]) -> List[str]:
    """Normalize user selections against a lookup table."""

    normalized: List[str] = []
    seen = set()
    for raw_value in values:
        if not raw_value:
            continue
        candidate = str(raw_value).strip().lower().replace(" ", "_").replace("-", "_")
        if candidate in lookup and candidate not in seen:
            normalized.append(candidate)
            seen.add(candidate)
    return normalized


def labels_for(values: Iterable[str], lookup: Mapping[str, FilterOption]) -> List[str]:
    """Return display labels for the provided option values."""

    return [lookup[value].label for value in values if value in lookup]


__all__ = [
    "FilterOption",
    "CUISINE_OPTIONS",
    "MEAL_OPTIONS",
    "DIET_OPTIONS",
    "CUISINE_LOOKUP",
    "MEAL_LOOKUP",
    "DIET_LOOKUP",
    "normalize_selection",
    "labels_for",
]
