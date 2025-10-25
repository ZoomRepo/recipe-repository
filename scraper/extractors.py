"""HTML extraction helpers for recipe listings and articles."""
from __future__ import annotations

import gzip
import json
import logging
from collections import deque
from io import BytesIO
from typing import Iterable, Iterator, List, Optional, Sequence, Set
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from .http_client import HttpClient
from .models import ArticleConfig, ListingConfig, Recipe, RecipeTemplate, StructuredDataConfig


class ListingDiscoveryError(RuntimeError):
    """Raised when listing discovery fails for a template."""

    def __init__(self, message: str, last_error: Optional[Exception] = None) -> None:
        if last_error:
            message = f"{message}: {last_error}"
        super().__init__(message)
        self.last_error = last_error

LIST_FIELDS = {"ingredients", "instructions", "categories", "tags"}
SITEMAP_CANDIDATES = (
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap-index.xml",
    "wp-sitemap.xml",
)

logger = logging.getLogger(__name__)


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _extract_text_list(soup: BeautifulSoup, selector: str) -> List[str]:
    return [
        _clean_text(element.get_text(separator=" "))
        for element in soup.select(selector)
        if element.get_text(strip=True)
    ]


def _extract_first_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    for element in soup.select(selector):
        text = element.get_text(separator=" ", strip=True)
        if text:
            return _clean_text(text)
        if element.has_attr("content"):
            return _clean_text(str(element["content"]))
        if element.has_attr("href"):
            return _clean_text(str(element["href"]))
    return None


def _extract_image(soup: BeautifulSoup, selector: str) -> Optional[str]:
    for element in soup.select(selector):
        if element.has_attr("content"):
            return str(element["content"]).strip()
        if element.has_attr("srcset"):
            return element["srcset"].split()[0]
        if element.has_attr("src"):
            return element["src"].strip()
        if element.has_attr("data-src"):
            return element["data-src"].strip()
        if element.name == "img":
            return element.get("src")
    return None


def _detect_list_field(field: str) -> bool:
    return field in LIST_FIELDS


def _safe_json_loads(payload: str) -> Iterable[dict]:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return []
    return data if isinstance(data, list) else [data]


