"""HTML extraction helpers for recipe listings and articles."""
from __future__ import annotations

import gzip
import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from io import BytesIO
from typing import Iterable, Iterator, List, Optional, Sequence, Set
from urllib.parse import parse_qs, urljoin, urlparse
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


class ArticleExtractionError(RuntimeError):
    """Raised when a recipe article cannot be populated with core content."""


LIST_FIELDS = {"ingredients", "instructions", "categories", "tags"}
SITEMAP_CANDIDATES = (
    "sitemap.xml",
    "sitemap_index.xml",
    "sitemap-index.xml",
    "wp-sitemap.xml",
)

STORAGE_SITEMAP_EXCLUDE_KEYWORDS = {
    "pages",
    "chefs",
    "collections",
    "playlists",
    "shows",
    "spotlights",
    "videos",
}

NAVIGATION_FRAGMENT_KEYWORDS = {
    "breadcrumb",
    "comment",
    "comments",
    "respond",
    "reply",
    "share",
    "print",
    "menu",
    "nav",
    "footer",
    "header",
}

ASSET_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".svg",
    ".webp",
    ".tif",
    ".tiff",
    ".ico",
    ".pdf",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
    ".mp4",
    ".mp3",
    ".mov",
    ".avi",
    ".m4v",
    ".webm",
    ".ogg",
    ".ogv",
    ".wav",
}

LISTING_JSONLD_ALLOWED_TYPES = {
    "recipe",
    "article",
    "blogposting",
    "newsarticle",
    "howto",
    "creativework",
}

logger = logging.getLogger(__name__)


@dataclass
class RecipeSection:
    """Represents a logical recipe grouping discovered within a page."""

    title: Optional[str] = None
    anchor: Optional[str] = None
    ingredients: List[str] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    image: Optional[str] = None
    container: Optional[Tag] = None
    heading: Optional[Tag] = None

    def has_content(self) -> bool:
        return bool(self.ingredients or self.instructions)


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


def _is_navigation_fragment(fragment: str) -> bool:
    lowered = fragment.lower()
    return any(keyword in lowered for keyword in NAVIGATION_FRAGMENT_KEYWORDS)


def _looks_like_asset_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in ASSET_EXTENSIONS):
        return True
    if path.endswith("/feed/") or path.endswith("/feed"):
        return True
    if parsed.query:
        query = parse_qs(parsed.query)
        if any(key in query for key in ("attachment_id", "download")):
            return True
    return False


def _normalise_base_url(url: str) -> str:
    return url.split("#", 1)[0].rstrip("/")


def _dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    unique: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _normalise_jsonld_types(value) -> Set[str]:
    types: Set[str] = set()
    if isinstance(value, str):
        types.add(value.lower())
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                types.add(item.lower())
    return types


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: Optional[str]) -> str:
    if not value:
        return ""
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug


def _extract_image_from_tag(element: Tag) -> Optional[str]:
    if element.has_attr("content"):
        candidate = str(element["content"]).strip()
        if candidate:
            return candidate
    if element.has_attr("srcset"):
        candidate = str(element["srcset"]).strip()
        if candidate:
            return candidate.split()[0]
    if element.has_attr("data-srcset"):
        candidate = str(element["data-srcset"]).strip()
        if candidate:
            return candidate.split()[0]
    for attribute in (
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-pin-media",
    ):
        if element.has_attr(attribute):
            candidate = str(element[attribute]).strip()
            if candidate:
                return candidate
    if element.name == "img":
        candidate = element.get("src")
        if candidate:
            return str(candidate)
    return None


def _find_section_image(heading: Tag) -> Optional[str]:
    def search_forward() -> Optional[str]:
        for element in heading.next_elements:
            if element is heading:
                continue
            if isinstance(element, Tag):
                label = _section_label(element)
                if label and not _is_content_heading_text(label):
                    return None
                if element.name == "img":
                    candidate = _extract_image_from_tag(element)
                    if candidate:
                        return candidate
        return None

    def search_backward() -> Optional[str]:
        for element in heading.previous_elements:
            if isinstance(element, Tag):
                label = _section_label(element)
                if label and not _is_content_heading_text(label):
                    return None
                if element.name == "img":
                    candidate = _extract_image_from_tag(element)
                    if candidate:
                        return candidate
        return None

    return search_forward() or search_backward()


def _heading_level(element: Tag) -> int:
    if element.name in HEADING_TAGS:
        try:
            return int(element.name[1])
        except (IndexError, ValueError):
            return 7
    return 7


