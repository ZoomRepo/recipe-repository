"""Tests for listing discovery fallbacks."""
from __future__ import annotations

import unittest

from scraper.extractors import ListingScraper
from scraper.models import ListingConfig, RecipeTemplate


class DummyResponse:
    def __init__(self, url: str, text: str) -> None:
        self.url = url
        self.text = text
        self.content = text.encode("utf-8")


class DummyHttpClient:
    def __init__(self, html: str) -> None:
        self._html = html
        self.calls = []

    def get(self, url: str, **_: object) -> DummyResponse:
        self.calls.append(url)
        return DummyResponse(url, self._html)


class ListingScraperJsonLdTests(unittest.TestCase):
    def _create_template(self) -> RecipeTemplate:
        return RecipeTemplate(
            name="Test",
            url="https://example.com/recipes/",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="a.selector-that-will-not-match",
                )
            ],
        )

    def test_json_ld_item_list_used_when_selectors_empty(self) -> None:
        html = """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "ItemList",
              "itemListElement": [
                {
                  "@type": "ListItem",
                  "position": 1,
                  "item": {
                    "@type": "Recipe",
                    "@id": "https://example.com/recipes/first",
                    "name": "First"
                  }
                },
                {
                  "@type": "ListItem",
                  "position": 2,
                  "item": {
                    "@type": "Recipe",
                    "url": "/recipes/second"
                  }
                }
              ]
            }
            </script>
          </head>
        </html>
        """
        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = self._create_template()

        urls = scraper.discover(template)

        self.assertEqual(
            urls,
            {
                "https://example.com/recipes/first",
                "https://example.com/recipes/second",
            },
        )
        self.assertEqual(http.calls, ["https://example.com/recipes/"])

    def test_json_ld_urls_ignore_external_domains(self) -> None:
        html = """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "ItemList",
              "itemListElement": [
                {
                  "@type": "ListItem",
                  "item": {
                    "@type": "Recipe",
                    "url": "https://example.com/recipes/local"
                  }
                },
                {
                  "@type": "ListItem",
                  "item": {
                    "@type": "Recipe",
                    "url": "https://other.com/recipes/external"
                  }
                }
              ]
            }
            </script>
          </head>
        </html>
        """
        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = self._create_template()

        urls = scraper.discover(template)

        self.assertEqual(urls, {"https://example.com/recipes/local"})

    def test_json_ld_ignores_non_recipe_types(self) -> None:
        html = """
        <html>
          <head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "ItemList",
              "itemListElement": [
                {
                  "@type": "ListItem",
                  "position": 1,
                  "item": {
                    "@type": "ImageObject",
                    "@id": "https://example.com/wp-content/uploads/photo.jpg"
                  }
                },
                {
                  "@type": "ListItem",
                  "position": 2,
                  "item": {
                    "@type": "Recipe",
                    "@id": "https://example.com/recipes/allowed"
                  }
                }
              ]
            }
            </script>
          </head>
        </html>
        """

        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = self._create_template()

        urls = scraper.discover(template)

        self.assertEqual(urls, {"https://example.com/recipes/allowed"})

    def test_listing_page_url_is_not_returned(self) -> None:
        html = """
        <html>
          <body>
            <a class="link" href="https://example.com/recipes/">Archive</a>
            <a class="link" href="/recipes/best-soup/">Recipe</a>
          </body>
        </html>
        """

        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/recipes/",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="a.link",
                )
            ],
        )

        urls = scraper.discover(template)

        self.assertEqual(urls, {"https://example.com/recipes/best-soup/"})

    def test_asset_urls_are_filtered(self) -> None:
        html = """
        <html>
          <body>
            <a class="link" href="/wp-content/uploads/image.jpg">Image</a>
            <a class="link" href="/recipes/final/">Recipe</a>
          </body>
        </html>
        """

        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/recipes/",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="a.link",
                )
            ],
        )

        urls = scraper.discover(template)

        self.assertEqual(urls, {"https://example.com/recipes/final/"})

    def test_navigation_fragments_are_filtered(self) -> None:
        html = """
        <html>
          <body>
            <a class="link" href="#breadcrumb">Breadcrumbs</a>
            <a class="link" href="#recipe-section">Recipe Section</a>
          </body>
        </html>
        """

        http = DummyHttpClient(html)
        scraper = ListingScraper(http, enable_sitemaps=False)
        template = RecipeTemplate(
            name="Test",
            url="https://example.com/recipes/",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="a.link",
                )
            ],
        )

        urls = scraper.discover(template)

        self.assertEqual(urls, {"https://example.com/recipes/#recipe-section"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
