"""Tests for the email-based temporary login gate."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from webapp.auth import (
    SESSION_AUTH_KEY,
    SESSION_CODE_KEY,
    SESSION_EMAIL_KEY,
    register_login_routes,
)
from webapp.config import AppConfig, DatabaseConfig, LoginGateConfig, MailConfig


class StubEmailService:
    def __init__(self) -> None:
        self.last_message: tuple[str, str] | None = None

    def send_login_code(self, recipient: str, code: str) -> None:
        self.last_message = (recipient, code)


class StubWhitelist:
    def __init__(self, allowed: set[str] | None = None) -> None:
        self.allowed = {item.lower() for item in allowed or set()}

    def is_allowed(self, email: str) -> bool:
        return email.lower() in self.allowed


BASE_DIR = Path(__file__).resolve().parents[1]


def build_app(
    login_enabled: bool = True,
    whitelisted: set[str] | None = None,
) -> tuple[Flask, StubEmailService, StubWhitelist]:
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "webapp" / "templates"),
        static_folder=str(BASE_DIR / "webapp" / "static"),
    )
    app.secret_key = "testing-secret"
    login_config = LoginGateConfig(
        enabled=login_enabled,
        code_ttl_minutes=10,
        session_lifetime_minutes=60,
    )
    email_service = StubEmailService()
    whitelist = StubWhitelist(whitelisted or {"user@example.com"})
    register_login_routes(
        app,
        login_config,
        email_service,
        whitelist,
        code_generator=lambda: "123456",
    )
    app.add_url_rule(
        "/whitelist/",
        endpoint="whitelist.index",
        view_func=lambda: "",
    )
    app.config["APP_CONFIG"] = AppConfig(
        database=DatabaseConfig(),
        page_size=20,
        secret_key="testing-secret",
        login_gate=login_config,
        mail=MailConfig(),
    )

    @app.route("/", endpoint="recipes.index")
    def protected() -> str:
        return "ok"

    return app, email_service, whitelist


def test_requires_login_when_gate_enabled():
    app, _, _ = build_app(login_enabled=True)

    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_email_login_flow_grants_access():
    app, email_service, _ = build_app(login_enabled=True)
    client = app.test_client()

    # Trigger the login gate to capture the target URL.
    response = client.get("/")
    assert response.status_code == 302

    # Request a login code.
    response = client.post(
        "/auth/login",
        data={"email": "user@example.com"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert email_service.last_message == ("user@example.com", "123456")

    with client.session_transaction() as session:
        assert session[SESSION_EMAIL_KEY] == "user@example.com"
        assert session[SESSION_CODE_KEY] == "123456"

    # Submit the verification code and confirm access.
    response = client.post("/auth/verify", data={"code": "123456"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    response = client.get("/")
    assert response.status_code == 200
    assert response.data == b"ok"

    with client.session_transaction() as session:
        assert session.get(SESSION_AUTH_KEY) is True


def test_gate_can_be_disabled():
    app, _, _ = build_app(login_enabled=False)
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200
    assert response.data == b"ok"


def test_email_must_be_whitelisted_before_code_sent():
    app, email_service, _ = build_app(
        login_enabled=True,
        whitelisted={"allowed@example.com"},
    )
    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={"email": "unknown@example.com"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert email_service.last_message is None
    assert b"isn&#39;t authorized" in response.data
