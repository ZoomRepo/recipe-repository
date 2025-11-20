"""Search repositories backed by Elasticsearch."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping, Protocol, Sequence

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import TransportError

from webapp.config import AppConfig
from webapp.filter_options import CUISINE_LOOKUP, DIET_LOOKUP, MEAL_LOOKUP, FilterOption
from webapp.models import PaginatedResult, RecipeSummary

logger = logging.getLogger(__name__)


class SearchRepository(Protocol):
    """Protocol describing search capabilities."""

    def search(
        self,
        query: str | None,
        ingredients: Iterable[str] | None,
        page: int,
        page_size: int,
        cuisines: Sequence[str] | None = None,
        meals: Sequence[str] | None = None,
        diets: Sequence[str] | None = None,
    ) -> PaginatedResult:
        ...


class ElasticsearchSearchRepository(SearchRepository):
    """Elasticsearch-backed implementation of the search repository."""

    def __init__(self, client: Elasticsearch, index: str) -> None:
        self._client = client
        self._index = index

    @classmethod
    def from_config(cls, config: AppConfig) -> "ElasticsearchSearchRepository":
        es_config = config.elasticsearch
        kwargs: MutableMapping[str, object] = {"request_timeout": es_config.timeout}
        if es_config.username or es_config.password:
            username = es_config.username or "elastic"
            kwargs["basic_auth"] = (username, es_config.password or "")
        if es_config.compatibility_version:
            version = es_config.compatibility_version
            if version not in (7, 8):
                logger.warning(
                    "Invalid Elasticsearch compatibility version '%s'; defaulting to 8",
                    version,
                )
                version = 8
            compat_header = (
                "application/vnd.elasticsearch+json; compatible-with=%s" % version
            )
            headers: MutableMapping[str, str] = kwargs.setdefault("headers", {})
            headers.update({"Accept": compat_header, "Content-Type": compat_header})
        client = Elasticsearch(es_config.url, **kwargs)
        return cls(client, es_config.recipe_index)

    def search(
        self,
        query: str | None,
        ingredients: Iterable[str] | None,
        page: int,
        page_size: int,
        cuisines: Sequence[str] | None = None,
        meals: Sequence[str] | None = None,
        diets: Sequence[str] | None = None,
    ) -> PaginatedResult:
        normalized_page = max(page, 1)
        offset = (normalized_page - 1) * page_size
        payload = self._build_search_body(query, ingredients, cuisines, meals, diets)

        try:
            response = self._client.search(
                index=self._index,
                query=payload["query"],
                from_=offset,
                size=page_size,
                highlight=payload["highlight"],
                _source=self._source_fields(),
                sort=["_score:desc", {"updated_at": "desc"}, {"id": "desc"}],
            )
        except TransportError:
            logger.exception("Elasticsearch search failed; returning empty result set")
            return PaginatedResult(
                items=[],
                total=0,
                page=normalized_page,
                page_size=page_size,
                query=query or None,
            )

        hits = response.get("hits", {})
        total_obj = hits.get("total", {})
        total = total_obj.get("value") if isinstance(total_obj, Mapping) else 0
        items = [self._map_hit_to_summary(hit) for hit in hits.get("hits", [])]

        return PaginatedResult(
            items=items,
            total=int(total or 0),
            page=normalized_page,
            page_size=page_size,
            query=query or None,
        )

    def _build_search_body(
        self,
        query: str | None,
        ingredients: Iterable[str] | None,
        cuisines: Sequence[str] | None,
        meals: Sequence[str] | None,
        diets: Sequence[str] | None,
    ) -> Mapping[str, object]:
        must_clauses: list[Mapping[str, object]] = []
        filter_clauses: list[Mapping[str, object]] = []

        if query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^4",
                            "title.shingles^2",
                            "description^2",
                            "description.shingles",
                            "instructions",
                            "ingredients.raw^2",
                            "ingredients.name^3",
                            "categories^2",
                            "tags^2",
                        ],
                        "type": "most_fields",
                        "operator": "and",
                    }
                }
            )
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^5",
                            "description^3",
                            "instructions^2",
                            "ingredients.name^3",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )

        if ingredients:
            for ingredient in ingredients:
                filter_clauses.append(
                    {
                        "nested": {
                            "path": "ingredients",
                            "query": {
                                "match": {
                                    "ingredients.name": {
                                        "query": ingredient,
                                        "operator": "and",
                                    }
                                }
                            },
                        }
                    }
                )

        cuisine_filters = self._build_option_filter_group(cuisines or [], CUISINE_LOOKUP)
        if cuisine_filters:
            filter_clauses.append(cuisine_filters)

        meal_filters = self._build_option_filter_group(meals or [], MEAL_LOOKUP)
        if meal_filters:
            filter_clauses.append(meal_filters)

        diet_filters = self._build_option_filter_group(diets or [], DIET_LOOKUP)
        if diet_filters:
            filter_clauses.append(diet_filters)

        query_body: Mapping[str, object] = {
            "query": {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}],
                    "filter": filter_clauses,
                }
            },
            "highlight": {
                "pre_tags": ["<mark>"],
                "post_tags": ["</mark>"],
                "fields": {
                    "title": {},
                    "description": {},
                    "instructions": {},
                    "ingredients.raw": {},
                },
            },
        }
        return query_body

    def _build_option_filter_group(
        self, values: Sequence[str], lookup: Mapping[str, FilterOption]
    ) -> Mapping[str, object] | None:
        option_filters: list[Mapping[str, object]] = []
        for value in values:
            option = lookup.get(value)
            if not option:
                continue
            keyword_filters: list[Mapping[str, object]] = []
            for keyword in option.normalized_keywords():
                keyword_filters.append(self._keyword_query(keyword))
            if keyword_filters:
                option_filters.append(
                    {"bool": {"should": keyword_filters, "minimum_should_match": 1}}
                )

        if not option_filters:
            return None

        return {"bool": {"should": option_filters, "minimum_should_match": 1}}

    def _keyword_query(self, keyword: str) -> Mapping[str, object]:
        return {
            "multi_match": {
                "query": keyword,
                "fields": [
                    "categories^3",
                    "tags^3",
                    "title^2",
                    "description",
                    "ingredients.raw",
                ],
                "type": "best_fields",
            }
        }

    def _source_fields(self) -> list[str]:
        return [
            "id",
            "title",
            "description",
            "source_name",
            "source_url",
            "image",
            "ingredients",
            "updated_at",
            "raw",
            "nutrients",
            "categories",
            "tags",
        ]

    def _map_hit_to_summary(self, hit: Mapping[str, object]) -> RecipeSummary:
        source = hit.get("_source", {}) if isinstance(hit, Mapping) else {}
        score = hit.get("_score") if isinstance(hit, Mapping) else None
        highlights = self._normalize_highlights(hit.get("highlight"))
        ingredients = self._extract_ingredients(source)
        return RecipeSummary(
            id=self._safe_int(source.get("id")),
            title=self._safe_str(source.get("title")),
            source_name=self._safe_str(source.get("source_name")) or "",
            source_url=self._safe_str(source.get("source_url")) or "",
            description=self._safe_str(source.get("description")),
            image=self._safe_str(source.get("image")),
            updated_at=self._parse_datetime(source.get("updated_at")),
            ingredients=ingredients,
            raw=source.get("raw") if isinstance(source, Mapping) else None,
            nutrients=self._extract_nutrients(source),
            score=score if isinstance(score, (int, float)) else None,
            highlights=highlights,
        )

    def _extract_ingredients(self, source: Mapping[str, object] | None) -> list[str]:
        if not source or not isinstance(source, Mapping):
            return []
        ingredients = source.get("ingredients")
        if not isinstance(ingredients, list):
            return []

        extracted: list[str] = []
        for entry in ingredients:
            if not isinstance(entry, Mapping):
                continue
            name = self._safe_str(entry.get("name"))
            raw = self._safe_str(entry.get("raw"))
            if raw:
                extracted.append(raw)
            elif name:
                extracted.append(name)
        return extracted

    def _normalize_highlights(
        self, highlights: Mapping[str, object] | None
    ) -> dict[str, list[str]] | None:
        if not highlights or not isinstance(highlights, Mapping):
            return None
        normalized: dict[str, list[str]] = {}
        for key, value in highlights.items():
            if isinstance(value, list):
                normalized[key] = [str(item) for item in value if item is not None]
        return normalized or None

    @staticmethod
    def _safe_str(value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _safe_int(value: object) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                normalized = value.replace("Z", "+00:00")
                return datetime.fromisoformat(normalized)
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_nutrients(source: Mapping[str, object] | None) -> Mapping[str, object] | None:
        if not source or not isinstance(source, Mapping):
            return None
        nutrients = source.get("nutrients")
        return nutrients if isinstance(nutrients, Mapping) else None

