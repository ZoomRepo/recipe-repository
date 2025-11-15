"""Command line utility that verifies Elasticsearch connectivity."""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

from webapp.config import AppConfig
from webapp.scripts.es_utils import ES_EXCEPTIONS, build_client, index_exists


DEFAULT_EXPECTED_STATUS = "yellow"


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check connectivity to the configured Elasticsearch cluster.",
    )
    parser.add_argument(
        "--expected-status",
        default=DEFAULT_EXPECTED_STATUS,
        help=(
            "Cluster status that should be considered healthy. "
            "Defaults to '%(default)s'."
        ),
    )
    parser.add_argument(
        "--check-indices",
        action="store_true",
        help="Also verify that the configured indices exist.",
    )
    parser.add_argument(
        "--username",
        help="Override the Elasticsearch username from the environment.",
    )
    parser.add_argument(
        "--password",
        help=(
            "Override the Elasticsearch password from the environment. "
            "Use with --username."
        ),
    )
    parser.add_argument(
        "--api-key",
        help=(
            "Provide a base64 encoded Elasticsearch API key. "
            "Takes precedence over --username/--password."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv or [])
    config = AppConfig.from_env()
    es_config = config.elasticsearch

    try:
        client = build_client(
            config,
            username=args.username,
            password=args.password,
            api_key=args.api_key,
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to create Elasticsearch client: {exc}", file=sys.stderr)
        return 2

    try:
        if not client.ping():
            print("Elasticsearch ping failed", file=sys.stderr)
            return 2
        health = client.cluster.health(
            wait_for_status=args.expected_status,
            request_timeout=es_config.timeout,
        )
    except ES_EXCEPTIONS as exc:
        print(f"Cluster health check failed: {exc}", file=sys.stderr)
        return 2

    status = health.get("status", "unknown")
    print(f"Cluster status: {status}")

    if args.check_indices:
        missing: list[str] = []
        for name in {es_config.recipe_index, es_config.scraper_index}:
            try:
                if not index_exists(client, name):
                    missing.append(name)
            except ES_EXCEPTIONS as exc:
                print(f"Failed to inspect index '{name}': {exc}", file=sys.stderr)
                return 2
        if missing:
            print(
                "Missing expected indices: " + ", ".join(sorted(missing)),
                file=sys.stderr,
            )
            return 1

    if status not in {args.expected_status, "green"}:
        print(
            f"Cluster reported status '{status}', expected at least "
            f"'{args.expected_status}'",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main(sys.argv[1:]))
