"""Flask views for browsing recipes."""
from __future__ import annotations

from typing import Any, List, Optional

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from werkzeug.datastructures import MultiDict

from .filter_options import (
    CUISINE_LOOKUP,
    CUISINE_OPTIONS,
    DIET_LOOKUP,
    DIET_OPTIONS,
    MEAL_LOOKUP,
    MEAL_OPTIONS,
    labels_for,
    normalize_selection,
)
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
        cuisines = normalize_selection(request.args.getlist("cuisine"), CUISINE_LOOKUP)
        meals = normalize_selection(request.args.getlist("meal"), MEAL_LOOKUP)
        diets = normalize_selection(request.args.getlist("diet"), DIET_LOOKUP)
        results = service.search(raw_query, page, ingredients, cuisines, meals, diets)
        heading_text = _format_heading(
            normalized_query, ingredients, cuisines, meals, diets
        )
        subtitle_text = _format_subtitle(results.total)
        filters = {
            "query": normalized_query,
            "ingredients": ingredients,
            "cuisines": cuisines,
            "meals": meals,
            "diets": diets,
        }
        return render_template(
            "recipes/index.html",
            results=results,
            filters=filters,
            heading=heading_text,
            subtitle=subtitle_text,
            cuisine_options=CUISINE_OPTIONS,
            meal_options=MEAL_OPTIONS,
            diet_options=DIET_OPTIONS,
        )

    @blueprint.route("/api/recipes")
    def api_recipes() -> Any:
        raw_query = request.args.get("q", "")
        normalized_query = _normalize_query(raw_query)
        page = _parse_page(request.args.get("page", "1"))
        ingredients = _parse_ingredients(request.args)
        cuisines = normalize_selection(request.args.getlist("cuisine"), CUISINE_LOOKUP)
        meals = normalize_selection(request.args.getlist("meal"), MEAL_LOOKUP)
        diets = normalize_selection(request.args.getlist("diet"), DIET_LOOKUP)
        results = service.search(raw_query, page, ingredients, cuisines, meals, diets)
        filters = {
            "query": normalized_query,
            "ingredients": ingredients,
            "cuisines": cuisines,
            "meals": meals,
            "diets": diets,
        }
        return jsonify(
            {
                "html": render_template(
                    "recipes/_results.html",
                    results=results,
                    filters=filters,
                ),
                "meta": {
                    "heading": _format_heading(
                        normalized_query, ingredients, cuisines, meals, diets
                    ),
                    "subtitle": _format_subtitle(results.total),
                    "total": results.total,
                    "page": results.page,
                    "total_pages": results.total_pages,
                },
                "filters": {
                    "query": normalized_query or "",
                    "ingredients": ingredients,
                    "cuisines": cuisines,
                    "meals": meals,
                    "diets": diets,
                },
            }
        )

    @blueprint.route("/recipes/<int:recipe_id>")
    def detail(recipe_id: int) -> str:
        recipe = service.get(recipe_id)
        if recipe is None:
            abort(404)
        if recipe.hotlink_enabled and recipe.source_url:
            destination = recipe.hotlink_destination()
            if destination:
                return redirect(destination)
        return render_template("recipes/detail.html", recipe=recipe)

    @blueprint.route("/sources", methods=["GET"])
    def sources() -> str:
        preferences = service.list_source_preferences()
        return render_template("recipes/sources.html", preferences=preferences)

    @blueprint.route("/sources/<path:source_name>/hotlink", methods=["POST"])
    def update_hotlink(source_name: str):
        if len(source_name) > 255:
            abort(400)
        preferences = service.list_source_preferences()
        known_sources = {preference.source_name for preference in preferences}
        if source_name not in known_sources:
            abort(404)
        enabled_values = request.form.getlist("enabled")
        selected_value = enabled_values[-1] if enabled_values else ""
        normalized_value = str(selected_value).strip().lower()
        enabled = normalized_value in {"1", "true", "on", "yes"}
        service.set_hotlink_preference(source_name, enabled)
        return redirect(url_for("recipes.sources"))

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


def _format_heading(
    query: Optional[str],
    ingredients: List[str],
    cuisines: List[str],
    meals: List[str],
    diets: List[str],
) -> str:
    if query and ingredients:
        plural = "s" if len(ingredients) != 1 else ""
        heading = f'Recipes matching "{query}" with {len(ingredients)} ingredient{plural}'
    elif query:
        heading = f'Recipes matching "{query}"'
    elif ingredients:
        heading = "Recipes containing " + ", ".join(ingredients)
    else:
        heading = "Latest recipes"

    descriptors: List[str] = []
    cuisine_labels = labels_for(cuisines, CUISINE_LOOKUP)
    if cuisine_labels:
        descriptors.append("Cuisine: " + ", ".join(cuisine_labels))
    meal_labels = labels_for(meals, MEAL_LOOKUP)
    if meal_labels:
        descriptors.append("Meal: " + ", ".join(meal_labels))
    diet_labels = labels_for(diets, DIET_LOOKUP)
    if diet_labels:
        descriptors.append("Diet: " + ", ".join(diet_labels))

    if descriptors:
        return f"{heading} · {' · '.join(descriptors)}"
    return heading


def _format_subtitle(total: int) -> str:
    suffix = "" if total == 1 else "s"
    return f"{total} recipe{suffix} found"
