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

from bs4 import BeautifulSoup, Tag

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


def _split_multiline_text(value: str) -> List[str]:
    parts: List[str] = []
    for raw in value.splitlines():
        cleaned = _clean_text(raw)
        if cleaned:
            parts.append(cleaned)
    return parts


def _extract_text_list(soup: BeautifulSoup, selector: str) -> List[str]:
    values: List[str] = []
    for element in soup.select(selector):
        if not element.get_text(strip=True):
            continue
        raw_text = element.get_text(separator="\n")
        values.extend(_split_multiline_text(raw_text))
    return values


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
        if element.has_attr("data-srcset"):
            return element["data-srcset"].split()[0]
        if element.has_attr("src"):
            return element["src"].strip()
        if element.has_attr("data-src"):
            return element["data-src"].strip()
        if element.has_attr("data-lazy-src"):
            return element["data-lazy-src"].strip()
        if element.has_attr("data-original"):
            return element["data-original"].strip()
        if element.has_attr("data-pin-media"):
            return element["data-pin-media"].strip()
        if element.name == "img":
            return element.get("src")
    return None


def _normalise_url(candidate: Optional[str], base_url: str) -> Optional[str]:
    if not candidate:
        return None
    cleaned = candidate.strip()
    if not cleaned:
        return None
    return urljoin(base_url, cleaned)


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


def _same_domain(base_url: str, candidate: str) -> bool:
    base = urlparse(base_url)
    target = urlparse(candidate)
    base_host = base.netloc.lower().lstrip("www.")
    target_host = target.netloc.lower().lstrip("www.")
    if target_host and target_host != base_host:
        return False
    return bool(target_host) or (not target.netloc and bool(target.path))


def _collect_json_ld_urls(node) -> Set[str]:
    """Return potential article URLs discovered within a JSON-LD node."""

    urls: Set[str] = set()
    if isinstance(node, dict):
        for key in ("url", "@id"):
            value = node.get(key)
            if isinstance(value, str):
                candidate = value.strip()
                if candidate:
                    urls.add(candidate)

        main_entity = node.get("mainEntityOfPage")
        if isinstance(main_entity, str):
            candidate = main_entity.strip()
            if candidate:
                urls.add(candidate)
        elif isinstance(main_entity, (dict, list)):
            urls.update(_collect_json_ld_urls(main_entity))

        if node.get("@type") == "ItemList":
            urls.update(_collect_json_ld_urls(node.get("itemListElement")))

        for value in node.values():
            if isinstance(value, (dict, list)):
                urls.update(_collect_json_ld_urls(value))

    elif isinstance(node, list):
        for item in node:
            urls.update(_collect_json_ld_urls(item))

    return urls


def _extract_listing_links_from_jsonld(soup: BeautifulSoup, base_url: str) -> Set[str]:
    """Derive article URLs from JSON-LD blobs embedded on listing pages."""

    discovered: Set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        payload = script.string or script.get_text()
        for candidate in _safe_json_loads(payload):
            for url in _collect_json_ld_urls(candidate):
                if not url:
                    continue
                absolute = urljoin(base_url, url)
                if not absolute:
                    continue
                if not _same_domain(base_url, absolute):
                    continue
                discovered.add(absolute)

    return discovered


HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
STRONG_TAGS = {"strong", "b"}
SECTION_CONTAINER_TAGS = set(HEADING_TAGS) | {"p", "div", "span", "section"}
INGREDIENT_HEADINGS = {
    "ingredient",
    "ingredients",
    "what's in",
    "what’s in",
    "whats in",
    "you will need",
    "you'll need",
    "you will require",
    "shopping list",
}
INSTRUCTION_HEADINGS = {
    "instruction",
    "instructions",
    "method",
    "methods",
    "direction",
    "directions",
    "step",
    "steps",
    "how to",
    "what to do",
    "preparation",
    "prep",
}


