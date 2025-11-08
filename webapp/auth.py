"""Authentication helpers for the temporary email login gate."""
from __future__ import annotations

import re
import secrets
import time
from datetime import timedelta
from typing import Callable, Protocol

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .config import AppConfig, LoginGateConfig
from .services import EmailService


class WhitelistChecker(Protocol):
    """Minimal interface for querying whether an email can receive a code."""

    def is_allowed(self, email: str) -> bool:
        """Return ``True`` when *email* is authorized for login."""
        raise NotImplementedError

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SESSION_AUTH_KEY = "login_authenticated"
SESSION_EMAIL_KEY = "login_email"
SESSION_CODE_KEY = "login_code"
SESSION_TIMESTAMP_KEY = "login_code_timestamp"
SESSION_NEXT_KEY = "login_next"


def register_login_routes(
    app,
    login_config: LoginGateConfig,
    email_service: EmailService,
    whitelist: WhitelistChecker,
    code_generator: Callable[[], str] | None = None,
) -> None:
    """Register login routes and guards on *app*."""

    blueprint = Blueprint("auth", __name__, url_prefix="/auth")
    generate_code = code_generator or _generate_code

    @blueprint.route("/login", methods=["GET", "POST"])
    def login() -> str:
        if not login_config.enabled:
            abort(404)

        if session.get(SESSION_AUTH_KEY):
            destination = session.pop(SESSION_NEXT_KEY, None) or url_for("recipes.index")
            return redirect(destination)

        next_url = request.args.get("next") or request.form.get("next")
        if next_url:
            session[SESSION_NEXT_KEY] = next_url

        email_value = session.get(SESSION_EMAIL_KEY, "")
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            if not _is_valid_email(email):
                flash("Enter a valid email address to receive your code.", "error")
            else:
                code = generate_code()
                normalized_email = email.lower()
                if not whitelist.is_allowed(normalized_email):
                    flash(
                        "That email address isn't authorized to access the site.",
                        "error",
                    )
                else:
                    session[SESSION_EMAIL_KEY] = normalized_email
                    session[SESSION_CODE_KEY] = code
                    session[SESSION_TIMESTAMP_KEY] = time.time()
                    try:
                        email_service.send_login_code(normalized_email, code)
                        flash("We sent a 6-digit access code to your email.", "success")
                    except Exception:  # pragma: no cover - best effort logging
                        current_app.logger.exception("Failed to send login code")
                        flash(
                            "We couldn't send the access code right now. Please try again.",
                            "error",
                        )
        email_value = session.get(SESSION_EMAIL_KEY, email_value)
        code_sent = SESSION_CODE_KEY in session
        return render_template(
            "auth/login.html",
            email=email_value,
            code_sent=code_sent,
        )

    @blueprint.route("/verify", methods=["POST"])
    def verify() -> str:
        if not login_config.enabled:
            abort(404)

        code = request.form.get("code", "").strip()
        stored_code = session.get(SESSION_CODE_KEY)
        issued_at = session.get(SESSION_TIMESTAMP_KEY)
        if not stored_code or issued_at is None:
            flash("Request a code before trying to verify.", "error")
            return redirect(url_for("auth.login"))

        if not code or code != stored_code:
            flash("That code is incorrect. Please try again.", "error")
            return redirect(url_for("auth.login"))

        expires_after = login_config.code_ttl_minutes * 60
        if time.time() - issued_at > expires_after:
            flash("Your code has expired. Request a new one to continue.", "error")
            session.pop(SESSION_CODE_KEY, None)
            session.pop(SESSION_TIMESTAMP_KEY, None)
            return redirect(url_for("auth.login"))

        session.pop(SESSION_CODE_KEY, None)
        session.pop(SESSION_TIMESTAMP_KEY, None)
        session.permanent = True
        app.permanent_session_lifetime = timedelta(
            minutes=login_config.session_lifetime_minutes
        )
        session[SESSION_AUTH_KEY] = True
        flash("You're now signed in.", "success")
        destination = session.pop(SESSION_NEXT_KEY, None) or url_for("recipes.index")
        return redirect(destination)

    app.register_blueprint(blueprint)

    @app.before_request
    def _require_login():
        if not login_config.enabled:
            return None

        if session.get(SESSION_AUTH_KEY):
            return None

        endpoint = request.endpoint or ""
        if endpoint.startswith("auth.") or endpoint.startswith("static"):
            return None

        if request.blueprint == "auth":
            return None

        config: AppConfig | None = current_app.config.get("APP_CONFIG")
        if config and not config.login_gate.enabled:
            return None

        session[SESSION_NEXT_KEY] = request.url
        return redirect(url_for("auth.login"))


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _is_valid_email(value: str) -> bool:
    return bool(value and EMAIL_RE.match(value))
