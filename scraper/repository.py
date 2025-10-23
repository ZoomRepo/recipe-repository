"""Persistence layer for recipes."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Optional

import mysql.connector
from mysql.connector.connection import MySQLConnection

from .models import Recipe


class RecipeRepository(ABC):
    """Abstract repository responsible for persisting recipes."""

    @abstractmethod
    def ensure_schema(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def save(self, recipe: Recipe) -> None:
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
        """
        with self._connection() as connection:
            cursor = connection.cursor()
            cursor.execute(schema_sql)
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

    @staticmethod
    def _to_json_text(value: Optional[object]) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False)
