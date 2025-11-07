from pathlib import Path

from flask import Flask, render_template

from webapp.models import PaginatedResult, RecipeSummary

BASE_DIR = Path(__file__).resolve().parent.parent


def render_results(recipe: RecipeSummary) -> str:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "webapp" / "templates"),
        static_folder=str(BASE_DIR / "webapp" / "static"),
    )
    app.add_url_rule("/recipes/<int:recipe_id>", "recipes.detail", lambda recipe_id: "")

    with app.test_request_context():
        return render_template(
            "recipes/_results.html",
            results=PaginatedResult(items=[recipe], total=1, page=1, page_size=1),
            filters={
                "query": "",
                "ingredients": [],
                "cuisines": [],
                "meals": [],
                "diets": [],
            },
        )


def test_overlay_renders_nutrients_and_ingredients() -> None:
    recipe = RecipeSummary(
        id=1,
        title="Test Recipe",
        source_name="Source",
        source_url="https://example.com",
        description="Tasty",
        image=None,
        updated_at=None,
        ingredients=["1 egg", "2 cups milk"],
        raw=None,
        nutrients={"calories": 100.456, "protein": 12.3},
    )

    html = render_results(recipe)

    assert "recipe-card-overlay" in html
    assert "role=\"dialog\"" in html
    assert "View nutrition &amp; ingredients" in html
    assert "Nutrition" in html
    assert "100.46" in html
    assert "2 cups milk" in html


def test_overlay_shows_fallback_messages() -> None:
    recipe = RecipeSummary(
        id=2,
        title="Another Recipe",
        source_name="Source",
        source_url="https://example.com",
        description=None,
        image=None,
        updated_at=None,
        ingredients=[],
        raw=None,
        nutrients=None,
    )

    html = render_results(recipe)

    assert "Nutrition information unavailable." in html
    assert "Ingredients unavailable." in html
    assert "data-role=\"overlay-close\"" in html
