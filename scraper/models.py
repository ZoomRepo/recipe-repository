"""Domain models used by the recipe scraper."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ListingConfig:
    """Describes how to discover recipe article URLs."""

    url: str
    link_selector: str
    pagination_selector: Optional[str] = None


@dataclass(frozen=True)
class ArticleConfig:
    """CSS selectors used to extract recipe details from an article page."""

    selectors: Dict[str, List[str]] = field(default_factory=dict)

    def iter_fields(self) -> Iterable[str]:
        return self.selectors.keys()

    def selectors_for(self, field: str) -> List[str]:
        return self.selectors.get(field, [])


@dataclass(frozen=True)
class StructuredDataConfig:
    """Configuration describing how to extract JSON-LD recipes."""

    enabled: bool = False
    json_ld_selector: Optional[str] = None
    json_ld_path: Optional[str] = None


@dataclass(frozen=True)
class RecipeTemplate:
    """Complete scraping template for a recipe website."""

    name: str
    url: str
    type: str
    listings: List[ListingConfig] = field(default_factory=list)
    article: ArticleConfig = field(default_factory=ArticleConfig)
    structured_data: StructuredDataConfig = field(default_factory=StructuredDataConfig)


@dataclass(frozen=True)
class ScrapeFailure:
    """Represents a failed scraping attempt that can be retried later."""

    template_name: str
    stage: str
    source_url: Optional[str] = None
    error_message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def normalised_source_url(self) -> str:
        return self.source_url or ""


@dataclass(frozen=True)
class PendingFailure(ScrapeFailure):
    """A stored failure fetched from persistence for replay."""

    id: int = 0
    attempt_count: int = 0


@dataclass
class Recipe:
    """Normalized recipe entity ready for persistence."""

    source_name: str
    source_url: str
    title: Optional[str] = None
    description: Optional[str] = None
    ingredients: List[str] = field(default_factory=list)
    instructions: List[str] = field(default_factory=list)
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    raw: Dict[str, object] = field(default_factory=dict)

    def as_record(self) -> Dict[str, object]:
        """Convert the recipe into a serializable dict for persistence."""

        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title,
            "description": self.description,
            "ingredients": self.ingredients,
            "instructions": self.instructions,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "total_time": self.total_time,
            "servings": self.servings,
            "image": self.image,
            "author": self.author,
            "categories": self.categories,
            "tags": self.tags,
            "raw": self.raw,
        }

    @classmethod
    def from_record(cls, payload: Dict[str, Any]) -> "Recipe":
        """Recreate a recipe entity from a persisted representation."""

        return cls(
            source_name=str(payload.get("source_name", "")),
            source_url=str(payload.get("source_url", "")),
            title=payload.get("title"),
            description=payload.get("description"),
            ingredients=list(payload.get("ingredients", []) or []),
            instructions=list(payload.get("instructions", []) or []),
            prep_time=payload.get("prep_time"),
            cook_time=payload.get("cook_time"),
            total_time=payload.get("total_time"),
            servings=payload.get("servings"),
            image=payload.get("image"),
            author=payload.get("author"),
            categories=list(payload.get("categories", []) or []),
            tags=list(payload.get("tags", []) or []),
            raw=dict(payload.get("raw", {}) or {}),
        )
