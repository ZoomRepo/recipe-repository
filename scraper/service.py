"""High level orchestration for scraping and persisting recipes."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

from .config_loader import load_templates
from .extractors import ArticleScraper, ListingScraper
from .http_client import HttpClient
from .models import PendingFailure, Recipe, RecipeTemplate, ScrapeFailure
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
        self._templates_by_name: Dict[str, RecipeTemplate] = {
            template.name: template for template in self._templates
        }

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
        self._replay_failures()
        for template in self._templates:
            self._scrape_template(template)
        logger.info("Scraping completed")

    def _scrape_template(self, template: RecipeTemplate) -> None:
        logger.info("Scraping template: %s", template.name)
        try:
            article_urls = self._listing_scraper.discover(template)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Failed to discover listings for %s: %s", template.name, exc)
            self._repository.record_failure(
                ScrapeFailure(
                    template_name=template.name,
                    stage="listing",
                    source_url=template.url,
                    error_message=str(exc),
                )
            )
            return

        self._repository.resolve_failure(template.name, "listing", template.url)

        logger.info(
            "Discovered %d article URLs for %s", len(article_urls), template.name
        )

        for url in sorted(article_urls):
            try:
                recipe = self._article_scraper.scrape(template, url)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Failed to scrape %s: %s", url, exc)
                self._repository.record_failure(
                    ScrapeFailure(
                        template_name=template.name,
                        stage="article",
                        source_url=url,
                        error_message=str(exc),
                    )
                )
                continue

            if not recipe.title and not recipe.ingredients:
                logger.debug("Skipping %s due to missing essential data", url)
                continue

            self._repository.resolve_failure(template.name, "article", recipe.source_url)
            try:
                self._repository.save(recipe)
                logger.info("Saved recipe: %s", recipe.title or recipe.source_url)
                self._repository.resolve_failure(
                    template.name, "persist", recipe.source_url
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception("Failed to persist recipe %s: %s", url, exc)
                self._repository.record_failure(
                    ScrapeFailure(
                        template_name=template.name,
                        stage="persist",
                        source_url=recipe.source_url,
                        error_message=str(exc),
                        context={"recipe": recipe.as_record()},
                    )
                )

    def close(self) -> None:
        self._http_client.close()

    def __enter__(self) -> "RecipeScraperService":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _replay_failures(self) -> None:
        pending = list(self._repository.iter_pending_failures())
        if not pending:
            return

        logger.info("Replaying %d previously failed scrape attempts", len(pending))
        for failure in pending:
            template = self._templates_by_name.get(failure.template_name)
            if not template:
                logger.warning(
                    "Skipping failure %s for unknown template %s",
                    failure.id,
                    failure.template_name,
                )
                continue
            if failure.stage == "article":
                self._retry_article_failure(template, failure)
            elif failure.stage == "persist":
                self._retry_persist_failure(template, failure)
            elif failure.stage == "listing":
                logger.debug(
                    "Pending listing failure for %s will be handled during normal run",
                    template.name,
                )

    def _retry_article_failure(
        self, template: RecipeTemplate, failure: PendingFailure
    ) -> None:
        url = failure.source_url
        if not url:
            logger.debug(
                "Failure %s for %s missing URL; cannot replay article scrape",
                failure.id,
                template.name,
            )
            return

        try:
            recipe = self._article_scraper.scrape(template, url)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Replay scrape failed again for %s (%s): %s",
                url,
                template.name,
                exc,
            )
            self._repository.record_failure(
                ScrapeFailure(
                    template_name=template.name,
                    stage="article",
                    source_url=url,
                    error_message=str(exc),
                )
            )
            return

        if not recipe.title and not recipe.ingredients:
            logger.debug(
                "Replay scrape for %s produced insufficient data; skipping",
                url,
            )
            return

        self._repository.resolve_failure(template.name, "article", recipe.source_url)
        try:
            self._repository.save(recipe)
            logger.info("Replay succeeded for %s", recipe.source_url)
            self._repository.resolve_failure(
                template.name, "persist", recipe.source_url
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Replay persistence failed for %s: %s", recipe.source_url, exc
            )
            self._repository.record_failure(
                ScrapeFailure(
                    template_name=template.name,
                    stage="persist",
                    source_url=recipe.source_url,
                    error_message=str(exc),
                    context={"recipe": recipe.as_record()},
                )
            )

    def _retry_persist_failure(
        self, template: RecipeTemplate, failure: PendingFailure
    ) -> None:
        context = failure.context or {}
        recipe_payload = context.get("recipe")
        recipe: Optional[Recipe]
        if recipe_payload:
            recipe = Recipe.from_record(recipe_payload)
        elif failure.source_url:
            try:
                recipe = self._article_scraper.scrape(template, failure.source_url)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning(
                    "Unable to re-scrape %s during persistence replay: %s",
                    failure.source_url,
                    exc,
                )
                self._repository.record_failure(
                    ScrapeFailure(
                        template_name=template.name,
                        stage="article",
                        source_url=failure.source_url,
                        error_message=str(exc),
                    )
                )
                return
        else:
            logger.debug(
                "Failure %s for %s lacks context; skipping", failure.id, template.name
            )
            return

        try:
            self._repository.save(recipe)
            logger.info("Replay persistence succeeded for %s", recipe.source_url)
            self._repository.resolve_failure(
                template.name, "persist", recipe.source_url
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "Replay persistence still failing for %s: %s", recipe.source_url, exc
            )
            self._repository.record_failure(
                ScrapeFailure(
                    template_name=template.name,
                    stage="persist",
                    source_url=recipe.source_url,
                    error_message=str(exc),
                    context={"recipe": recipe.as_record()},
                )
            )
