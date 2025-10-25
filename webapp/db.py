"""Database connection helpers for the web application."""
from __future__ import annotations

from mysql.connector import pooling

from .config import DatabaseConfig


def create_connection_pool(config: DatabaseConfig) -> pooling.MySQLConnectionPool:
    """Create a MySQL connection pool using *config*."""

    return pooling.MySQLConnectionPool(
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
