"""Utilities for indexing recipes into Elasticsearch."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable, Mapping, MutableMapping, Sequence

from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import NotFoundError

from webapp.config import AppConfig

logger = logging.getLogger(__name__)


class RecipeDocumentBuilder:
    """Build Elasticsearch recipe documents from database rows."""

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> dict:
        raw_data = cls._parse_json_object(row.get("raw"))
        ingredients = cls._parse_json_list(row.get("ingredients"))
        ingredient_entries = [cls._build_ingredient(item) for item in ingredients if item]
        instructions = cls._join_text(cls._parse_json_list(row.get("instructions")))

        categories = cls._parse_json_list(row.get("categories"))
        tags = cls._parse_json_list(row.get("tags"))

        title = cls._string_or_none(row.get("title"))
        document: MutableMapping[str, object] = {
            "id": row.get("id"),
            "source_name": row.get("source_name"),
            "source_url": row.get("source_url"),
            "title": title,
            "description": cls._string_or_none(row.get("description")),
            "ingredients": ingredient_entries,
            "instructions": instructions,
            "prep_time": cls._string_or_none(row.get("prep_time")),
            "cook_time": cls._string_or_none(row.get("cook_time")),
            "total_time": cls._string_or_none(row.get("total_time")),
            "servings": cls._string_or_none(row.get("servings")),
            "image": cls._string_or_none(row.get("image")),
            "author": cls._string_or_none(row.get("author")),
            "categories": categories,
            "tags": tags,
            "raw": raw_data,
            "nutrients": cls._extract_nutrients(raw_data),
            "created_at": cls._isoformat(row.get("created_at")),
            "updated_at": cls._isoformat(row.get("updated_at")),
        }

        suggest_inputs = cls._build_suggest_inputs(title, ingredient_entries, categories, tags)
        if suggest_inputs:
            document["suggest"] = {"input": suggest_inputs}

        return document

    @staticmethod
    def _string_or_none(value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _parse_json_list(value: object | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item is not None]
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return [value]
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item is not None]
            if isinstance(parsed, str):
                return [parsed]
        return []

    @staticmethod
    def _parse_json_object(value: object | None) -> dict | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return parsed
        return None

    @staticmethod
    def _build_ingredient(raw_text: str) -> dict:
        cleaned = raw_text.strip()
        return {
            "raw": cleaned,
            "name": cleaned,
        }

    @staticmethod
    def _join_text(values: Sequence[str]) -> str | None:
        normalized = [value.strip() for value in values if value and value.strip()]
        if not normalized:
            return None
        return "\n\n".join(normalized)

    @staticmethod
    def _extract_nutrients(raw: Mapping[str, object] | None) -> Mapping[str, object] | None:
        if not raw or not isinstance(raw, Mapping):
            return None
        nutrients = raw.get("nutrition")
        return nutrients if isinstance(nutrients, Mapping) else None

    @staticmethod
    def _isoformat(value: object | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return None

    @classmethod
    def _build_suggest_inputs(
        cls,
        title: str | None,
        ingredients: Sequence[Mapping[str, str]],
        categories: Sequence[str],
        tags: Sequence[str],
    ) -> list[str]:
        inputs: list[str] = []
        for candidate in [title, *categories, *tags]:
            if candidate:
                inputs.append(str(candidate))
        inputs.extend(entry.get("name") for entry in ingredients if entry.get("name"))
        return [item for item in inputs if item]


class RecipeSearchIndexer:
    """Encapsulates common Elasticsearch indexing operations."""

    def __init__(self, client: Elasticsearch, index: str) -> None:
        self._client = client
        self._index = index

    @classmethod
    def from_config(cls, config: AppConfig) -> "RecipeSearchIndexer":
        es_config = config.elasticsearch
        kwargs: dict[str, object] = {"request_timeout": es_config.timeout}
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
            kwargs["headers"] = {
                "Accept": compat_header,
                "Content-Type": compat_header,
            }
        client = Elasticsearch(es_config.url, **kwargs)
        return cls(client, es_config.recipe_index)

    def bulk_index(self, documents: Iterable[Mapping[str, object]]) -> None:
        actions = (
            {
                "_op_type": "index",
                "_index": self._index,
                "_id": document.get("id"),
                "_source": document,
            }
            for document in documents
        )
        helpers.bulk(self._client, actions)

    def bulk_index_rows(self, rows: Iterable[Mapping[str, object]]) -> None:
        self.bulk_index(RecipeDocumentBuilder.from_row(row) for row in rows)

    def upsert_recipe(self, document: Mapping[str, object]) -> None:
        self._client.index(index=self._index, id=document.get("id"), document=document)

    def upsert_row(self, row: Mapping[str, object]) -> None:
        document = RecipeDocumentBuilder.from_row(row)
        self.upsert_recipe(document)

    def delete_recipe(self, recipe_id: int) -> None:
        try:
            self._client.delete(index=self._index, id=recipe_id)
        except NotFoundError:
            logger.debug("Recipe %s already absent from index", recipe_id)
