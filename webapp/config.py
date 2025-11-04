"""Configuration objects for the recipe web application."""
from __future__ import annotations

import os
from dataclasses import dataclass


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
class StripeConfig:
    """Configuration for Stripe integration."""

    secret_key: str = ""
    webhook_secret: str = ""
    product_name: str = "findmyflavour Premium"
    product_description: str = "Unlock unlimited recipe discovery and features"
    currency: str = "gbp"
    unit_amount: int = 300
    interval: str = "month"
    interval_count: int = 1

    @classmethod
    def from_env(cls, prefix: str = "STRIPE_") -> "StripeConfig":
        return cls(
            secret_key=os.getenv(f"{prefix}SECRET_KEY", cls.secret_key),
            webhook_secret=os.getenv(f"{prefix}WEBHOOK_SECRET", cls.webhook_secret),
            product_name=os.getenv(f"{prefix}PRODUCT_NAME", cls.product_name),
            product_description=os.getenv(
                f"{prefix}PRODUCT_DESCRIPTION", cls.product_description
            ),
            currency=os.getenv(f"{prefix}CURRENCY", cls.currency),
            unit_amount=int(os.getenv(f"{prefix}UNIT_AMOUNT", cls.unit_amount)),
            interval=os.getenv(f"{prefix}INTERVAL", cls.interval),
            interval_count=int(
                os.getenv(f"{prefix}INTERVAL_COUNT", cls.interval_count)
            ),
        )


@dataclass(frozen=True)
class AppConfig:
    """Top level application configuration."""

    database: DatabaseConfig = DatabaseConfig()
    page_size: int = 20
    stripe: StripeConfig = StripeConfig()

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create the configuration from environment variables."""

        database = DatabaseConfig.from_env()
        page_size = int(os.getenv("PAGE_SIZE", cls.page_size))
        stripe = StripeConfig.from_env()
        return cls(database=database, page_size=page_size, stripe=stripe)
