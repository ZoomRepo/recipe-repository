"""Backfill job to index all recipes into Elasticsearch."""
from __future__ import annotations

import argparse
import logging
from contextlib import contextmanager
from itertools import islice
from typing import Iterable, Iterator, List

import mysql.connector

from elasticsearch.exceptions import AuthenticationException
from elasticsearch.helpers import BulkIndexError

from webapp.config import AppConfig
from webapp.search.indexer import RecipeDocumentBuilder, RecipeSearchIndexer

logger = logging.getLogger(__name__)


DEFAULT_BATCH_SIZE = 500


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reindex all recipes from MySQL into Elasticsearch",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of recipes to index per batch.",
    )
    return parser.parse_args()


def _chunked(iterable: Iterable[dict], size: int) -> Iterator[List[dict]]:
    iterator = iter(iterable)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            return
        yield batch


@contextmanager
def _recipe_stream(config: AppConfig) -> Iterator[Iterator[dict]]:
    db = config.database
    query = """
        SELECT
            id,
            source_name,
            source_url,
            title,
            description,
            ingredients,
            instructions,
            prep_time,
            cook_time,
            total_time,
            servings,
            image,
            author,
            categories,
            tags,
            raw,
            created_at,
            updated_at
        FROM recipes
        ORDER BY id ASC
    """
    connection = mysql.connector.connect(
        host=db.host,
        port=db.port,
        user=db.user,
        password=db.password,
        database=db.database,
        charset="utf8mb4",
        use_unicode=True,
    )
    cursor = connection.cursor(dictionary=True, buffered=True)
    try:
        cursor.execute(query)
        def _iter_rows() -> Iterator[dict]:
            for row in cursor:
                yield dict(row)

        yield _iter_rows()
    finally:
        try:
            cursor.close()
        finally:
            connection.close()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(level=logging.INFO)
    config = AppConfig.from_env()
    indexer = RecipeSearchIndexer.from_config(config)

    logger.info("Starting reindex into '%s'", config.elasticsearch.recipe_index)
    with _recipe_stream(config) as rows:
        documents = (RecipeDocumentBuilder.from_row(row) for row in rows)

        total = 0
        for batch in _chunked(documents, max(args.batch_size, 1)):
            try:
                indexer.bulk_index(batch)
            except AuthenticationException as exc:  # pragma: no cover - env specific
                logger.error(
                    "Failed to authenticate to Elasticsearch at %s. "
                    "Set ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD if the "
                    "cluster requires credentials.",
                    config.elasticsearch.url,
                )
                raise SystemExit(1) from exc
            except BulkIndexError as exc:
                logger.error(
                    "Bulk indexing failed for a batch; aborting after %d indexed recipes",
                    total,
                )
                raise SystemExit(1) from exc
            total += len(batch)
            logger.info("Indexed %d recipes so far", total)

    logger.info("Reindex complete. %d recipes indexed.", total)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