def _walk_recipe_nodes(value) -> Iterator[dict]:
    if isinstance(value, dict):
        if value.get("@type") == "Recipe":
            yield value
        for nested in value.values():
            yield from _walk_recipe_nodes(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_recipe_nodes(item)


def _normalise_sequence(value: Optional[Sequence[str]]) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [_clean_text(value)]
    return [_clean_text(str(item)) for item in value if str(item).strip()]


def _normalise_instructions(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [_clean_text(value)]
    instructions: List[str] = []
    for item in value:
        if isinstance(item, dict):
            text = item.get("text") or item.get("@value")
            if text:
                instructions.append(_clean_text(str(text)))
        else:
            instructions.append(_clean_text(str(item)))
    return [item for item in instructions if item]


class ListingScraper:
    """Scrape recipe article URLs from listing pages."""

    def __init__(
        self,
        http_client: HttpClient,
        max_pages: int = 200,
        enable_sitemaps: bool = True,
        sitemap_max_urls: int = 2000,
    ) -> None:
        self._http = http_client
        self._max_pages = max_pages
        self._enable_sitemaps = enable_sitemaps
        self._sitemap_max_urls = sitemap_max_urls

    def discover(self, template: RecipeTemplate) -> Set[str]:
        discovered: Set[str] = set()
        had_listing_error = False
        last_error: Optional[Exception] = None
        for listing in template.listings:
            try:
                discovered.update(self._scrape_listing(listing))
            except Exception as exc:  # pylint: disable=broad-except
                had_listing_error = True
                last_error = exc
                logger.warning(
                    "Listing discovery failed for %s (%s): %s",
                    template.name,
                    listing.url,
                    exc,
                    extra={
                        "source_name": template.name,
                        "recipe": listing.url,
                    },
                )

        sitemap_urls: Set[str] = set()
        if not discovered and self._enable_sitemaps:
            sitemap_urls = self._discover_from_sitemaps(template)
            if sitemap_urls:
                logger.info(
                    "Sitemap fallback discovered %d article URLs for %s",
                    len(sitemap_urls),
                    template.name,
                )
            elif had_listing_error:
                logger.info(
                    "Sitemap fallback yielded no URLs for %s", template.name
                )
            discovered.update(sitemap_urls)
        if had_listing_error and not discovered:
            raise ListingDiscoveryError(
                f"Failed to discover listings for {template.name}", last_error
            )
        return discovered

    def _scrape_listing(self, listing: ListingConfig) -> Set[str]:
        pages_seen: Set[str] = set()
        article_urls: Set[str] = set()
        next_page = listing.url
        pages_processed = 0
        while next_page and pages_processed < self._max_pages:
            response = self._http.get(next_page)
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = response.url
            for element in soup.select(listing.link_selector):
                href = element.get("href")
                if not href:
                    continue
                article_urls.add(urljoin(base_url, href))

            pages_processed += 1
            pages_seen.add(base_url)
            if listing.pagination_selector:
                next_link = soup.select_one(listing.pagination_selector)
                if next_link and next_link.get("href"):
                    candidate = urljoin(base_url, next_link.get("href"))
                    if candidate not in pages_seen:
                        next_page = candidate
                        continue
            break
        return article_urls

    def _discover_from_sitemaps(self, template: RecipeTemplate) -> Set[str]:
        """Attempt to discover recipe URLs via sitemap crawling."""

        base_candidates = self._candidate_sitemaps(template.url)
        queue = deque(base_candidates)
        visited: Set[str] = set()
        article_urls: Set[str] = set()

        while queue and len(article_urls) < self._sitemap_max_urls:
            sitemap_url = queue.popleft()
            if sitemap_url in visited:
                continue
            visited.add(sitemap_url)

            try:
                response = self._http.get(sitemap_url, timeout=30)
            except Exception as exc:  # pylint: disable=broad-except
                logger.debug("Failed to fetch sitemap %s: %s", sitemap_url, exc)
                continue

            content = self._decode_sitemap_content(sitemap_url, response.content)
            if content is None:
                continue

            try:
                root = ElementTree.fromstring(content)
            except ElementTree.ParseError as exc:
                logger.debug("Failed to parse sitemap %s: %s", sitemap_url, exc)
                continue

            namespace = ""
            if root.tag.startswith("{") and "}" in root.tag:
                namespace = root.tag.split("}")[0].strip("{")
            loc_tag = f"{{{namespace}}}loc" if namespace else "loc"

            for loc in root.iter(loc_tag):
                loc_text = (loc.text or "").strip()
                if not loc_text:
                    continue
                if not self._same_domain(template.url, loc_text):
                    continue

                if loc_text.endswith((".xml", ".xml.gz")):
                    if loc_text not in visited:
                        queue.append(loc_text)
                    continue

                article_urls.add(loc_text)
                if len(article_urls) >= self._sitemap_max_urls:
                    break

        return article_urls

    def _candidate_sitemaps(self, base_url: str) -> List[str]:
        base = base_url.rstrip("/") + "/"
        return [urljoin(base, candidate) for candidate in SITEMAP_CANDIDATES]

    @staticmethod
    def _same_domain(base_url: str, candidate: str) -> bool:
        base = urlparse(base_url)
        target = urlparse(candidate)
        base_host = base.netloc.lower().lstrip("www.")
        target_host = target.netloc.lower().lstrip("www.")
        if target_host and target_host != base_host:
            return False
        return bool(target_host) or (not target.netloc and bool(target.path))

    @staticmethod
    def _decode_sitemap_content(url: str, payload: bytes) -> Optional[bytes]:
        if not payload:
            return None
        if url.endswith(".gz"):
            try:
                return gzip.decompress(payload)
            except OSError:
                try:
                    with gzip.GzipFile(fileobj=BytesIO(payload)) as handle:
                        return handle.read()
                except OSError as exc:  # pylint: disable=broad-except
                    logger.debug("Failed to decompress sitemap %s: %s", url, exc)
                    return None
        return payload


class ArticleScraper:
    """Extract a :class:`Recipe` from a recipe article page."""

    def __init__(self, http_client: HttpClient) -> None:
        self._http = http_client

    def scrape(self, template: RecipeTemplate, url: str) -> Recipe:
        response = self._http.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        structured_recipe = self._extract_structured_data(template.structured_data, soup)
        recipe = Recipe(
            source_name=template.name,
            source_url=url,
        )
        if structured_recipe:
            self._populate_from_structured(recipe, structured_recipe)

        self._populate_from_selectors(recipe, soup, template.article)
        return recipe

    def _extract_structured_data(
        self, config: StructuredDataConfig, soup: BeautifulSoup
    ) -> Optional[dict]:
        if not config.enabled or not config.json_ld_selector:
            return None

        for script in soup.select(config.json_ld_selector):
            payload = script.string or script.get_text()
            for candidate in _safe_json_loads(payload):
                for recipe in _walk_recipe_nodes(candidate):
                    return recipe
        return None

    def _populate_from_structured(self, recipe: Recipe, data: dict) -> None:
        recipe.title = recipe.title or data.get("name")
        recipe.description = recipe.description or data.get("description")
        recipe.ingredients = recipe.ingredients or _normalise_sequence(
            data.get("recipeIngredient")
        )
        recipe.instructions = recipe.instructions or _normalise_instructions(
            data.get("recipeInstructions")
        )
        recipe.prep_time = recipe.prep_time or data.get("prepTime")
        recipe.cook_time = recipe.cook_time or data.get("cookTime")
        recipe.total_time = recipe.total_time or data.get("totalTime")

        servings = data.get("recipeYield")
        if servings and not recipe.servings:
            if isinstance(servings, (list, tuple)):
                servings = servings[0]
            recipe.servings = _clean_text(str(servings))

        image = data.get("image")
        if isinstance(image, list):
            image = image[0]
        elif isinstance(image, dict):
            image = image.get("url")
        if image and not recipe.image:
            recipe.image = str(image)

        author = data.get("author")
        if isinstance(author, list):
            author = author[0]
        if isinstance(author, dict):
            author = author.get("name")
        if isinstance(author, str) and not recipe.author:
            recipe.author = author

        categories = data.get("recipeCategory")
        recipe.categories = recipe.categories or _normalise_sequence(categories)

        keywords = data.get("keywords")
        if isinstance(keywords, str):
            recipe.tags = recipe.tags or [
                _clean_text(part) for part in keywords.split(",") if part.strip()
            ]
        else:
            recipe.tags = recipe.tags or _normalise_sequence(keywords)

        recipe.raw.update({"json_ld": data})

    def _populate_from_selectors(
        self, recipe: Recipe, soup: BeautifulSoup, selectors: ArticleConfig
    ) -> None:
        for field in selectors.iter_fields():
            selector_list = selectors.selectors_for(field)
            if not selector_list:
                continue

            if not hasattr(recipe, field):
                continue

            if field == "image":
                value = self._extract_field(selector_list, soup, image=True)
                if value and not recipe.image:
                    recipe.image = value
                continue

            value = self._extract_field(selector_list, soup, multiple=_detect_list_field(field))
            if value is None:
                continue

            if isinstance(value, list):
                current = getattr(recipe, field)
                if not current:
                    setattr(recipe, field, value)
            else:
                current = getattr(recipe, field)
                if not current:
                    setattr(recipe, field, value)

    def _extract_field(
        self,
        selector_list: Sequence[str],
        soup: BeautifulSoup,
        multiple: bool = False,
        image: bool = False,
    ):
        if image:
            for selector in selector_list:
                result = _extract_image(soup, selector)
                if result:
                    return result
            return None

        if multiple:
            values: List[str] = []
            for selector in selector_list:
                values.extend(_extract_text_list(soup, selector))
            # Remove duplicates while preserving order
            seen = set()
            unique_values = []
            for item in values:
                if item not in seen:
                    unique_values.append(item)
                    seen.add(item)
            return unique_values

        for selector in selector_list:
            value = _extract_first_text(soup, selector)
            if value:
                return value
        return None
