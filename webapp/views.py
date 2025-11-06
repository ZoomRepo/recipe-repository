"""Flask views for browsing recipes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Blueprint, abort, jsonify, render_template, request
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
from .models import RecipeDetail, RecipeSummary
from .service import RecipeService


def register_routes(app: Any, service: RecipeService) -> None:
    """Register the HTTP routes on *app* using the provided service."""

    blueprint = Blueprint("recipes", __name__)
    api_blueprint = Blueprint("recipes_api", __name__, url_prefix="/api/v1")

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

    @api_blueprint.route("/recipes")
    def api_recipes_v1() -> Any:
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
        payload = {
            "items": [_serialize_summary(item) for item in results.items],
            "pagination": {
                "page": results.page,
                "pageSize": results.page_size,
                "total": results.total,
                "totalPages": results.total_pages,
            },
            "filters": filters,
        }
        return jsonify(payload)

    @api_blueprint.route("/recipes/<int:recipe_id>")
    def api_recipe_detail(recipe_id: int) -> Any:
        recipe = service.get(recipe_id)
        if recipe is None:
            return jsonify({"error": "Recipe not found"}), 404
        return jsonify(_serialize_detail(recipe))

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
    app.register_blueprint(api_blueprint)


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


def _serialize_summary(recipe: RecipeSummary) -> Dict[str, Any]:
    return {
        "id": recipe.id,
        "title": recipe.title,
        "sourceName": recipe.source_name,
        "sourceUrl": recipe.source_url,
        "description": recipe.description,
        "image": recipe.image,
        "updatedAt": recipe.updated_at.isoformat() if recipe.updated_at else None,
        "ingredients": list(recipe.ingredients),
        "nutrients": recipe.nutrients,
    }


def _serialize_detail(recipe: RecipeDetail) -> Dict[str, Any]:
    payload = _serialize_summary(recipe)
    payload.update(
        {
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions,
            "prepTime": recipe.prep_time,
            "cookTime": recipe.cook_time,
            "totalTime": recipe.total_time,
            "servings": recipe.servings,
            "author": recipe.author,
            "categories": recipe.categories,
            "tags": recipe.tags,
            "raw": recipe.raw,
            "nutrients": recipe.nutrients,
        }
    )
    return payload
