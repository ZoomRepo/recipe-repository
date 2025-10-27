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

    def test_microdata_fallback_extracts_lists(self) -> None:
        html = """
        <html>
            <body>
                <article itemscope itemtype="https://schema.org/Recipe">
                    <h1 itemprop="name">Bajan Sweet Bread</h1>
                    <section>
                        <ul>
                            <li itemprop="recipeIngredient">3 cups flour</li>
                            <li itemprop="recipeIngredient">1 cup sugar</li>
                        </ul>
                        <p itemprop="recipeIngredient">1 cup grated coconut</p>
                    </section>
                    <div itemprop="recipeInstructions">
                        <ol>
                            <li>Combine dry ingredients.</li>
                            <li>Stir in coconut and bake.</li>
                        </ol>
                    </div>
                    <div itemprop="recipeInstructions">
                        <p itemprop="text">Cool before slicing.</p>
                    </div>
                </article>
            </body>
        </html>
        """

        template = RecipeTemplate(
            name="Test",
            url="https://example.com/article",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": ["h1[itemprop='name']"],
                    "ingredients": [".ingredients li"],
                    "instructions": [".instructions li"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(recipe.title, "Bajan Sweet Bread")
        self.assertEqual(
            recipe.ingredients,
            [
                "3 cups flour",
                "1 cup sugar",
                "1 cup grated coconut",
            ],
        )
        self.assertEqual(
            recipe.instructions,
            [
                "Combine dry ingredients.",
                "Stir in coconut and bake.",
                "Cool before slicing.",
            ],
        )


    def test_wprm_fallback_markup(self) -> None:
        html = """
        <html>
            <body>
                <h1>African Fried chicken</h1>
                <div class="wprm-fallback-recipe">
                    <div class="wprm-fallback-recipe-ingredients">
                        <ul>
                            <li>2 chicken</li>
                            <li>1 onion (1/2 sliced)</li>
                            <li>1 tablespoon ginger</li>
                        </ul>
                    </div>
                    <div class="wprm-fallback-recipe-instructions">
                        <ol>
                            <li>Grind the spices with the least amount of water as possible.</li>
                            <li>Mix the chicken with the blended spices and simmer.</li>
                            <li>Fry in batches until golden.</li>
                        </ol>
                    </div>
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

        self.assertEqual(recipe.title, "African Fried chicken")
        self.assertEqual(
            recipe.ingredients,
            [
                "2 chicken",
                "1 onion (1/2 sliced)",
                "1 tablespoon ginger",
            ],
        )
        self.assertEqual(
            recipe.instructions,
            [
                "Grind the spices with the least amount of water as possible.",
                "Mix the chicken with the blended spices and simmer.",
                "Fry in batches until golden.",
            ],
        )

    def test_generic_meta_title_and_image_fallback(self) -> None:
        html = """
        <html>
            <head>
                <title>Poached Apricots - Ozlem's Turkish Table</title>
                <meta property="og:title" content="Poached Dried Apricots in Light Syrup with Kaymak" />
                <meta property="og:image" content="https://cdn.example.com/images/apricots.jpg" />
            </head>
            <body>
                <article>
                    <p>Recipe content.</p>
                </article>
            </body>
        </html>
        """

        template = RecipeTemplate(
            name="Test",
            url="https://example.com/apricots",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": [".missing-title"],
                    "image": [".missing-image"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(
            recipe.title, "Poached Dried Apricots in Light Syrup with Kaymak"
        )
        self.assertEqual(
            recipe.image, "https://cdn.example.com/images/apricots.jpg"
        )

    def test_data_attribute_image_fallback_is_absolute(self) -> None:
        html = """
        <html>
            <head>
                <title>Baobab Drink</title>
            </head>
            <body>
                <div class="entry-content">
                    <img data-lazy-src="/wp-content/uploads/baobab-drink.jpg" alt="Baobab Drink" />
                </div>
            </body>
        </html>
        """

        template = RecipeTemplate(
            name="Test",
            url="https://naturallyzimbabwean.com/baobab-drink/",
            type="cooking",
            article=ArticleConfig(
                selectors={
                    "title": [".missing-title"],
                    "image": [".missing-image"],
                }
            ),
            structured_data=StructuredDataConfig(enabled=False),
        )

        scraper = ArticleScraper(DummyHttpClient(html))
        recipe = scraper.scrape(template, template.url)

        self.assertEqual(recipe.title, "Baobab Drink")
        self.assertEqual(
            recipe.image,
            "https://naturallyzimbabwean.com/wp-content/uploads/baobab-drink.jpg",
        )


if __name__ == "__main__":
    unittest.main()