def _extract_recipe_sections(soup: BeautifulSoup) -> List[RecipeSection]:
    sections: List[RecipeSection] = []
    current: Optional[RecipeSection] = None
    current_title_level: Optional[int] = None
    last_field: Optional[str] = None

    def ensure_current() -> RecipeSection:
        nonlocal current
        if current is None:
            current = RecipeSection()
        return current

    def attach_container(section: RecipeSection, element: Tag) -> None:
        if section.container is None:
            section.container = element.parent if isinstance(element.parent, Tag) else element

    def finalise_current() -> None:
        nonlocal current, current_title_level, last_field
        if current:
            current.ingredients = _dedupe_preserve_order(current.ingredients)
            current.instructions = _dedupe_preserve_order(current.instructions)
            if current.has_content():
                sections.append(current)
        current = None
        current_title_level = None
        last_field = None

    for element in soup.find_all(list(SECTION_CONTAINER_TAGS)):
        label = _section_label(element)
        if not label:
            continue
        lowered = label.lower()
        level = _heading_level(element)

        if any(keyword in lowered for keyword in INGREDIENT_HEADINGS):
            section = ensure_current()
            section.ingredients.extend(_extract_section_items(element))
            attach_container(section, element)
            last_field = "ingredients"
            if element.name in HEADING_TAGS:
                heading_level = _heading_level(element)
                if current_title_level is None or heading_level < current_title_level:
                    current_title_level = heading_level
            continue
        if any(keyword in lowered for keyword in INSTRUCTION_HEADINGS):
            section = ensure_current()
            section.instructions.extend(_extract_section_items(element))
            attach_container(section, element)
            last_field = "instructions"
            if element.name in HEADING_TAGS:
                heading_level = _heading_level(element)
                if current_title_level is None or heading_level < current_title_level:
                    current_title_level = heading_level
            continue

        if current and not current.has_content() and last_field is None:
            current = None
            current_title_level = None
            last_field = None

        if current and current.instructions:
            boundary_level = current_title_level if current_title_level is not None else 0
            if level <= boundary_level:
                if current.has_content():
                    finalise_current()
                else:
                    current = None
            else:
                # Treat as a subsection that continues instruction content.
                items = _extract_section_items(element)
                if items:
                    current.instructions.extend(items)
                    last_field = "instructions"
                    attach_container(current, element)
                continue

        if current is None:
            current = RecipeSection(
                title=label,
                anchor=(element.get("id") or element.get("data-id")),
                image=_find_section_image(element),
                container=element.parent if isinstance(element.parent, Tag) else element,
                heading=element if isinstance(element, Tag) else None,
            )
            current_title_level = level
            continue

        # Treat as a subsection of the current recipe.
        if not current.title:
            current.title = label
            current.anchor = current.anchor or element.get("id") or element.get("data-id")
            if not current.image:
                current.image = _find_section_image(element)
            if current.heading is None and isinstance(element, Tag):
                current.heading = element
            current_title_level = level
        else:
            items = _extract_section_items(element)
            if items:
                if last_field == "instructions":
                    current.instructions.extend(items)
                else:
                    current.ingredients.extend(items)
                    last_field = "ingredients"
            attach_container(current, element)

    if current and current.has_content():
        finalise_current()
    elif current and not current.has_content():
        current = None

    return sections


def _ensure_unique_anchor(anchor: str, used: Set[str]) -> str:
    candidate = anchor
    index = 2
    while candidate in used:
        candidate = f"{anchor}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def _resolve_section_anchor(
    section: Optional[RecipeSection],
    index: int,
    fallback_title: Optional[str],
    used: Set[str],
) -> str:
    if section and section.anchor:
        anchor = section.anchor.strip().lstrip("#")
        if anchor:
            return _ensure_unique_anchor(anchor, used)

    for candidate in (
        section.title if section else None,
        fallback_title,
        f"recipe-{index + 1}",
    ):
        slug = _slugify(candidate)
        if slug:
            anchor = slug
            if not anchor.startswith("recipe-"):
                anchor = f"recipe-{anchor}"
            return _ensure_unique_anchor(anchor, used)

    return _ensure_unique_anchor(f"recipe-{index + 1}", used)


