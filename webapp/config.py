"""Configuration objects for the recipe web application."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _strtobool(value: str) -> bool:
    """Return ``True`` when *value* represents a truthy string."""

    return value.lower() in {"1", "true", "t", "yes", "y", "on"}


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
class MailConfig:
    """Outgoing mail settings for sending authentication codes."""

    enabled: bool = False
    host: str = "localhost"
    port: int = 587
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    sender: str = "no-reply@reciperepository.local"

    @classmethod
    def from_env(cls, prefix: str = "MAIL_") -> "MailConfig":
        """Create a configuration from environment variables."""

        enabled = _strtobool(os.getenv(f"{prefix}ENABLED", "false"))
        host = os.getenv(f"{prefix}HOST", cls.host)
        port = int(os.getenv(f"{prefix}PORT", cls.port))
        username = os.getenv(f"{prefix}USERNAME")
        password = os.getenv(f"{prefix}PASSWORD")
        use_tls = _strtobool(os.getenv(f"{prefix}USE_TLS", "true"))
        sender = os.getenv(f"{prefix}SENDER", cls.sender)
        return cls(
            enabled=enabled,
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            sender=sender,
        )


@dataclass(frozen=True)
class ElasticsearchConfig:
    """Connection information for the Elasticsearch cluster."""

    url: str = "http://localhost:9200"
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    recipe_index: str = "recipes"
    scraper_index: str = "scraper-events"
    timeout: int = 10

    @classmethod
    def from_env(cls, prefix: str = "ELASTICSEARCH_") -> "ElasticsearchConfig":
        """Create the configuration from environment variables."""

        url = os.getenv(f"{prefix}URL", cls.url)
        username = os.getenv(f"{prefix}USERNAME")
        password = os.getenv(f"{prefix}PASSWORD")
        api_key = os.getenv(f"{prefix}API_KEY")
        recipe_index = os.getenv(f"{prefix}RECIPE_INDEX", cls.recipe_index)
        scraper_index = os.getenv(f"{prefix}SCRAPER_INDEX", cls.scraper_index)
        timeout = int(os.getenv(f"{prefix}TIMEOUT", cls.timeout))
        return cls(
            url=url,
            username=username,
            password=password,
            api_key=api_key,
            recipe_index=recipe_index,
            scraper_index=scraper_index,
            timeout=timeout,
        )


@dataclass(frozen=True)
class LoginGateConfig:
    """Configuration for the temporary email login gate."""

    enabled: bool = False
    code_ttl_minutes: int = 10
    session_lifetime_minutes: int = 720

    @classmethod
    def from_env(cls, prefix: str = "LOGIN_GATE_") -> "LoginGateConfig":
        """Create the configuration from environment variables."""

        enabled = _strtobool(os.getenv(f"{prefix}ENABLED", "false"))
        code_ttl_minutes = int(
            os.getenv(f"{prefix}CODE_TTL_MINUTES", cls.code_ttl_minutes)
        )
        session_lifetime_minutes = int(
            os.getenv(
                f"{prefix}SESSION_LIFETIME_MINUTES", cls.session_lifetime_minutes
            )
        )
        return cls(
            enabled=enabled,
            code_ttl_minutes=code_ttl_minutes,
            session_lifetime_minutes=session_lifetime_minutes,
        )


@dataclass(frozen=True)
class AppConfig:
    """Top level application configuration."""

    database: DatabaseConfig = DatabaseConfig()
    page_size: int = 20
    secret_key: str = "dev-secret-key"
    login_gate: LoginGateConfig = LoginGateConfig()
    mail: MailConfig = MailConfig()
    elasticsearch: ElasticsearchConfig = ElasticsearchConfig()

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create the configuration from environment variables."""

        database = DatabaseConfig.from_env()
        page_size = int(os.getenv("PAGE_SIZE", cls.page_size))
        secret_key = os.getenv("SECRET_KEY", cls.secret_key)
        login_gate = LoginGateConfig.from_env()
        mail = MailConfig.from_env()
        elasticsearch = ElasticsearchConfig.from_env()
        return cls(
            database=database,
            page_size=page_size,
            secret_key=secret_key,
            login_gate=login_gate,
            mail=mail,
            elasticsearch=elasticsearch,
        )
