"""Tests for the whitelist management interface."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from webapp.whitelist import WhitelistEntry, register_whitelist_routes


class StubWhitelistRepository:
    def __init__(self) -> None:
        self.entries: dict[str, WhitelistEntry] = {}

    def list_entries(self) -> list[WhitelistEntry]:
        return [self.entries[key] for key in sorted(self.entries)]

    def add_email(self, email: str) -> bool:
        normalized = email.lower()
        if normalized in self.entries:
            return False
        self.entries[normalized] = WhitelistEntry(email=normalized, added_at=None)
        return True

    def remove_email(self, email: str) -> bool:
        normalized = email.lower()
        return self.entries.pop(normalized, None) is not None

    def is_allowed(self, email: str) -> bool:
        return email.lower() in self.entries


BASE_DIR = Path(__file__).resolve().parents[1]


def build_app() -> tuple[Flask, StubWhitelistRepository]:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "webapp" / "templates"),
        static_folder=str(BASE_DIR / "webapp" / "static"),
    )
    app.secret_key = "testing"
    repository = StubWhitelistRepository()
    register_whitelist_routes(app, repository)
    app.add_url_rule(
        "/",
        endpoint="recipes.index",
        view_func=lambda: "",
    )
    return app, repository


def test_lists_existing_entries():
    app, repository = build_app()
    repository.add_email("allowed@example.com")

    client = app.test_client()
    response = client.get("/whitelist/")

    assert response.status_code == 200
    assert b"allowed@example.com" in response.data


def test_can_add_new_email():
    app, repository = build_app()
    client = app.test_client()

    response = client.post(
        "/whitelist/",
        data={"email": "new@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert repository.is_allowed("new@example.com")
    assert b"Added new@example.com" in response.data


def test_rejects_duplicate_email_addition():
    app, repository = build_app()
    repository.add_email("dupe@example.com")
    client = app.test_client()

    response = client.post(
        "/whitelist/",
        data={"email": "dupe@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already on the whitelist" in response.data


def test_can_remove_email():
    app, repository = build_app()
    repository.add_email("remove@example.com")
    client = app.test_client()

    response = client.post(
        "/whitelist/remove",
        data={"email": "remove@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert not repository.is_allowed("remove@example.com")
    assert b"Removed remove@example.com" in response.data
