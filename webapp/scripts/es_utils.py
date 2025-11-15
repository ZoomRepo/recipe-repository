"""Shared helpers for Elasticsearch admin scripts."""
from __future__ import annotations

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import BadRequestError, NotFoundError, TransportError

try:  # pragma: no cover - elasticsearch<8 compatibility
    from elasticsearch import ApiError
except ImportError:  # pragma: no cover
    ApiError = TransportError  # type: ignore[assignment]

from webapp.config import AppConfig

# In elasticsearch-py 7.x ``BadRequestError`` inherits from ``TransportError``
# while 8.x+ promotes it to ``ApiError``. Expose a single tuple that callers
# can use when catching transport-level failures so we remain compatible across
# versions without littering the scripts with conditional imports.
ES_EXCEPTIONS: tuple[type[Exception], ...] = (TransportError, ApiError)


def build_client(
    config: AppConfig,
    *,
    username: str | None = None,
    password: str | None = None,
    api_key: str | None = None,
) -> Elasticsearch:
    """Create an Elasticsearch client using the provided app configuration."""

    es_config = config.elasticsearch
    kwargs = {"request_timeout": es_config.timeout}

    resolved_api_key = api_key or es_config.api_key
    resolved_username = username if username is not None else es_config.username
    resolved_password = password if password is not None else es_config.password

    if resolved_api_key:
        kwargs["api_key"] = resolved_api_key
    elif resolved_username:
        kwargs["basic_auth"] = (resolved_username, resolved_password or "")

    return Elasticsearch(es_config.url, **kwargs)


def index_exists(client: Elasticsearch, index_name: str) -> bool:
    """Return ``True`` when *index_name* exists, falling back when needed."""

    try:
        return bool(client.indices.exists(index=index_name))
    except BadRequestError as exc:
        status = getattr(getattr(exc, "meta", None), "status", None)
        if status not in {None, 400, 405}:
            raise

        try:
            client.indices.get(index=index_name)
        except NotFoundError:
            return False
        except BadRequestError:
            raise
        return True
