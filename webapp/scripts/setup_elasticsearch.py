"""Initialise Elasticsearch indices required by the web application."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from webapp.config import AppConfig
from webapp.scripts.es_utils import ES_EXCEPTIONS, build_client, index_exists


DEFAULT_MAPPING_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "elasticsearch" / "recipe_index.json"
)


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the recipe Elasticsearch index using the configured mapping.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_MAPPING_PATH,
        help="Path to the index mapping JSON file. Defaults to '%(default)s'.",
    )
    parser.add_argument(
        "--index",
        help="Override the index name configured in the environment.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete any existing index before creating it again.",
    )
    return parser.parse_args(list(argv))


def _load_mapping(path: Path) -> dict:
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SystemExit(f"Mapping file '{path}' does not exist.")
    try:
        return json.loads(contents)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse mapping file '{path}': {exc}")


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv or [])
    config = AppConfig.from_env()
    es_config = config.elasticsearch
    index_name = args.index or es_config.recipe_index

    mapping = _load_mapping(args.mapping)
    settings = mapping.get("settings")
    mappings = mapping.get("mappings")
    aliases = mapping.get("aliases")

    try:
        client = build_client(config)
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to create Elasticsearch client: {exc}", file=sys.stderr)
        return 2

    try:
        exists = index_exists(client, index_name)
    except ES_EXCEPTIONS as exc:
        print(f"Failed to inspect index '{index_name}': {exc}", file=sys.stderr)
        return 2

    if exists:
        if args.force:
            try:
                client.indices.delete(index=index_name)
                print(f"Deleted existing index '{index_name}'.")
            except ES_EXCEPTIONS as exc:
                print(f"Failed to delete index '{index_name}': {exc}", file=sys.stderr)
                return 2
        else:
            print(f"Index '{index_name}' already exists; no action taken.")
            return 0

    try:
        client.indices.create(
            index=index_name,
            settings=settings,
            mappings=mappings,
            aliases=aliases,
        )
    except ES_EXCEPTIONS as exc:
        print(f"Failed to create index '{index_name}': {exc}", file=sys.stderr)
        return 2

    print(f"Created index '{index_name}' using mapping '{args.mapping}'.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main(sys.argv[1:]))
