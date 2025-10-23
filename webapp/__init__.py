"""Flask application factory for browsing scraped recipes."""
from __future__ import annotations

from flask import Flask

from .config import AppConfig
from .repository import RecipeQueryRepository
from .service import RecipeService
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
    service = RecipeService(repository, resolved_config.page_size)
    register_routes(app, service)
    app.config["APP_CONFIG"] = resolved_config
    app.config["RECIPE_SERVICE"] = service
    return app