def _section_label(element: Tag) -> Optional[str]:
    if element.name not in SECTION_CONTAINER_TAGS:
        return None

    if element.name in HEADING_TAGS:
        text = element.get_text(separator=" ")
    else:
        strong = None
        for candidate in element.find_all(list(STRONG_TAGS)):
            preceding = "".join(
                str(sibling).strip() for sibling in candidate.previous_siblings if str(sibling).strip()
            )
            if not preceding:
                strong = candidate
                break
        if strong is None:
            return None
        text = strong.get_text(separator=" ")
    cleaned = _clean_text(text) if text else ""
    if cleaned.endswith(":"):
        cleaned = cleaned[:-1].strip()
    return cleaned or None


def _matches_heading(heading: Tag, keywords: Set[str]) -> bool:
    text = _section_label(heading)
    if not text:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _is_section_heading(element: Tag) -> bool:
    return _section_label(element) is not None


def _extract_inline_section_items(heading: Tag) -> List[str]:
    if heading.name in HEADING_TAGS:
        return []

    strong = heading.find(list(STRONG_TAGS))
    if strong is None:
        return []

    parts: List[str] = []
    for sibling in strong.next_siblings:
        if isinstance(sibling, Tag):
            if sibling.name in STRONG_TAGS:
                continue
            if sibling.name == "br":
                parts.append("\n")
                continue
            parts.append(sibling.get_text(separator="\n"))
        else:
            parts.append(str(sibling))

    combined = "".join(parts)
    inline_items: List[str] = []
    for text in _split_multiline_text(combined):
        stripped = text.lstrip(":;-–— ").strip()
        if stripped:
            inline_items.append(stripped)
    return inline_items


def _extract_section_items(heading: Tag) -> List[str]:
    items: List[str] = _extract_inline_section_items(heading)
    heading_parents = set(heading.parents)
    for element in heading.next_elements:
        if element is heading:
            continue
        if isinstance(element, Tag) and _is_section_heading(element):
            if heading in element.parents or element in heading_parents:
                continue
            break
        if isinstance(element, Tag):
            if element.name in {"ul", "ol"}:
                for item in element.find_all("li"):
                    items.extend(_split_multiline_text(item.get_text(separator="\n")))
            elif element.name == "p":
                items.extend(_split_multiline_text(element.get_text(separator="\n")))
    seen: Set[str] = set()
    unique_items: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique_items.append(item)
    return unique_items


def _extract_semistructured_lists(soup: BeautifulSoup, keywords: Set[str]) -> List[str]:
    values: List[str] = []
    for heading in soup.find_all(list(SECTION_CONTAINER_TAGS)):
        if _matches_heading(heading, keywords):
            values.extend(_extract_section_items(heading))
    return values


def _extract_wprm_fallback_lists(soup: BeautifulSoup, field_name: str) -> List[str]:
    """Extract lists from WP Recipe Maker fallback markup."""

    suffix = None
    if field_name == "ingredients":
        suffix = "ingredients"
    elif field_name == "instructions":
        suffix = "instructions"

    if not suffix:
        return []

    selector = f".wprm-fallback-recipe-{suffix}"
    values: List[str] = []
    for container in soup.select(selector):
        items: List[str] = []
        for li in container.find_all("li"):
            items.extend(_split_multiline_text(li.get_text(separator="\n")))

        if not items:
            for paragraph in container.find_all("p"):
                items.extend(_split_multiline_text(paragraph.get_text(separator="\n")))

        for item in items:
            cleaned = item.strip()
            if cleaned:
                values.append(cleaned)

    # Deduplicate while preserving order
    seen: Set[str] = set()
    unique_values: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values


