"""Persistence layer for recipes."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Iterable, List, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from .models import PendingFailure, Recipe, ScrapeFailure


class RecipeRepository(ABC):
    """Abstract repository responsible for persisting recipes."""

    @abstractmethod
    def ensure_schema(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save(self, recipe: Recipe) -> None:
        raise NotImplementedError

    @abstractmethod
    def record_failure(self, failure: ScrapeFailure) -> None:
        raise NotImplementedError

    @abstractmethod
    def resolve_failure(
        self, template_name: str, stage: str, source_url: Optional[str]
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def iter_pending_failures(self) -> Iterable[PendingFailure]:
        raise NotImplementedError


class MySqlRecipeRepository(RecipeRepository):
    """MySQL backed implementation of :class:`RecipeRepository`."""

    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306,
        connect_timeout: int = 10,
    ) -> None:
        self._config = {
            "host": host,
            "user": user,
            "password": password,
            "database": database,
            "port": port,
            "connection_timeout": connect_timeout,
            "charset": "utf8mb4",
            "use_unicode": True,
        }

    @contextmanager
    def _connection(self) -> Generator[MySQLConnection, None, None]:
        connection = mysql.connector.connect(**self._config)
        try:
            yield connection
        finally:
            connection.close()

    def ensure_schema(self) -> None:
        schema_sql = """
        CREATE TABLE IF NOT EXISTS recipes (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            source_name VARCHAR(255) NOT NULL,
            source_url VARCHAR(2048) NOT NULL,
            title TEXT,
            description TEXT,
            ingredients LONGTEXT,
            instructions LONGTEXT,
            prep_time VARCHAR(255),
            cook_time VARCHAR(255),
            total_time VARCHAR(255),
            servings VARCHAR(255),
            image VARCHAR(1024),
            author VARCHAR(255),
            categories LONGTEXT,
            tags LONGTEXT,
            raw LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_source_url (source_url(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

        CREATE TABLE IF NOT EXISTS scrape_failures (
            id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            template_name VARCHAR(255) NOT NULL,
            stage VARCHAR(50) NOT NULL,
            source_url VARCHAR(2048) NOT NULL DEFAULT '',
            error_message TEXT,
            context LONGTEXT,
            attempt_count INT UNSIGNED NOT NULL DEFAULT 1,
            resolved TINYINT(1) NOT NULL DEFAULT 0,
            last_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP NULL DEFAULT NULL,
            UNIQUE KEY uniq_failure (template_name, stage, source_url(255))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self._connection() as connection:
            cursor = connection.cursor()
            for statement in filter(None, schema_sql.split(";")):
                if statement.strip():
                    cursor.execute(statement)
            connection.commit()

    def save(self, recipe: Recipe) -> None:
        payload = recipe.as_record()
        params = (
            payload["source_name"],
            payload["source_url"],
            payload.get("title"),
            payload.get("description"),
            self._to_json_text(payload.get("ingredients")),
            self._to_json_text(payload.get("instructions")),
            payload.get("prep_time"),
            payload.get("cook_time"),
            payload.get("total_time"),
            payload.get("servings"),
            payload.get("image"),
            payload.get("author"),
            self._to_json_text(payload.get("categories")),
            self._to_json_text(payload.get("tags")),
            self._to_json_text(payload.get("raw")),
        )
        sql = """
            INSERT INTO recipes (
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
                raw
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                description = VALUES(description),
                ingredients = VALUES(ingredients),
                instructions = VALUES(instructions),
                prep_time = VALUES(prep_time),
                cook_time = VALUES(cook_time),
                total_time = VALUES(total_time),
                servings = VALUES(servings),
                image = VALUES(image),
                author = VALUES(author),
                categories = VALUES(categories),
                tags = VALUES(tags),
                raw = VALUES(raw),
                updated_at = CURRENT_TIMESTAMP
        """
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()

    def record_failure(self, failure: ScrapeFailure) -> None:
        sql = """
            INSERT INTO scrape_failures (
                template_name,
                stage,
                source_url,
                error_message,
                context,
                attempt_count,
                resolved
            ) VALUES (%s, %s, %s, %s, %s, 1, 0)
            ON DUPLICATE KEY UPDATE
                error_message = VALUES(error_message),
                context = VALUES(context),
                attempt_count = scrape_failures.attempt_count + 1,
                resolved = 0,
                last_attempt_at = CURRENT_TIMESTAMP,
                resolved_at = NULL
        """
        params = (
            failure.template_name,
            failure.stage,
            failure.normalised_source_url(),
            failure.error_message,
            self._to_json_text(failure.context),
        )
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()

    def resolve_failure(
        self, template_name: str, stage: str, source_url: Optional[str]
    ) -> None:
        sql = """
            UPDATE scrape_failures
            SET resolved = 1,
                resolved_at = CURRENT_TIMESTAMP
            WHERE template_name = %s AND stage = %s AND source_url = %s
        """
        params = (template_name, stage, source_url or "")
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(sql, params)
            connection.commit()

    def iter_pending_failures(self) -> Iterable[PendingFailure]:
        sql = """
            SELECT id, template_name, stage, source_url, error_message, context, attempt_count
            FROM scrape_failures
            WHERE resolved = 0
            ORDER BY last_attempt_at ASC
        """
        with self._connection() as connection:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql)
            rows = cursor.fetchall()
        failures: List[PendingFailure] = []
        for row in rows:
            context = self._from_json_text(row.get("context"))
            failures.append(
                PendingFailure(
                    id=row["id"],
                    template_name=row["template_name"],
                    stage=row["stage"],
                    source_url=row.get("source_url") or None,
                    error_message=row.get("error_message") or "",
                    context=context or {},
                    attempt_count=row.get("attempt_count", 0) or 0,
                )
            )
        return failures

    @staticmethod
    def _to_json_text(value: Optional[object]) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _from_json_text(value: Optional[str]) -> Optional[dict]:
        if not value:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
