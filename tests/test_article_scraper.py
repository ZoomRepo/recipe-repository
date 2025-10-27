import unittest

from scraper.extractors import ArticleScraper
from scraper.models import ArticleConfig, RecipeTemplate, StructuredDataConfig


class DummyResponse:
    def __init__(self, text: str, url: str) -> None:
        self.text = text
        self.url = url


class DummyHttpClient:
    def __init__(self, html: str) -> None:
        self._html = html

    def get(self, url: str):  # noqa: D401 - simple stub
        return DummyResponse(self._html, url)


class ArticleScraperFallbackTests(unittest.TestCase):
    def test_semistructured_fallback_extracts_lists(self) -> None:
        html = """
        <html>
            <body>
                <h1>Our Moroccan Family Feast</h1>
                <div>
                    <h4>What’s in it...</h4>
                </div>
                <div>
                    <p>
                        2 cups of dried couscous cooked as per instructions<br/>
                        Chopped herbs of your choice (we used a bunch of parsley and mint)<br/>
                        2 tbsp extra virgin olive oil<br/>
                        Juice of 1 lemon<br/>
                        Salt and freshly ground black pepper
                    </p>
                </div>
                <div>
                    <h4>What to do with it...</h4>
                </div>
                <div>
                    <ol>
                        <li>Cook couscous as per instructions.</li>
                        <li>When ready to serve add herbs and season.</li>
                    </ol>
                </div>
                <div>
                    <h4>Ingredients</h4>
                </div>
                <div>
                    <p>
                        600g baby aubergines<br/>
                        4 tbsp of extra virgin olive oil
                    </p>
                </div>
                <div>
                    <h4>Directions</h4>
                </div>
                <div>
                    <ol>
                        <li>Cut the aubergines in half and grill.</li>
                        <li>Combine with tomatoes and spices, then simmer.</li>
                    </ol>
                </div>
            </body>
        </html>
        """
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/article",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": ["h1"],
                    "ingredients": ["ul.ingredients li"],
                    "instructions": ["ul.instructions li"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(recipe.title, "Our Moroccan Family Feast")
        self.assertEqual(
            recipe.ingredients,
            [
                "2 cups of dried couscous cooked as per instructions",
                "Chopped herbs of your choice (we used a bunch of parsley and mint)",
                "2 tbsp extra virgin olive oil",
                "Juice of 1 lemon",
                "Salt and freshly ground black pepper",
                "600g baby aubergines",
                "4 tbsp of extra virgin olive oil",
            ],
        )
        self.assertEqual(
            recipe.instructions,
            [
                "Cook couscous as per instructions.",
                "When ready to serve add herbs and season.",
                "Cut the aubergines in half and grill.",
                "Combine with tomatoes and spices, then simmer.",
            ],
        )

    def test_selectors_preferred_when_present(self) -> None:
        html = """
        <html>
            <body>
                <h1>Structured Recipe</h1>
                <div>
                    <h4>Ingredients</h4>
                    <p>Ignored fallback ingredient</p>
                    <ul class="ingredients">
                        <li>1 cup flour</li>
                        <li>2 eggs</li>
                    </ul>
                </div>
                <div>
                    <h4>Directions</h4>
                    <p>Ignored fallback instruction</p>
                    <ul class="instructions">
                        <li>Mix ingredients.</li>
                        <li>Bake for 20 minutes.</li>
                    </ul>
                </div>
            </body>
        </html>
        """
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/article",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": ["h1"],
                    "ingredients": ["ul.ingredients li"],
                    "instructions": ["ul.instructions li"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(recipe.title, "Structured Recipe")
        self.assertEqual(recipe.ingredients, ["1 cup flour", "2 eggs"])
        self.assertEqual(
            recipe.instructions,
            [
                "Mix ingredients.",
                "Bake for 20 minutes.",
            ],
        )

    def test_semistructured_strong_heading_sections(self) -> None:
        html = """
        <html>
            <body>
                <h1>Ewa Agoyin</h1>
                <p><strong>Ingredients:</strong></p>
                <ul>
                    <li>2 cups honey beans</li>
                    <li>1 cup palm oil</li>
                </ul>
                <div>
                    <p><strong>Method</strong></p>
                </div>
                <div>
                    <p>Soak beans overnight.<br/>Cook until tender.<br/>Blend pepper mix and fry in palm oil.</p>
                </div>
            </body>
        </html>
        """
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/article",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": ["h1"],
                    "ingredients": [".ingredients li"],
                    "instructions": [".instructions li"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(recipe.title, "Ewa Agoyin")
        self.assertEqual(
            recipe.ingredients,
            [
                "2 cups honey beans",
                "1 cup palm oil",
            ],
        )
        self.assertEqual(
            recipe.instructions,
            [
                "Soak beans overnight.",
                "Cook until tender.",
                "Blend pepper mix and fry in palm oil.",
            ],
        )


if __name__ == "__main__":
    unittest.main()
