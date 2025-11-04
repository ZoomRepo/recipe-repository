"""Filter option definitions for recipe search."""
from __future__ import annotations

from dataclasses import dataclass
import re
from string import capwords
from typing import Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


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


def build_lookup(options: Sequence[FilterOption]) -> MutableMapping[str, FilterOption]:
    """Create a mapping of option values to their definitions."""

    return {option.value: option for option in options}


def merge_options(
    base_options: Sequence[FilterOption], additional: Sequence[FilterOption]
) -> Tuple[FilterOption, ...]:
    """Combine filter options ensuring de-duplication and alphabetical ordering."""

    combined: MutableMapping[str, FilterOption] = {
        option.value: option for option in base_options
    }
    for option in additional:
        combined.setdefault(option.value, option)
    return tuple(sorted(combined.values(), key=lambda opt: opt.label.lower()))


_CUISINE_EXCLUDED_VALUES = {
    "",  # defensive guard
    "appetizer",
    "appetizers",
    "baking",
    "bbq",
    "beverage",
    "beverages",
    "bread",
    "breakfast",
    "brunch",
    "cocktail",
    "cocktails",
    "dessert",
    "desserts",
    "dinner",
    "drink",
    "drinks",
    "gluten free",
    "gluten-free",
    "healthy",
    "keto",
    "lunch",
    "main course",
    "paleo",
    "salad",
    "salads",
    "soup",
    "soups",
    "starter",
    "starters",
    "vegan",
    "vegetarian",
}

_CUISINE_EXCLUDED_TOKENS = {
    "appetizer",
    "appetizers",
    "baking",
    "bbq",
    "beverage",
    "beverages",
    "bread",
    "breakfast",
    "brunch",
    "cake",
    "cakes",
    "casserole",
    "casseroles",
    "cheese",
    "chicken",
    "comfort",
    "cookies",
    "cooking",
    "dessert",
    "desserts",
    "dinner",
    "drink",
    "drinks",
    "easter",
    "easy",
    "fast",
    "fish",
    "free",
    "fried",
    "gluten",
    "grill",
    "grilled",
    "healthy",
    "holiday",
    "instant",
    "kid",
    "kids",
    "keto",
    "lamb",
    "lunch",
    "meat",
    "noodle",
    "noodles",
    "paleo",
    "pastry",
    "pasta",
    "pie",
    "pies",
    "pork",
    "pressure",
    "quick",
    "roast",
    "salad",
    "salads",
    "seafood",
    "slow",
    "snack",
    "snacks",
    "soup",
    "soups",
    "spring",
    "stew",
    "stews",
    "summer",
    "thanksgiving",
    "turkey",
    "vegan",
    "vegetarian",
    "winter",
}

_CUISINE_ACCEPTED_SUFFIXES = ("ian", "ean", "an", "ese", "ish", "i", "ic", "ch", "que")

_CUISINE_ACCEPTED_LAST_TOKENS = {
    "african",
    "american",
    "arabic",
    "asian",
    "atlantic",
    "australian",
    "balkan",
    "baltic",
    "caribbean",
    "central",
    "cuisine",
    "eastern",
    "european",
    "fusion",
    "islander",
    "foods",
    "food",
    "latin",
    "levantine",
    "mediterranean",
    "middle",
    "northern",
    "pacific",
    "recipes",
    "scandinavian",
    "southern",
    "style",
    "western",
}

_CUISINE_SPECIAL_CASES = {
    "middle eastern",
    "middle east",
    "north african",
    "east african",
    "west african",
    "south african",
    "latin american",
    "central american",
    "south american",
    "south asian",
    "southeast asian",
    "south east asian",
    "east asian",
    "west asian",
    "north american",
    "tex mex",
    "tex-mex",
    "british",
    "english",
    "irish",
    "scottish",
    "welsh",
    "scandinavian",
    "nordic",
}


def _normalize_cuisine_candidate(raw_value: str) -> Optional[str]:
    if not raw_value:
        return None

    cleaned = re.sub(r"\s+", " ", str(raw_value)).strip()
    if not cleaned:
        return None

    normalized = cleaned.lower()
    if normalized in _CUISINE_EXCLUDED_VALUES:
        return None

    normalized = (
        normalized.replace("&", " and ")
        .replace("/", " ")
        .replace("'", "'")
        .replace("\u2019", "'")
    )
    normalized = re.sub(r"\s+", " ", normalized)

    tokens = [token for token in re.split(r"[\s-]+", normalized) if token]
    if not tokens:
        return None

    if any(token in _CUISINE_EXCLUDED_TOKENS for token in tokens):
        return None

    candidate = " ".join(tokens)
    if candidate in _CUISINE_SPECIAL_CASES:
        return capwords(candidate)

    last_token = tokens[-1]
    if last_token in {"cuisine", "cuisines"} and len(tokens) > 1:
        tokens = tokens[:-1]
        last_token = tokens[-1]
        candidate = " ".join(tokens)

    if last_token in _CUISINE_ACCEPTED_LAST_TOKENS:
        pass
    elif any(last_token.endswith(suffix) for suffix in _CUISINE_ACCEPTED_SUFFIXES):
        if last_token in _CUISINE_EXCLUDED_TOKENS:
            return None
    else:
        return None

    if len(candidate) < 3 or len(candidate) > 40:
        return None

    return capwords(candidate)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def _keywords_from_label(label: str, original: str) -> Tuple[str, ...]:
    base = label.lower()
    original_normalized = re.sub(r"\s+", " ", original.strip().lower())
    keywords = {base, original_normalized}
    tokens = [token for token in re.split(r"[\s/&-]+", base) if len(token) > 2]
    keywords.update(tokens)
    keywords.add(f"{base} cuisine")
    keywords.add(base.replace(" cuisine", ""))
    return tuple(sorted({keyword for keyword in keywords if keyword}))


def build_dynamic_cuisine_options(
    raw_labels: Iterable[str],
    existing: Sequence[FilterOption],
) -> List[FilterOption]:
    """Create filter options for cuisines discovered in the data store."""

    existing_values = {option.value for option in existing}
    seen_values = set()
    dynamic: List[FilterOption] = []
    for label in raw_labels:
        normalized_label = _normalize_cuisine_candidate(label)
        if not normalized_label:
            continue
        value = _slugify(normalized_label)
        if not value or value in existing_values or value in seen_values:
            continue
        option = FilterOption(
            value=value,
            label=normalized_label,
            keywords=_keywords_from_label(normalized_label, str(label)),
        )
        seen_values.add(value)
        dynamic.append(option)
    dynamic.sort(key=lambda option: option.label.lower())
    return dynamic


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
CUISINE_LOOKUP = build_lookup(CUISINE_OPTIONS)
MEAL_LOOKUP = build_lookup(MEAL_OPTIONS)
DIET_LOOKUP = build_lookup(DIET_OPTIONS)


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
    "build_lookup",
    "merge_options",
    "build_dynamic_cuisine_options",
    "normalize_selection",
    "labels_for",
]