def _extract_microdata_lists(soup: BeautifulSoup, field_name: str) -> List[str]:
    """Extract lists from schema.org microdata when available."""

    if field_name == "ingredients":
        props = ("recipeIngredient", "ingredients")
    elif field_name == "instructions":
        props = (
            "recipeInstructions",
            "instructions",
        )
    else:
        return []

    values: List[str] = []

    def collect_text(element: Tag) -> None:
        nonlocal values

        text_nodes = element.find_all(attrs={"itemprop": "text"})
        if text_nodes:
            for node in text_nodes:
                values.extend(
                    _split_multiline_text(node.get_text(separator="\n"))
                )
            return

        if element.name in {"ul", "ol"}:
            for item in element.find_all("li"):
                values.extend(
                    _split_multiline_text(item.get_text(separator="\n"))
                )
            return

        if element.name in {"li", "p", "span", "div"}:
            values.extend(
                _split_multiline_text(element.get_text(separator="\n"))
            )

    for prop in props:
        for element in soup.find_all(attrs={"itemprop": prop}):
            if element.find_parent(attrs={"itemprop": prop}):
                continue
            collect_text(element)

    seen: Set[str] = set()
    unique_values: List[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique_values.append(cleaned)
    return unique_values


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
        had_listing_results = False
        for listing in template.listings:
            try:
                urls = self._scrape_listing(listing)
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
                continue

            if urls:
                discovered.update(urls)
                had_listing_results = True
            else:
                logger.debug(
                    "Listing discovery yielded no URLs for %s using selector %s",
                    listing.url,
                    listing.link_selector,
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
        if not discovered and not had_listing_results:
            raise ListingDiscoveryError(
                f"No article URLs discovered for {template.name} "
                f"({template.url}). Verify the listing link selector configuration."
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
            page_urls: Set[str] = set()
            for element in soup.select(listing.link_selector):
                href = element.get("href")
                if not href:
                    continue
                page_urls.add(urljoin(base_url, href))

            if not page_urls:
                json_ld_links = _extract_listing_links_from_jsonld(soup, base_url)
                if json_ld_links:
                    logger.debug(
                        "Listing discovery recovered %d URLs from JSON-LD on %s",
                        len(json_ld_links),
                        base_url,
                    )
                page_urls.update(json_ld_links)

            article_urls.update(page_urls)

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
        return _same_domain(base_url, candidate)

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
        self._apply_generic_fallbacks(recipe, soup, response.url)
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
                value = self._extract_field(
                    selector_list, soup, image=True, field_name=field
                )
                if value and not recipe.image:
                    recipe.image = value
                continue

            value = self._extract_field(
                selector_list,
                soup,
                multiple=_detect_list_field(field),
                field_name=field,
            )
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
        field_name: Optional[str] = None,
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
            if not values and field_name == "ingredients":
                values = _extract_wprm_fallback_lists(soup, field_name)
                if values:
                    return values
                values = _extract_microdata_lists(soup, field_name)
                if values:
                    return values
                values = _extract_semistructured_lists(soup, INGREDIENT_HEADINGS)
            elif not values and field_name == "instructions":
                values = _extract_wprm_fallback_lists(soup, field_name)
                if values:
                    return values
                values = _extract_microdata_lists(soup, field_name)
                if values:
                    return values
                values = _extract_semistructured_lists(soup, INSTRUCTION_HEADINGS)
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

    def _apply_generic_fallbacks(
        self, recipe: Recipe, soup: BeautifulSoup, base_url: str
    ) -> None:
        if not recipe.title:
            for selector in (
                "meta[property='og:title']",
                "meta[property='og:title:alt']",
                "meta[name='twitter:title']",
                "meta[name='title']",
                "title",
            ):
                value = _extract_first_text(soup, selector)
                if value:
                    recipe.title = value
                    break

        if not recipe.image:
            for selector in (
                "meta[property='og:image']",
                "meta[property='og:image:url']",
                "meta[property='og:image:secure_url']",
                "meta[name='twitter:image']",
                "meta[name='twitter:image:src']",
                "link[rel='image_src']",
            ):
                candidate = _extract_image(soup, selector)
                if not candidate:
                    continue
                absolute = _normalise_url(candidate, base_url)
                if absolute:
                    recipe.image = absolute
                    break

        if not recipe.image:
            for selector in (
                "article img",
                "div.entry-content img",
                "div.post-content img",
                "main img",
                "img",
            ):
                candidate = _extract_image(soup, selector)
                if not candidate:
                    continue
                absolute = _normalise_url(candidate, base_url)
                if absolute:
                    recipe.image = absolute
                    break