def _resolve_section_image(section: RecipeSection, base_url: str) -> Optional[str]:
    seen: Set[str] = set()

    def consider(candidate: Optional[str]) -> Optional[str]:
        if not candidate:
            return None
        cleaned = candidate.strip()
        if not cleaned or cleaned in seen:
            return None
        seen.add(cleaned)
        normalised = _normalise_url(cleaned, base_url)
        return normalised or cleaned

    image = consider(section.image)
    if image:
        return image

    if section.heading is not None:
        heading_image = _find_section_image(section.heading)
        image = consider(heading_image)
        if image:
            return image

    if section.container is not None:
        for img in section.container.find_all("img"):
            image = consider(_extract_image_from_tag(img))
            if image:
                return image

    return None


def _collect_json_ld_urls(node) -> Set[str]:
    """Return potential article URLs discovered within a JSON-LD node."""

    urls: Set[str] = set()
    if isinstance(node, dict):
        types = _normalise_jsonld_types(node.get("@type"))
        is_allowed = not types or any(
            item in LISTING_JSONLD_ALLOWED_TYPES for item in types
        )
        for key in ("url", "@id"):
            value = node.get(key)
            if isinstance(value, str) and is_allowed:
                candidate = value.strip()
                if candidate:
                    urls.add(candidate)

        main_entity = node.get("mainEntityOfPage")
        if isinstance(main_entity, str) and is_allowed:
            candidate = main_entity.strip()
            if candidate:
                urls.add(candidate)
        elif isinstance(main_entity, (dict, list)):
            urls.update(_collect_json_ld_urls(main_entity))

        if "itemlist" in types:
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
                if _looks_like_asset_url(absolute):
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

SECTION_CONTENT_KEYWORDS = INGREDIENT_HEADINGS | INSTRUCTION_HEADINGS


def _section_label(element: Tag) -> Optional[str]:
    if element.name not in SECTION_CONTAINER_TAGS:
        return None

    if element.name in HEADING_TAGS:
        text = element.get_text(separator=" ")
    else:
        if element.find(list(HEADING_TAGS)):
            return None

        strong = None
        for child in element.children:
            if isinstance(child, Tag):
                if child.name in STRONG_TAGS:
                    strong = child
                    break
                nested = child.find(list(STRONG_TAGS), recursive=False)
                if nested is not None:
                    strong = nested
                    break
                if child.name not in {"br"} and child.get_text(strip=True):
                    return None
            else:
                if str(child).strip():
                    return None
        if strong is None:
            return None
        text = strong.get_text(separator=" ")
    cleaned = _clean_text(text) if text else ""
    if cleaned.endswith(":"):
        cleaned = cleaned[:-1].strip()
    return cleaned or None


