import json
from pathlib import Path

import pytest

from scraper.scripts.find_non_food_images import (
    FOOD_KEYWORDS,
    label_is_food,
    load_recipe_records,
    normalise_label,
)


def write_json(tmp_path: Path, filename: str, payload) -> Path:
    path = tmp_path / filename
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_recipe_records_from_array(tmp_path):
    recipes = [{"title": "Soup", "image": "https://example.com/soup.jpg"}]
    path = write_json(tmp_path, "recipes.json", recipes)

    loaded = load_recipe_records(path)

    assert loaded == recipes


def test_load_recipe_records_from_wrapper(tmp_path):
    recipes = [{"title": "Salad", "image": "https://example.com/salad.jpg"}]
    path = write_json(tmp_path, "recipes.json", {"recipes": recipes})

    loaded = load_recipe_records(path)

    assert loaded == recipes


def test_load_recipe_records_invalid_structure(tmp_path):
    path = write_json(tmp_path, "recipes.json", {"not": "recipes"})

    with pytest.raises(ValueError):
        load_recipe_records(path)


@pytest.mark.parametrize(
    "label",
    [
        "Cheeseburger",
        "plate of sushi",
        "BBQ ribs",
        normalise_label(next(iter(FOOD_KEYWORDS))),
    ],
)
def test_label_is_food_true(label):
    assert label_is_food(label)


@pytest.mark.parametrize("label", ["Lawn mower", "Golden retriever", "Office building"])
def test_label_is_food_false(label):
    assert not label_is_food(label)
