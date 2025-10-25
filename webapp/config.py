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
class SmsConfig:
    """Configuration for sending SMS notifications."""

    account_sid: Optional[str] = None
    auth_token: Optional[str] = None
    from_number: Optional[str] = None

    @classmethod
    def from_env(cls, prefix: str = "SMS_") -> "SmsConfig":
        return cls(
            account_sid=os.getenv(f"{prefix}ACCOUNT_SID"),
            auth_token=os.getenv(f"{prefix}AUTH_TOKEN"),
            from_number=os.getenv(f"{prefix}FROM_NUMBER"),
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
    sms: SmsConfig = SmsConfig()
    access: AccessConfig = AccessConfig()

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create the configuration from environment variables."""

        database = DatabaseConfig.from_env()
        page_size = int(os.getenv("PAGE_SIZE", cls.page_size))
        secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
        sms = SmsConfig.from_env()
        access = AccessConfig.from_env()
        return cls(
            database=database,
            page_size=page_size,
            secret_key=secret_key,
            sms=sms,
            access=access,
        )
