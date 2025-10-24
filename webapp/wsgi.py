"""WSGI entrypoint for running the recipe web application in production."""
from __future__ import annotations

from . import create_app
from .config import AppConfig


# Instantiate the application at module import so production WSGI servers can
# discover it without executing any additional code.
app = create_app(AppConfig.from_env())


def get_app():
    """Return the configured Flask application.

    Exposed for WSGI servers that expect a callable returning the app instead
    of a module-level variable.
    """

    return app

