"""Command line utility that verifies Elasticsearch connectivity."""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError

from webapp.config import AppConfig


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
    return parser.parse_args(list(argv))


def _build_client(config: AppConfig) -> Elasticsearch:
    es_config = config.elasticsearch
    kwargs = {"request_timeout": es_config.timeout}
    if es_config.username or es_config.password:
        kwargs["basic_auth"] = (es_config.username or "elastic", es_config.password or "")
    if es_config.compatibility_version:
        version = es_config.compatibility_version
        compat_header = (
            "application/vnd.elasticsearch+json; compatible-with=%s" % version
        )
        kwargs["headers"] = {
            "Accept": compat_header,
            "Content-Type": compat_header,
        }
    return Elasticsearch(es_config.url, **kwargs)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv or [])
    config = AppConfig.from_env()
    es_config = config.elasticsearch

    try:
        client = _build_client(config)
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Failed to create Elasticsearch client: {exc}", file=sys.stderr)
        return 2

    try:
        if not client.ping():
            username = es_config.username or ("elastic" if es_config.password else None)
            auth_description = username if username else "none"
            print(
                "Elasticsearch ping failed for "
                f"url='{es_config.url}' auth='{auth_description}'",
                file=sys.stderr,
            )
            return 2
        health = client.cluster.health(
            wait_for_status=args.expected_status,
            request_timeout=es_config.timeout,
        )
    except TransportError as exc:
        print(f"Cluster health check failed: {exc}", file=sys.stderr)
        return 2

    status = health.get("status", "unknown")
    print(f"Cluster status: {status}")

    if args.check_indices:
        missing: list[str] = []
        for name in {es_config.recipe_index, es_config.scraper_index}:
            try:
                if not client.indices.exists(index=name):
                    missing.append(name)
            except TransportError as exc:
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
