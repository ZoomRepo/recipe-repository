"""Entry point for running the recipe web application."""
from __future__ import annotations

import os

from . import create_app
from .config import AppConfig


def main() -> None:
    config = AppConfig.from_env()
    app = create_app(config)
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
