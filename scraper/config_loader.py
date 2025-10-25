"""Utilities for loading scraper configuration templates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Sequence

from .models import ArticleConfig, ListingConfig, RecipeTemplate, StructuredDataConfig


def _coerce_iterable(value: object) -> Iterable[dict]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def load_template_payload(path: Path) -> List[dict]:
    """Return the raw template payload stored in ``path``."""

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):  # pragma: no cover - defensive guard
        raise ValueError("Template configuration must be a list")

    return payload


def save_template_payload(path: Path, payload: Sequence[dict]) -> None:
    """Persist the provided template payload back to ``path``."""

    with path.open("w", encoding="utf-8") as handle:
        json.dump(list(payload), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def parse_templates(raw_templates: Iterable[dict]) -> List[RecipeTemplate]:
    """Convert raw template dictionaries into :class:`RecipeTemplate` objects."""

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
                scraped=bool(raw.get("scraped") or raw.get("scraper")),
            )
        )

    return templates


def load_templates(path: Path) -> List[RecipeTemplate]:
    """Load all recipe templates defined in ``path``."""

    return parse_templates(load_template_payload(path))
