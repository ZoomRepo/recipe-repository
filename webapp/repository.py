"""Data access layer for the recipe web application."""
from __future__ import annotations

import json
from typing import List, Optional

from mysql.connector import pooling

from .config import DatabaseConfig
from .filter_options import (
    CUISINE_LOOKUP,
    DIET_LOOKUP,
    MEAL_LOOKUP,
    FilterOption,
)
from .models import PaginatedResult, RecipeDetail, RecipeSummary


class RecipeQueryRepository:
    """Provides read-only access to the recipe catalogue."""

    def __init__(self, pool: pooling.MySQLConnectionPool) -> None:
        self._pool = pool

    @classmethod
    def from_config(cls, config: DatabaseConfig) -> "RecipeQueryRepository":
        pool = pooling.MySQLConnectionPool(
            pool_name=config.pool_name,
            pool_size=config.pool_size,
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database,
            charset="utf8mb4",
            use_unicode=True,
        )
        return cls(pool)

    def search(
        self,
        query: Optional[str],
        ingredients: Optional[List[str]],
        page: int,
        page_size: int,
        cuisines: Optional[List[str]] = None,
        meals: Optional[List[str]] = None,
        diets: Optional[List[str]] = None,
    ) -> PaginatedResult:
        """Search recipes matching *query* and *ingredients* with pagination."""

        normalized_page = max(page, 1)
        offset = (normalized_page - 1) * page_size
        conditions: List[str] = []
        params: List[object] = []
        if query:
            lowered_query = query.lower()
            like = f"%{lowered_query}%"
            normalized_clause = (
                "("
                "LOWER(COALESCE(title, '')) LIKE %s OR "
                "LOWER(COALESCE(description, '')) LIKE %s OR "
                "LOWER(COALESCE(ingredients, '')) LIKE %s OR "
                "LOWER(COALESCE(instructions, '')) LIKE %s OR "
                "LOWER(COALESCE(categories, '')) LIKE %s OR "
                "LOWER(COALESCE(tags, '')) LIKE %s"
                ")"
            )
            query_clauses = [normalized_clause]
            params.extend([like] * 6)

            keywords = [part for part in lowered_query.split() if part]
            if len(keywords) > 1:
                keyword_clause = (
                    "(LOWER(COALESCE(title, '')) LIKE %s OR "
                    "LOWER(COALESCE(description, '')) LIKE %s)"
                )
                for keyword in keywords:
                    keyword_like = f"%{keyword}%"
                    query_clauses.append(keyword_clause)
                    params.extend([keyword_like, keyword_like])

            conditions.append(f"({' OR '.join(query_clauses)})")
        if ingredients:
            for ingredient in ingredients:
                normalized = ingredient.lower()
                like = f"%{normalized}%"
                conditions.append("LOWER(ingredients) LIKE %s")
                params.append(like)
        self._apply_option_filters(cuisines, CUISINE_LOOKUP, conditions, params)
        self._apply_option_filters(meals, MEAL_LOOKUP, conditions, params)
        self._apply_option_filters(diets, DIET_LOOKUP, conditions, params)
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        listing_sql = f"""
            SELECT
                id,
                title,
                source_name,
                source_url,
                description,
                image,
                updated_at
            FROM recipes
            {where_clause}
            ORDER BY updated_at DESC, id DESC
            LIMIT %s OFFSET %s
        """
        count_sql = f"SELECT COUNT(*) AS total FROM recipes {where_clause}"
        items = self._fetch_summaries(listing_sql, (*params, page_size, offset))
        total = self._fetch_total(count_sql, params)
        return PaginatedResult(
            items=items,
            total=total,
            page=normalized_page,
            page_size=page_size,
            query=query or None,
        )

    def get(self, recipe_id: int) -> Optional[RecipeDetail]:
        """Return a single recipe or ``None`` if it does not exist."""

        sql = """
            SELECT
                id,
                title,
                source_name,
                source_url,
                description,
                image,
                ingredients,
                instructions,
                prep_time,
                cook_time,
                total_time,
                servings,
                author,
                categories,
                tags,
                raw,
                updated_at
            FROM recipes
            WHERE id = %s
        """
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql, (recipe_id,))
                row = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        if not row:
            return None
        return RecipeDetail(
            id=row["id"],
            title=row.get("title"),
            source_name=row["source_name"],
            source_url=row["source_url"],
            description=row.get("description"),
            image=row.get("image"),
            updated_at=row.get("updated_at"),
            ingredients=self._parse_json_list(row.get("ingredients")),
            instructions=self._parse_json_list(row.get("instructions")),
            prep_time=row.get("prep_time"),
            cook_time=row.get("cook_time"),
            total_time=row.get("total_time"),
            servings=row.get("servings"),
            author=row.get("author"),
            categories=self._parse_json_list(row.get("categories")),
            tags=self._parse_json_list(row.get("tags")),
            raw=self._parse_json_object(row.get("raw")),
        )

    def _fetch_summaries(self, sql: str, params: tuple) -> List[RecipeSummary]:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            finally:
                cursor.close()
        finally:
            connection.close()
        return [
            RecipeSummary(
                id=row["id"],
                title=row.get("title"),
                source_name=row["source_name"],
                source_url=row["source_url"],
                description=row.get("description"),
                image=row.get("image"),
                updated_at=row.get("updated_at"),
            )
            for row in rows
        ]

    def _fetch_total(self, sql: str, params: List[object]) -> int:
        connection = self._pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute(sql, tuple(params))
                (total,) = cursor.fetchone()
            finally:
                cursor.close()
        finally:
            connection.close()
        return int(total)

    def _apply_option_filters(
        self,
        selected: Optional[List[str]],
        lookup: dict[str, FilterOption],
        conditions: List[str],
        params: List[object],
    ) -> None:
        if not selected:
            return

        option_clauses: List[str] = []
        for value in selected:
            option = lookup.get(value)
            if not option:
                continue
            clause = self._build_keywords_clause(option.normalized_keywords(), params)
            if clause:
                option_clauses.append(clause)
        if option_clauses:
            conditions.append(f"({' OR '.join(option_clauses)})")

    def _build_keywords_clause(
        self, keywords: tuple[str, ...], params: List[object]
    ) -> Optional[str]:
        if not keywords:
            return None

        column_template = (
            "LOWER(COALESCE(title, '')) LIKE %s OR "
            "LOWER(COALESCE(description, '')) LIKE %s OR "
            "LOWER(COALESCE(categories, '')) LIKE %s OR "
            "LOWER(COALESCE(tags, '')) LIKE %s OR "
            "LOWER(COALESCE(ingredients, '')) LIKE %s"
        )

        keyword_clauses: List[str] = []
        for keyword in keywords:
            like = f"%{keyword}%"
            keyword_clauses.append(f"({column_template})")
            params.extend([like] * 5)

        if not keyword_clauses:
            return None
        return f"({' OR '.join(keyword_clauses)})"

    @staticmethod
    def _parse_json_list(value: Optional[str]) -> List[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if item is not None]
        if isinstance(parsed, str):
            return [parsed]
        return []

    @staticmethod
    def _parse_json_object(value: Optional[str]) -> Optional[dict]:
        if not value:
            return None
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return None
        if isinstance(parsed, dict):
            return parsed
        return None
