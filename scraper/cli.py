"""Command line interface for the recipe scraper."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List, Optional

from .config_loader import load_templates
from .extractors import ArticleScraper, ListingScraper
from .http_client import HttpClient
from .models import RecipeTemplate
from .repository import MySqlRecipeRepository
from .service import RecipeScraperService, logger as service_logger


DEFAULT_CONFIG = Path("config/scraper_templates.json")
DEFAULT_DB_HOST = "192.168.1.99"
DEFAULT_DB_NAME = "reciperepository"
DEFAULT_DB_USER = "reciperepository"
DEFAULT_DB_PASSWORD = "Xenomorph123!"


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape recipes into MySQL")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to the scraper templates JSON file.",
    )
    parser.add_argument(
        "--db-host",
        default=DEFAULT_DB_HOST,
        help="MySQL host name.",
    )
    parser.add_argument(
        "--db-port",
        default=3306,
        type=int,
        help="MySQL port.",
    )
    parser.add_argument(
        "--db-name",
        default=DEFAULT_DB_NAME,
        help="MySQL database name.",
    )
    parser.add_argument(
        "--db-user",
        default=DEFAULT_DB_USER,
        help="MySQL user name.",
    )
    parser.add_argument(
        "--db-password",
        default=DEFAULT_DB_PASSWORD,
        help="MySQL password.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=200,
        help="Maximum number of listing pages to crawl per site.",
    )
    parser.add_argument(
        "--sites",
        nargs="*",
        help="Optional list of template names or domains to restrict scraping to.",
    )
    parser.add_argument(
        "--rerun-failures",
        action="store_true",
        help="Only replay previously stored scrape failures instead of scraping new listings.",
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=None,
        help="Maximum number of stored failures to replay when --rerun-failures is provided.",
    )
    parser.add_argument(
        "--migrate-only",
        action="store_true",
        help="Create or update database tables and exit without running the scraper.",
    )
    return parser.parse_args(argv)


class _ContextDefaultsFilter(logging.Filter):
    """Ensure log records contain source/recipe attributes for formatting."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        if not hasattr(record, "source_name"):
            record.source_name = "-"
        if not hasattr(record, "recipe"):
            record.recipe = "-"
        return True


def configure_logging(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    service_logger.setLevel(numeric_level)

    root_logger = logging.getLogger()
    if not any(getattr(handler, "_scraper_warning_handler", False) for handler in root_logger.handlers):
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        warning_log = log_dir / "scraper-warnings.log"
        file_handler = logging.FileHandler(warning_log)
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s source=%(source_name)s recipe=%(recipe)s - %(message)s"
            )
        )
        file_handler.addFilter(_ContextDefaultsFilter())
        file_handler._scraper_warning_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(file_handler)


def filter_templates(
    templates: Iterable[RecipeTemplate], selectors: Optional[List[str]]
) -> List[RecipeTemplate]:
    if not selectors:
        return list(templates)

    normalised = {item.lower() for item in selectors}
    filtered: List[RecipeTemplate] = []
    for template in templates:
        name = template.name.lower()
        domain = template.url.lower().split("//", 1)[-1].rstrip("/")
        if name in normalised or domain in normalised:
            filtered.append(template)
    return filtered


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    configure_logging(args.log_level)

    repository = MySqlRecipeRepository(
        host=args.db_host,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        port=args.db_port,
    )
    repository.ensure_schema()

    if args.migrate_only:
        logging.getLogger(__name__).info("Database schema ensured")
        return

    templates = load_templates(args.config)
    templates = filter_templates(templates, args.sites)
    if not templates:
        if args.rerun_failures:
            logging.getLogger(__name__).warning(
                "No templates matched selection; failure replay will skip unmatched entries"
            )
        else:
            logging.getLogger(__name__).warning("No templates matched selection; exiting")
            return

    with HttpClient() as http_client:
        listing_scraper = ListingScraper(http_client, max_pages=args.max_pages)
        article_scraper = ArticleScraper(http_client)
        with RecipeScraperService(
            templates,
            repository,
            http_client=http_client,
            listing_scraper=listing_scraper,
            article_scraper=article_scraper,
        ) as service:
            if args.rerun_failures:
                service.replay_failures(max_failures=args.max_failures)
            else:
                service.run()


if __name__ == "__main__":
    main()
