"""Flask views for browsing recipes."""
from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, render_template, request

from .service import RecipeService


def register_routes(app: Any, service: RecipeService) -> None:
    """Register the HTTP routes on *app* using the provided service."""

    blueprint = Blueprint("recipes", __name__)

    @blueprint.route("/")
    def index() -> str:
        query = request.args.get("q", "")
        page = _parse_page(request.args.get("page", "1"))
        results = service.search(query, page)
        return render_template(
            "recipes/index.html",
            results=results,
            query=query,
        )

    @blueprint.route("/recipes/<int:recipe_id>")
    def detail(recipe_id: int) -> str:
        recipe = service.get(recipe_id)
        if recipe is None:
            abort(404)
        return render_template("recipes/detail.html", recipe=recipe)

    @blueprint.app_errorhandler(404)
    def not_found(_: Exception) -> tuple[str, int]:
        return render_template("errors/404.html"), 404

    app.register_blueprint(blueprint)


def _parse_page(raw_page: str) -> int:
    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        return 1
    return page if page > 0 else 1
