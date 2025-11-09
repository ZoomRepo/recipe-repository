"""Identify recipes whose primary image likely does not depict food.

This script reads normalised recipe records (the same structure produced by
``Recipe.as_record``) from a JSON file, downloads their associated images, and
classifies them using a pre-trained ImageNet model. Recipes whose images are not
recognised as food are reported in the output along with the predicted
ImageNet label and probability.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps, UnidentifiedImageError
from tqdm import tqdm

from scraper.http_client import HttpClient

logger = logging.getLogger(__name__)

ASSETS_DIR = (Path(__file__).resolve().parent.parent / "assets").resolve()
DEFAULT_MODEL_PATH = ASSETS_DIR / "squeezenet1.1-7.onnx"
DEFAULT_LABELS_PATH = ASSETS_DIR / "imagenet_labels.json"

# Normalised list of food-related labels derived from the Food101 dataset plus
# a handful of generic fallbacks that frequently appear in ImageNet. The values
# are all stored in lowercase without punctuation to simplify comparisons.
FOOD_KEYWORDS: Sequence[str] = sorted(
    {
        "apple pie",
        "baby back ribs",
        "baklava",
        "beef carpaccio",
        "beef tartare",
        "beet salad",
        "beignets",
        "bibimbap",
        "bread pudding",
        "breakfast burrito",
        "bruschetta",
        "caesar salad",
        "cannoli",
        "caprese salad",
        "carrot cake",
        "ceviche",
        "cheesecake",
        "cheese plate",
        "chicken curry",
        "chicken quesadilla",
        "chicken wings",
        "chocolate cake",
        "chocolate mousse",
        "churros",
        "clam chowder",
        "club sandwich",
        "crab cakes",
        "creme brulee",
        "croque madame",
        "cup cakes",
        "deviled eggs",
        "donuts",
        "dumplings",
        "edamame",
        "eggs benedict",
        "escargots",
        "falafel",
        "filet mignon",
        "fish and chips",
        "foie gras",
        "french fries",
        "french onion soup",
        "french toast",
        "fried calamari",
        "fried rice",
        "frozen yogurt",
        "garlic bread",
        "gnocchi",
        "greek salad",
        "grilled cheese sandwich",
        "grilled salmon",
        "guacamole",
        "gyoza",
        "hamburger",
        "hot and sour soup",
        "hot dog",
        "huevos rancheros",
        "hummus",
        "ice cream",
        "lasagna",
        "lobster bisque",
        "lobster roll sandwich",
        "macaroni and cheese",
        "macarons",
        "miso soup",
        "mussels",
        "nachos",
        "omelette",
        "onion rings",
        "oysters",
        "pad thai",
        "paella",
        "pancakes",
        "panna cotta",
        "peking duck",
        "pho",
        "pizza",
        "pork chop",
        "poutine",
        "prime rib",
        "pulled pork sandwich",
        "ramen",
        "ravioli",
        "red velvet cake",
        "risotto",
        "samosa",
        "sashimi",
        "scallops",
        "seaweed salad",
        "shrimp and grits",
        "spaghetti bolognese",
        "spaghetti carbonara",
        "spring rolls",
        "steak",
        "strawberry shortcake",
        "sushi",
        "tacos",
        "takoyaki",
        "tiramisu",
        "tuna tartare",
        "waffles",
        # Generic catch-alls for common ImageNet food classes
        "barbecue",
        "bbq",
        "beer",
        "biscuit",
        "bread",
        "burger",
        "cake",
        "candy",
        "casserole",
        "cheese",
        "chili",
        "chocolate",
        "coffee",
        "cookie",
        "dessert",
        "drink",
        "fish",
        "food",
        "fruit",
        "grill",
        "kebab",
        "meat",
        "noodle",
        "pasta",
        "pie",
        "pizza pie",
        "pork",
        "poultry",
        "rice",
        "salad",
        "sandwich",
        "seafood",
        "soup",
        "steakhouse",
        "stew",
        "sundae",
        "sushi bar",
        "sweet",
        "tea",
        "toast",
        "yogurt",
    }
)


@dataclass
class FlaggedRecipe:
    """Represents a recipe whose image was classified as non-food."""

    source_name: Optional[str]
    source_url: Optional[str]
    title: Optional[str]
    image_url: str
    predicted_label: str
    confidence: float
    predictions: List[Dict[str, float]]

    def as_dict(self) -> Dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "title": self.title,
            "image_url": self.image_url,
            "predicted_label": self.predicted_label,
            "confidence": self.confidence,
            "predictions": self.predictions,
        }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect recipes whose images do not appear to be food.",
    )
    parser.add_argument(
        "recipes",
        type=Path,
        help="Path to a JSON file containing a list of recipe records.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the flagged recipes as JSON.",
    )
    parser.add_argument(
        "--topk",
        type=int,
        default=3,
        help="Number of top predictions to inspect for food classes (default: 3).",
    )
    parser.add_argument(
        "--food-threshold",
        type=float,
        default=0.20,
        help="Minimum probability for a prediction to be considered food (default: 0.20).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most this many recipes (useful for smoke testing).",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="Override the default ONNX model path.",
    )
    parser.add_argument(
        "--labels-path",
        type=Path,
        default=DEFAULT_LABELS_PATH,
        help="Override the default ImageNet labels path.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Adjust the verbosity of log output.",
    )
    return parser.parse_args(argv)


def load_recipe_records(path: Path) -> List[Dict[str, object]]:
    """Load recipe records from *path*.

    The file must contain either a list of recipe dicts or an object with a
    top-level ``"recipes"`` key containing that list.
    """

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"Failed to parse JSON from {path}: {exc}") from exc

    if isinstance(raw, dict):
        if "recipes" in raw and isinstance(raw["recipes"], list):
            raw = raw["recipes"]
        else:
            raise ValueError(
                "Expected a list of recipes or an object with a 'recipes' key",
            )

    if not isinstance(raw, list):
        raise ValueError("Recipe file must contain a JSON array of recipes")

    recipes: List[Dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Recipe at index {index} is not a JSON object")
        recipes.append(item)
    return recipes


def normalise_label(label: str) -> str:
    return " ".join(label.lower().replace("_", " ").split())


def label_is_food(label: str, keywords: Sequence[str] = FOOD_KEYWORDS) -> bool:
    """Return ``True`` if *label* appears to represent food."""

    normalised = normalise_label(label)
    return any(keyword in normalised for keyword in keywords)


def load_labels(path: Path = DEFAULT_LABELS_PATH) -> List[str]:
    """Load ImageNet labels from *path*."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        labels: List[str] = []
        for index in range(len(data)):
            entry = data.get(str(index))
            if entry is None:
                raise ValueError(f"Missing label for index {index}")
            if isinstance(entry, list):
                labels.append(str(entry[1]))
            else:
                labels.append(str(entry))
        return labels
    if isinstance(data, list):
        return [str(item) for item in data]
    raise ValueError("Unsupported label file structure")


