"""Flask application factory for browsing scraped recipes."""
from __future__ import annotations

from datetime import timedelta

from flask import Flask

from .auth import register_login_routes
from .config import AppConfig
from .repository import RecipeQueryRepository
from .service import RecipeService
from .services import EmailService, NutritionService
from .whitelist import LoginWhitelistRepository, register_whitelist_routes
from .views import register_routes


def create_app(config: AppConfig | None = None) -> Flask:
    """Create and configure the Flask application."""

    resolved_config = config or AppConfig.from_env()
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    repository = RecipeQueryRepository.from_config(resolved_config.database)
    nutrition_service = NutritionService()
    service = RecipeService(
        repository,
        resolved_config.page_size,
        nutrition_service=nutrition_service,
    )
    register_routes(app, service)
    app.secret_key = resolved_config.secret_key
    app.config["SECRET_KEY"] = resolved_config.secret_key
    app.permanent_session_lifetime = timedelta(
        minutes=resolved_config.login_gate.session_lifetime_minutes
    )
    email_service = EmailService(resolved_config.mail)
    whitelist_repository = LoginWhitelistRepository.from_config(
        resolved_config.database
    )
    register_login_routes(
        app,
        resolved_config.login_gate,
        email_service,
        whitelist_repository,
    )
    register_whitelist_routes(app, whitelist_repository)
    app.config["APP_CONFIG"] = resolved_config
    app.config["ELASTICSEARCH_CONFIG"] = resolved_config.elasticsearch
    app.config["RECIPE_SERVICE"] = service
    return app
