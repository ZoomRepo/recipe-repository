"""Utilities for loading environment variables for CLI scripts."""
from __future__ import annotations

from pathlib import Path


def load_dotenv_if_available(path: str | Path | None = None, *, override: bool = False) -> bool:
    """Load variables from a ``.env`` file when python-dotenv is installed."""

    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency guard
        return False

    dotenv_path: str | Path | None = path
    if dotenv_path is None:
        project_root = Path(__file__).resolve().parents[2]
        dotenv_path = project_root / ".env"

    return load_dotenv(dotenv_path=dotenv_path, override=override)
