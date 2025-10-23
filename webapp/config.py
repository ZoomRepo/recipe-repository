"""Configuration objects for the recipe web application."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection details for the recipe database."""

    host: str = "217.43.43.202"
    port: int = 3306
    user: str = "reciperepository"
    password: str = "Xenomorph123"
    database: str = "reciperepository"
    pool_name: str = "recipe_web_pool"
    pool_size: int = 5

    @classmethod
    def from_env(cls, prefix: str = "DB_") -> "DatabaseConfig":
        """Create a configuration from environment variables."""

        return cls(
            host=os.getenv(f"{prefix}HOST", cls.host),
            port=int(os.getenv(f"{prefix}PORT", cls.port)),
            user=os.getenv(f"{prefix}USER", cls.user),
            password=os.getenv(f"{prefix}PASSWORD", cls.password),
            database=os.getenv(f"{prefix}NAME", cls.database),
            pool_name=os.getenv(f"{prefix}POOL_NAME", cls.pool_name),
            pool_size=int(os.getenv(f"{prefix}POOL_SIZE", cls.pool_size)),
        )


@dataclass(frozen=True)
class AppConfig:
    """Top level application configuration."""

    database: DatabaseConfig = DatabaseConfig()
    page_size: int = 20

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create the configuration from environment variables."""

        database = DatabaseConfig.from_env()
        page_size = int(os.getenv("PAGE_SIZE", cls.page_size))
        return cls(database=database, page_size=page_size)
