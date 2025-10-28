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


class MultiPageHttpClient:
    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages
        self.calls: list[str] = []

    def get(self, url: str, **_: object) -> DummyResponse:
        self.calls.append(url)
        html = self._pages.get(url)
        if html is None and not url.endswith("/"):
            html = self._pages.get(f"{url}/")
        if html is None:
            raise AssertionError(f"Unexpected URL requested: {url}")
        return DummyResponse(url, html)


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

    def test_pagination_discovers_additional_pages(self) -> None:
        page_one = """
        <html>
          <body>
            <article><h2><a href="/recipes/seffa/">Seffa</a></h2></article>
            <article><h2><a href="/recipes/mint-tea/">Mint Tea</a></h2></article>
            <nav class="pagination">
              <a class="page-numbers" href="/recipes/page/2/">2</a>
              <a class="page-numbers" href="/recipes/page/3/">3</a>
            </nav>
          </body>
        </html>
        """

        page_two = """
        <html>
          <body>
            <article><h2><a href="/recipes/bread/">Coconut Bread</a></h2></article>
            <nav class="pagination">
              <a class="page-numbers" href="/recipes/page/3/">3</a>
            </nav>
          </body>
        </html>
        """

        page_three = """
        <html>
          <body>
            <article><h2><a href="/recipes/drink/">Sorrel Drink</a></h2></article>
          </body>
        </html>
        """

        http = MultiPageHttpClient(
            {
                "https://example.com/recipes/": page_one,
                "https://example.com/recipes/page/2/": page_two,
                "https://example.com/recipes/page/3/": page_three,
            }
        )

        scraper = ListingScraper(http, enable_sitemaps=False, max_pages=10)
        template = RecipeTemplate(
            name="Come Chop",
            url="https://example.com/recipes/",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="article h2 a",
                    pagination_selector="a.page-numbers",
                )
            ],
        )

        urls = scraper.discover(template)

        self.assertEqual(
            urls,
            {
                "https://example.com/recipes/seffa/",
                "https://example.com/recipes/mint-tea/",
                "https://example.com/recipes/bread/",
                "https://example.com/recipes/drink/",
            },
        )
        self.assertEqual(len(http.calls), 3)
        self.assertEqual(
            set(http.calls),
            {
                "https://example.com/recipes/",
                "https://example.com/recipes/page/2/",
                "https://example.com/recipes/page/3/",
            },
        )

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


class ListingScraperSitemapTests(unittest.TestCase):
    def test_sitemaps_used_before_listing_and_skip_non_recipe_storage(self) -> None:
        sitemap_index = """<?xml version='1.0' encoding='UTF-8'?>
        <sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
          <sitemap>
            <loc>https://example.com/storage/recipes-1.xml</loc>
          </sitemap>
          <sitemap>
            <loc>https://example.com/storage/pages-1.xml</loc>
          </sitemap>
        </sitemapindex>
        """

        recipe_sitemap = """<?xml version='1.0' encoding='UTF-8'?>
        <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
          <url><loc>https://example.com/recipes/first/</loc></url>
          <url><loc>https://example.com/recipes/second/</loc></url>
        </urlset>
        """

        empty_sitemap = """<?xml version='1.0' encoding='UTF-8'?>
        <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'></urlset>
        """

        listing_html = """
        <html>
          <body>
            <article><h2><a href="/recipes/from-listing/">Listing Recipe</a></h2></article>
          </body>
        </html>
        """

        http = MultiPageHttpClient(
            {
                "https://example.com/sitemap.xml": sitemap_index,
                "https://example.com/sitemap_index.xml": empty_sitemap,
                "https://example.com/sitemap-index.xml": empty_sitemap,
                "https://example.com/wp-sitemap.xml": empty_sitemap,
                "https://example.com/storage/recipes-1.xml": recipe_sitemap,
                "https://example.com/recipes/": listing_html,
            }
        )

        scraper = ListingScraper(http, enable_sitemaps=True)
        template = RecipeTemplate(
            name="Food Network",
            url="https://example.com/collections/argentinian-recipes#all-recipes",
            type="cooking",
            listings=[
                ListingConfig(
                    url="https://example.com/recipes/",
                    link_selector="article h2 a",
                )
            ],
        )

        urls = scraper.discover(template)

        self.assertEqual(
            urls,
            {
                "https://example.com/recipes/first/",
                "https://example.com/recipes/second/",
                "https://example.com/recipes/from-listing/",
            },
        )

        self.assertIn("https://example.com/sitemap.xml", http.calls)
        self.assertNotIn("https://example.com/storage/pages-1.xml", http.calls)
        self.assertLess(
            http.calls.index("https://example.com/sitemap.xml"),
            http.calls.index("https://example.com/recipes/"),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
