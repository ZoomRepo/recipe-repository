"""Utilities for loading scraper configuration templates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import ArticleConfig, ListingConfig, RecipeTemplate, StructuredDataConfig


def _coerce_iterable(value: object) -> Iterable[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_templates(path: Path) -> List[RecipeTemplate]:
    """Load all recipe templates defined in ``path``."""

    with path.open("r", encoding="utf-8") as handle:
        raw_templates = json.load(handle)

    templates: List[RecipeTemplate] = []
    for raw in raw_templates:
        listings: List[ListingConfig] = []
        recipes_section = raw.get("recipes", {})
        for listing in _coerce_iterable(recipes_section.get("listing")):
            listings.append(
                ListingConfig(
                    url=listing["url"],
                    link_selector=listing["link_selector"],
                    pagination_selector=listing.get("pagination_selector"),
                )
            )

        article_config = ArticleConfig(selectors=raw.get("article", {}))
        structured_data_raw = raw.get("structured_data", {})
        structured_config = StructuredDataConfig(
            enabled=structured_data_raw.get("enabled", False),
            json_ld_selector=structured_data_raw.get("json_ld_selector"),
            json_ld_path=structured_data_raw.get("json_ld_path"),
        )

        templates.append(
            RecipeTemplate(
                name=raw["name"],
                url=raw["url"],
                type=raw.get("type", "cooking"),
                listings=listings,
                article=article_config,
                structured_data=structured_config,
            )
        )

    return templates
