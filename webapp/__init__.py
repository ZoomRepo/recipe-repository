"""Flask application factory for browsing scraped recipes."""
from __future__ import annotations

from flask import Flask, redirect, request, url_for

from .access_repository import AccessRepository
from .access_service import AccessService
from .access_views import register_access_routes
from .config import AppConfig
from .db import create_connection_pool
from .email import SmtpSettings, create_email_sender
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
    app.secret_key = resolved_config.secret_key

    pool = create_connection_pool(resolved_config.database)
    recipe_repository = RecipeQueryRepository.from_pool(pool)
    service = RecipeService(recipe_repository, resolved_config.page_size)

    access_repository = AccessRepository.from_pool(pool)
    email_settings = None
    if resolved_config.email.host and resolved_config.email.from_address:
        email_settings = SmtpSettings(
            host=resolved_config.email.host,
            port=resolved_config.email.port,
            username=resolved_config.email.username,
            password=resolved_config.email.password,
            use_tls=resolved_config.email.use_tls,
            from_address=resolved_config.email.from_address,
        )
    email_sender = create_email_sender(email_settings)
    access_service = AccessService(access_repository, email_sender, resolved_config.access)

    register_access_routes(app, access_service)
    register_routes(app, service)

    @app.before_request
    def _require_invite() -> None:
        endpoint = request.endpoint or ""
        if not endpoint:
            return None
        if endpoint.startswith("access.") or endpoint == "static":
            return None
        device_id = request.cookies.get(access_service.cookie_name)
        if access_service.is_device_authorized(device_id):
            return None
        return redirect(url_for("access.welcome"))

    app.config["APP_CONFIG"] = resolved_config
    app.config["RECIPE_SERVICE"] = service
    app.config["ACCESS_SERVICE"] = access_service
    return app