def _is_content_heading_text(value: str) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in SECTION_CONTENT_KEYWORDS)


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

        if self._enable_sitemaps:
            sitemap_urls = self._discover_from_sitemaps(template)
            if sitemap_urls:
                logger.info(
                    "Discovered %d article URLs for %s via sitemaps",
                    len(sitemap_urls),
                    template.name,
                    extra={
                        "source_name": template.name,
                    },
                )
                discovered.update(sitemap_urls)
        for listing in template.listings:
            try:
                urls = self._scrape_listing(template.url, listing)
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

    def _scrape_listing(
        self, template_url: str, listing: ListingConfig
    ) -> Set[str]:
        pages_seen: Set[str] = set()
        queued_pages: Set[str] = set()
        article_urls: Set[str] = set()
        queue = deque([listing.url])
        queued_pages.add(_normalise_base_url(listing.url))
        pages_processed = 0

        while queue and pages_processed < self._max_pages:
            next_page = queue.popleft()
            queued_pages.discard(_normalise_base_url(next_page))

            normalised_next = _normalise_base_url(next_page)
            if normalised_next in pages_seen:
                continue

            response = self._http.get(next_page)
            soup = BeautifulSoup(response.text, "html.parser")
            base_url = response.url
            base_normalised = _normalise_base_url(base_url)

            if base_normalised in pages_seen:
                pages_processed += 1
                continue

            page_urls: Set[str] = set()
            for element in soup.select(listing.link_selector):
                href = element.get("href")
                if not href:
                    continue
                absolute = urljoin(base_url, href)
                if self._should_include_url(template_url, listing.url, absolute):
                    page_urls.add(absolute)

            if not page_urls:
                json_ld_links = _extract_listing_links_from_jsonld(soup, base_url)
                if json_ld_links:
                    logger.debug(
                        "Listing discovery recovered %d URLs from JSON-LD on %s",
                        len(json_ld_links),
                        base_url,
                    )
                page_urls.update(
                    {
                        link
                        for link in json_ld_links
                        if self._should_include_url(
                            template_url, listing.url, link
                        )
                    }
                )

            article_urls.update(page_urls)

            pages_processed += 1
            pages_seen.add(base_normalised)
            if normalised_next:
                pages_seen.add(normalised_next)

            if listing.pagination_selector:
                for link in soup.select(listing.pagination_selector):
                    href = link.get("href")
                    if not href:
                        continue
                    candidate = urljoin(base_url, href)
                    if not candidate:
                        continue
                    if not _same_domain(listing.url, candidate):
                        continue
                    candidate_base = _normalise_base_url(candidate)
                    if not candidate_base:
                        continue
                    if candidate_base in pages_seen or candidate_base in queued_pages:
                        continue
                    queue.append(candidate)
                    queued_pages.add(candidate_base)
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
                    if not self._should_queue_sitemap(template.url, loc_text):
                        continue
                    if loc_text not in visited:
                        queue.append(loc_text)
                    continue

                if self._should_include_url(template.url, template.url, loc_text):
                    article_urls.add(loc_text)
                if len(article_urls) >= self._sitemap_max_urls:
                    break

        return article_urls

    def _candidate_sitemaps(self, base_url: str) -> List[str]:
        parsed = urlparse(base_url)
        if parsed.scheme and parsed.netloc:
            base = f"{parsed.scheme}://{parsed.netloc}/"
        else:
            base = base_url.split("#", 1)[0].rstrip("/") + "/"
        return [urljoin(base, candidate) for candidate in SITEMAP_CANDIDATES]

    @staticmethod
    def _same_domain(base_url: str, candidate: str) -> bool:
        return _same_domain(base_url, candidate)

    @staticmethod
    def _should_queue_sitemap(template_url: str, sitemap_url: str) -> bool:
        if not _same_domain(template_url, sitemap_url):
            return False
        path = urlparse(sitemap_url).path.lower()
        if "/storage/" in path and "recipe" not in path:
            if any(keyword in path for keyword in STORAGE_SITEMAP_EXCLUDE_KEYWORDS):
                return False
        return True

    @staticmethod
    def _should_include_url(
        template_url: str, listing_url: str, candidate_url: str
    ) -> bool:
        parsed = urlparse(candidate_url)
        if parsed.fragment:
            fragment = parsed.fragment
            if _is_navigation_fragment(fragment):
                return False
            lowered_fragment = fragment.lower()
            if lowered_fragment.startswith("/"):
                return False
            if any(keyword in lowered_fragment for keyword in ("schema", "image", "logo")):
                return False

        candidate_base = _normalise_base_url(candidate_url)
        if not candidate_base:
            return False

        listing_base = _normalise_base_url(listing_url)
        template_base = _normalise_base_url(template_url)

        if not parsed.fragment and candidate_base in {listing_base, template_base}:
            return False

        if _looks_like_asset_url(candidate_url):
            return False

        return True

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

    def scrape(self, template: RecipeTemplate, url: str) -> List[Recipe]:
        response = self._http.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        content_soup = self._derive_content_soup(soup, url)

        structured_recipes = self._extract_structured_data(template.structured_data, soup)
        sections = _extract_recipe_sections(content_soup)

        recipe_count = max(len(structured_recipes), len(sections), 1)
        multi_mode = recipe_count > 1

        base_response_url = response.url
        base_url = _normalise_base_url(base_response_url)

        recipes: List[Recipe] = []
        used_anchors: Set[str] = set()

        for index in range(recipe_count):
            section = sections[index] if index < len(sections) else None
            recipe = Recipe(
                source_name=template.name,
                source_url=base_response_url,
            )

            if index < len(structured_recipes):
                self._populate_from_structured(recipe, structured_recipes[index])

            skip_fields: Optional[Set[str]] = None
            if multi_mode:
                skip_fields = {"ingredients", "instructions"}

            self._populate_from_selectors(
                recipe,
                soup,
                content_soup,
                template.article,
                skip_fields=skip_fields,
            )

            if section:
                self._populate_from_section(
                    recipe,
                    section,
                    base_response_url,
                    prefer_section=multi_mode,
                )
            self._apply_generic_fallbacks(recipe, soup, base_response_url)

            if multi_mode:
                anchor = _resolve_section_anchor(section, index, recipe.title, used_anchors)
                recipe.source_url = f"{base_url}#{anchor}" if base_url else f"{base_response_url}#{anchor}"

            try:
                self._validate_recipe(recipe, recipe.source_url)
            except ArticleExtractionError:
                if multi_mode:
                    continue
                raise

            recipes.append(recipe)

        if not recipes:
            raise ArticleExtractionError(
                "Missing ingredients and instructions while scraping %s" % url
            )

        return recipes

    def _derive_content_soup(self, soup: BeautifulSoup, url: str) -> BeautifulSoup:
        parsed = urlparse(url)
        fragment = parsed.fragment
        if not fragment:
            return soup

        target = soup.find(id=fragment) or soup.find(attrs={"name": fragment})
        if not isinstance(target, Tag):
            return soup

        def is_navigation(tag: Tag) -> bool:
            classes = " ".join(tag.get("class", [])).lower()
            return any(
                keyword in classes
                for keyword in (
                    "breadcrumb",
                    "nav",
                    "menu",
                    "header",
                    "footer",
                    "pagination",
                )
            )

        container = target
        best_match: Optional[Tag] = None
        while isinstance(container, Tag) and container.parent is not None:
            if container.name in {"article", "section"}:
                best_match = container
                break
            if container.name == "div":
                classes = " ".join(container.get("class", [])).lower()
                if any(keyword in classes for keyword in ("recipe", "post", "entry")) and not is_navigation(container):
                    best_match = container
                    break
            if container.parent.name in {"body", "html"}:
                break
            container = container.parent

        if not best_match:
            container = target
            while isinstance(container, Tag):
                if container.name in {"article", "section"} and not is_navigation(container):
                    best_match = container
                    break
                if container.parent is None or container.parent.name in {"body", "html"}:
                    break
                container = container.parent

        if not best_match:
            container = target
            while isinstance(container, Tag):
                if not is_navigation(container):
                    best_match = container
                    break
                parent = container.parent
                if not isinstance(parent, Tag):
                    break
                if parent.name in {"body", "html"} and is_navigation(parent):
                    break
                container = parent

        if isinstance(best_match, Tag):
            return BeautifulSoup(str(best_match), "html.parser")

        return soup

    def _extract_structured_data(
        self, config: StructuredDataConfig, soup: BeautifulSoup
    ) -> List[dict]:
        if not config.enabled or not config.json_ld_selector:
            return []

        recipes: List[dict] = []
        for script in soup.select(config.json_ld_selector):
            payload = script.string or script.get_text()
            for candidate in _safe_json_loads(payload):
                for recipe in _walk_recipe_nodes(candidate):
                    recipes.append(recipe)
        return recipes

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

    def _populate_from_section(
        self,
        recipe: Recipe,
        section: RecipeSection,
        base_url: str,
        prefer_section: bool = False,
    ) -> None:
        if section.title and (prefer_section or not recipe.title):
            recipe.title = section.title

        if section.ingredients and not recipe.ingredients:
            recipe.ingredients = _dedupe_preserve_order(section.ingredients)

        if section.instructions and not recipe.instructions:
            recipe.instructions = _dedupe_preserve_order(section.instructions)

        if prefer_section or not recipe.image:
            section_image = _resolve_section_image(section, base_url)
            if section_image:
                recipe.image = section_image

    def _populate_from_selectors(
        self,
        recipe: Recipe,
        full_soup: BeautifulSoup,
        content_soup: BeautifulSoup,
        selectors: ArticleConfig,
        skip_fields: Optional[Set[str]] = None,
    ) -> None:
        soups_to_try = [content_soup]
        if content_soup is not full_soup:
            soups_to_try.append(full_soup)

        for field in selectors.iter_fields():
            if skip_fields and field in skip_fields:
                continue

            selector_list = selectors.selectors_for(field)
            if not selector_list:
                continue

            if not hasattr(recipe, field):
                continue

            current_value = getattr(recipe, field)
            if current_value:
                continue

            for soup in soups_to_try:
                if field == "image":
                    value = self._extract_field(
                        selector_list, soup, image=True, field_name=field
                    )
                else:
                    value = self._extract_field(
                        selector_list,
                        soup,
                        multiple=_detect_list_field(field),
                        field_name=field,
                    )

                if value is None:
                    continue

                if isinstance(value, list):
                    if not value:
                        continue
                    setattr(recipe, field, value)
                    break

                if value:
                    setattr(recipe, field, value)
                    break

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

    def _validate_recipe(self, recipe: Recipe, url: str) -> None:
        if recipe.ingredients or recipe.instructions:
            return

        raise ArticleExtractionError(
            "Missing ingredients and instructions while scraping %s" % url
        )
