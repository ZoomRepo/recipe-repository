from dataclasses import dataclass
from typing import Dict, Optional

import pytest

from webapp.services import NutritionService


@dataclass
class DummyRecipe:
    ingredients: list[str]
    nutrients: Optional[Dict[str, float]] = None
    raw: Optional[dict] = None


class InMemoryNutritionSource:
    def __init__(self, data: Dict[str, Dict[str, float]]):
        self._data = {key.lower(): value for key, value in data.items()}

    def get_ingredient_nutrition(self, ingredient_name: str) -> Optional[Dict[str, float]]:
        return self._data.get(ingredient_name)


@pytest.fixture
def service() -> NutritionService:
    return NutritionService()


def test_returns_existing_nutrients_when_present(service: NutritionService) -> None:
    recipe = DummyRecipe(ingredients=["egg"], nutrients={"calories": 120, "protein": "10"})
    assert service.get_nutrition_for_recipe(recipe) == {"calories": 120.0, "protein": 10.0}


def test_uses_raw_nutrition_when_available(service: NutritionService) -> None:
    recipe = DummyRecipe(ingredients=["egg"], raw={"nutrition": {"Calories": "305 kcal", "fiber": "2g"}})
    assert service.get_nutrition_for_recipe(recipe) == {"calories": 305.0, "fiber": 2.0}


def test_aggregates_from_raw_ingredient_objects(service: NutritionService) -> None:
    recipe = DummyRecipe(
        ingredients=[],
        raw={
            "ingredients": [
                {"original": "1 egg", "nutrition": {"Calories": 72, "Protein": "6g"}},
                {
                    "original": "1 tbsp olive oil",
                    "nutrients": [
                        {"name": "Calories", "amount": 119, "unit": "kcal"},
                        {"name": "Fat", "value": 13.5, "unit": "g"},
                    ],
                },
            ]
        },
    )

    assert service.get_nutrition_for_recipe(recipe) == {
        "calories": 191.0,
        "protein": 6.0,
        "fat": 13.5,
    }


def test_aggregates_from_data_source() -> None:
    source = InMemoryNutritionSource(
        {
            "chicken breast": {"calories": 120, "protein": 26},
            "olive oil": {"calories": 40, "fat": 4.5},
        }
    )
    service = NutritionService(data_source=source)
    recipe = DummyRecipe(
        ingredients=["1 chicken breast", "1 tbsp olive oil"],
        raw={"ingredients": ["1 chicken breast", "1 tbsp olive oil"]},
    )
    assert service.get_nutrition_for_recipe(recipe) == {
        "calories": 160.0,
        "protein": 26.0,
        "fat": 4.5,
    }


def test_returns_none_when_no_data_available(service: NutritionService) -> None:
    recipe = DummyRecipe(ingredients=["unknown ingredient"])
    assert service.get_nutrition_for_recipe(recipe) is None


def test_handles_nested_nutrient_collections(service: NutritionService) -> None:
    recipe = DummyRecipe(
        ingredients=["spinach"],
        raw={
            "nutrition": {
                "nutrients": [
                    {"label": "Calories", "quantity": 25, "unit": "kcal"},
                    {"label": "Sugars", "amount": "1.5 g"},
                ]
            }
        },
    )

    assert service.get_nutrition_for_recipe(recipe) == {
        "calories": 25.0,
        "sugar": 1.5,
    }
