"""Configuration objects for the recipe web application."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatabaseConfig:
    """Connection details for the recipe database."""

    host: str = "192.168.1.99"
    port: int = 3306
    user: str = "reciperepository"
    password: str = "Xenomorph123!"
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
class EmailConfig:
    """Configuration for sending invite verification emails."""

    host: Optional[str] = None
    port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True
    from_address: Optional[str] = None

    @classmethod
    def from_env(cls, prefix: str = "EMAIL_") -> "EmailConfig":
        host = os.getenv(f"{prefix}HOST")
        port = int(os.getenv(f"{prefix}PORT", cls.port))
        username = os.getenv(f"{prefix}USERNAME")
        password = os.getenv(f"{prefix}PASSWORD")
        use_tls_raw = os.getenv(f"{prefix}USE_TLS")
        use_tls = cls.use_tls
        if use_tls_raw is not None:
            use_tls = use_tls_raw.lower() in {"1", "true", "yes", "on"}
        from_address = os.getenv(f"{prefix}FROM_ADDRESS")
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            from_address=from_address,
        )


@dataclass(frozen=True)
class AccessConfig:
    """Configuration options for the invite-only flow."""

    cookie_name: str = "recipe_device_id"
    code_ttl_minutes: int = 15

    @classmethod
    def from_env(cls, prefix: str = "ACCESS_") -> "AccessConfig":
        cookie_name = os.getenv(f"{prefix}COOKIE_NAME", cls.cookie_name)
        code_ttl = int(os.getenv(f"{prefix}CODE_TTL_MINUTES", cls.code_ttl_minutes))
        return cls(cookie_name=cookie_name, code_ttl_minutes=code_ttl)


@dataclass(frozen=True)
class AppConfig:
    """Top level application configuration."""

    database: DatabaseConfig = DatabaseConfig()
    page_size: int = 20
    secret_key: str = "change-me"
    email: EmailConfig = EmailConfig()
    access: AccessConfig = AccessConfig()

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create the configuration from environment variables."""

        database = DatabaseConfig.from_env()
        page_size = int(os.getenv("PAGE_SIZE", cls.page_size))
        secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
        email = EmailConfig.from_env()
        access = AccessConfig.from_env()
        return cls(
            database=database,
            page_size=page_size,
            secret_key=secret_key,
            email=email,
            access=access,
        )