def preprocess_image(image: Image.Image) -> np.ndarray:
    """Prepare an image for SqueezeNet inference."""

    image = ImageOps.exif_transpose(image)
    resized = image.resize((224, 224))
    array = np.asarray(resized, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    normalized = (array - mean) / std
    chw = np.transpose(normalized, (2, 0, 1))
    return np.expand_dims(chw, axis=0)


def softmax(logits: np.ndarray) -> np.ndarray:
    """Compute softmax values for the given logits array."""

    max_per_row = np.max(logits, axis=1, keepdims=True)
    exp = np.exp(logits - max_per_row)
    return exp / np.sum(exp, axis=1, keepdims=True)


class ImageClassifier:
    """ONNX Runtime based image classifier for ImageNet."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        labels_path: Path = DEFAULT_LABELS_PATH,
    ) -> None:
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {model_path}. Ensure the ONNX model is available."
            )
        if not labels_path.exists():
            raise FileNotFoundError(f"Label file not found at {labels_path}.")
        self._session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        self._labels = load_labels(labels_path)

    @property
    def labels(self) -> Sequence[str]:
        return self._labels

    def classify(self, image: Image.Image, topk: int) -> List[tuple[int, float]]:
        inputs = {self._input_name: preprocess_image(image)}
        logits = self._session.run(None, inputs)[0]
        probabilities = softmax(logits)
        topk = max(1, min(topk, probabilities.shape[1]))
        top_indices = np.argsort(probabilities[0])[-topk:][::-1]
        return [
            (int(index), float(probabilities[0][index]))
            for index in top_indices
        ]


def download_image(client: HttpClient, url: str) -> Image.Image:
    """Fetch *url* and return it as a PIL image."""

    response = client.get(url, timeout=20)
    try:
        image = Image.open(BytesIO(response.content))
        return image.convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError(f"Failed to decode image from {url}") from exc


def inspect_recipes(
    recipes: Sequence[Dict[str, object]],
    classifier: ImageClassifier,
    client: HttpClient,
    *,
    topk: int,
    threshold: float,
) -> List[FlaggedRecipe]:
    """Evaluate recipes and return those with non-food images."""

    flagged: List[FlaggedRecipe] = []
    progress = tqdm(recipes, desc="Evaluating images")
    for recipe in progress:
        image_url = recipe.get("image")
        if not isinstance(image_url, str) or not image_url.strip():
            progress.set_postfix_str("no image")
            continue
        try:
            image = download_image(client, image_url)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to download %s: %s", image_url, exc)
            progress.set_postfix_str("download failed")
            continue

        try:
            predictions = classifier.classify(image, topk)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Failed to classify %s: %s", image_url, exc)
            progress.set_postfix_str("classification failed")
            continue

        top_predictions = [
            {
                "label": classifier.labels[index],
                "confidence": probability,
            }
            for index, probability in predictions
        ]

        has_food = any(
            probability >= threshold and label_is_food(classifier.labels[index])
            for index, probability in predictions
        )
        if has_food:
            progress.set_postfix_str("looks like food")
            continue

        flagged.append(
            FlaggedRecipe(
                source_name=str(recipe.get("source_name"))
                if recipe.get("source_name")
                else None,
                source_url=str(recipe.get("source_url"))
                if recipe.get("source_url")
                else None,
                title=str(recipe.get("title")) if recipe.get("title") else None,
                image_url=image_url,
                predicted_label=top_predictions[0]["label"],
                confidence=top_predictions[0]["confidence"],
                predictions=top_predictions,
            )
        )
        progress.set_postfix_str("flagged")

    progress.close()
    return flagged


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))

    recipes = load_recipe_records(args.recipes)
    if args.limit is not None:
        recipes = recipes[: max(args.limit, 0)]

    classifier = ImageClassifier(
        model_path=args.model_path,
        labels_path=args.labels_path,
    )

    with HttpClient(headers={"Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}) as client:
        flagged = inspect_recipes(
            recipes,
            classifier,
            client,
            topk=args.topk,
            threshold=args.food_threshold,
        )

    if args.output:
        args.output.write_text(
            json.dumps([entry.as_dict() for entry in flagged], indent=2),
            encoding="utf-8",
        )
        logger.info("Wrote %d flagged recipes to %s", len(flagged), args.output)

    if flagged:
        print("Non-food images detected:")
        for entry in flagged:
            confidence = f"{entry.confidence:.1%}"
            title = entry.title or entry.source_url or entry.image_url
            print(
                f"- {title} -> {entry.predicted_label} ({confidence}) [{entry.image_url}]"
            )
    else:
        print("No non-food images detected.")

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
