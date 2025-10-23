"""HTTP client with retry logic tailored for scraping."""
from __future__ import annotations

from typing import Any, Dict, Optional

import requests
from requests import Response
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class HttpClient:
    """Wrapper around :mod:`requests` providing retry-aware GET calls."""

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        if headers:
            self._session.headers.update(headers)

        retry_strategy = Retry(
            total=max_retries,
            read=max_retries,
            connect=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def get(self, url: str, **kwargs: Any) -> Response:
        """Perform an HTTP GET request."""

        timeout = kwargs.pop("timeout", self._timeout)
        response = self._session.get(url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
