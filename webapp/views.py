"""Flask views for browsing recipes."""
from __future__ import annotations

from typing import Any, List, Optional

from flask import Blueprint, abort, jsonify, render_template, request
from werkzeug.datastructures import MultiDict

from .service import RecipeService


def register_routes(app: Any, service: RecipeService) -> None:
    """Register the HTTP routes on *app* using the provided service."""

    blueprint = Blueprint("recipes", __name__)

    @blueprint.route("/")
    def index() -> str:
        raw_query = request.args.get("q", "")
        normalized_query = _normalize_query(raw_query)
        page = _parse_page(request.args.get("page", "1"))
        ingredients = _parse_ingredients(request.args)
        results = service.search(raw_query, page, ingredients)
        filters = {"query": normalized_query, "ingredients": ingredients}
        return render_template(
            "recipes/index.html",
            results=results,
            filters=filters,
        )

    @blueprint.route("/api/recipes")
    def api_recipes() -> Any:
        raw_query = request.args.get("q", "")
        normalized_query = _normalize_query(raw_query)
        page = _parse_page(request.args.get("page", "1"))
        ingredients = _parse_ingredients(request.args)
        results = service.search(raw_query, page, ingredients)
        filters = {"query": normalized_query, "ingredients": ingredients}
        return jsonify(
            {
                "html": render_template(
                    "recipes/_results.html",
                    results=results,
                    filters=filters,
                ),
                "meta": {
                    "heading": _format_heading(normalized_query, ingredients),
                    "subtitle": _format_subtitle(results.total),
                    "total": results.total,
                    "page": results.page,
                    "total_pages": results.total_pages,
                },
                "filters": {
                    "query": normalized_query or "",
                    "ingredients": ingredients,
                },
            }
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


def _normalize_query(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip()
    return normalized or None


def _parse_ingredients(args: MultiDict[str, str]) -> List[str]:
    values: List[str] = []
    values.extend(args.getlist("ingredient"))
    csv_values = args.get("ingredients")
    if csv_values:
        values.extend(part.strip() for part in csv_values.split(","))

    normalized: List[str] = []
    seen = set()
    for value in values:
        if not value:
            continue
        cleaned = value.strip().lower()
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return normalized


def _format_heading(query: Optional[str], ingredients: List[str]) -> str:
    if query and ingredients:
        plural = "s" if len(ingredients) != 1 else ""
        return f'Recipes matching "{query}" with {len(ingredients)} ingredient{plural}'
    if query:
        return f'Recipes matching "{query}"'
    if ingredients:
        return "Recipes containing " + ", ".join(ingredients)
    return "Latest recipes"


def _format_subtitle(total: int) -> str:
    suffix = "" if total == 1 else "s"
    return f"{total} recipe{suffix} found"
