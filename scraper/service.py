"""High level orchestration for scraping and persisting recipes."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

from .config_loader import load_templates
from .extractors import ArticleScraper, ListingScraper
from .http_client import HttpClient
from .models import RecipeTemplate
from .repository import RecipeRepository


logger = logging.getLogger(__name__)


class RecipeScraperService:
    """Coordinates listing discovery, article extraction, and persistence."""

    def __init__(
        self,
        templates: Iterable[RecipeTemplate],
        repository: RecipeRepository,
        http_client: Optional[HttpClient] = None,
        listing_scraper: Optional[ListingScraper] = None,
        article_scraper: Optional[ArticleScraper] = None,
    ) -> None:
        self._templates = list(templates)
        self._repository = repository
        self._http_client = http_client or HttpClient()
        self._listing_scraper = listing_scraper or ListingScraper(self._http_client)
        self._article_scraper = article_scraper or ArticleScraper(self._http_client)

    @classmethod
    def from_config(
        cls,
        config_path: Path,
        repository: RecipeRepository,
        http_client: Optional[HttpClient] = None,
        listing_scraper: Optional[ListingScraper] = None,
        article_scraper: Optional[ArticleScraper] = None,
    ) -> "RecipeScraperService":
        templates = load_templates(config_path)
        return cls(
            templates,
            repository,
            http_client=http_client,
            listing_scraper=listing_scraper,
            article_scraper=article_scraper,
        )

    def run(self) -> None:
        logger.info("Starting recipe scraping for %d templates", len(self._templates))
        for template in self._templates:
            self._scrape_template(template)
        logger.info("Scraping completed")

    def _scrape_template(self, template: RecipeTemplate) -> None:
        logger.info("Scraping template: %s", template.name)
        try:
            article_urls = self._listing_scraper.discover(template)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to discover listings for %s: %s", template.name, exc)
            return

        logger.info(
            "Discovered %d article URLs for %s", len(article_urls), template.name
        )

        for url in sorted(article_urls):
            try:
                recipe = self._article_scraper.scrape(template, url)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Failed to scrape %s: %s", url, exc)
                continue

            if not recipe.title and not recipe.ingredients:
                logger.debug("Skipping %s due to missing essential data", url)
                continue

            try:
                self._repository.save(recipe)
                logger.info("Saved recipe: %s", recipe.title or recipe.source_url)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Failed to persist recipe %s: %s", url, exc)

    def close(self) -> None:
        self._http_client.close()

    def __enter__(self) -> "RecipeScraperService":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
