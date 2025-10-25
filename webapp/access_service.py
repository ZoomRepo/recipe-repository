"""Service layer for the access-gating flow."""
from __future__ import annotations

import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .access_repository import AccessRepository
from .config import AccessConfig
from .email import EmailSender

LOGGER = logging.getLogger(__name__)


class RequestCodeStatus(Enum):
    SENT = "sent"
    NOT_FOUND = "not_found"
    ALREADY_VERIFIED = "already_verified"
    INVALID_EMAIL = "invalid_email"
    FAILED = "failed"


@dataclass(frozen=True)
class RequestCodeResult:
    status: RequestCodeStatus
    email: Optional[str] = None
    device_id: Optional[str] = None


class VerifyCodeStatus(Enum):
    VERIFIED = "verified"
    INVALID = "invalid"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    ALREADY_VERIFIED = "already_verified"
    FAILED = "failed"


@dataclass(frozen=True)
class VerifyCodeResult:
    status: VerifyCodeStatus
    device_id: Optional[str] = None


class AccessService:
    """Coordinates subscription and invite verification flows."""

    CODE_LENGTH = 6

    def __init__(
        self,
        repository: AccessRepository,
        email_sender: EmailSender,
        config: AccessConfig,
        logger: logging.Logger | None = None,
    ) -> None:
        self._repository = repository
        self._email_sender = email_sender
        self._config = config
        self._logger = logger or LOGGER

    @property
    def cookie_name(self) -> str:
        return self._config.cookie_name

    def subscribe(self, email: str) -> None:
        normalized = (email or "").strip().lower()
        if not normalized:
            raise ValueError("Email address is required")
        self._repository.add_subscriber(normalized)

    def request_access_code(self, email: str) -> RequestCodeResult:
        normalized = self._normalize_email(email)
        if not normalized:
            return RequestCodeResult(RequestCodeStatus.INVALID_EMAIL)

        invited = self._repository.get_invited_user_by_email(normalized)
        if not invited:
            return RequestCodeResult(RequestCodeStatus.NOT_FOUND)
        if invited.get("device_id"):
            return RequestCodeResult(
                RequestCodeStatus.ALREADY_VERIFIED,
                invited["email"],
                invited.get("device_id"),
            )

        code = self._generate_code()
        try:
            self._repository.save_access_code(invited["id"], code)
            subject = "Your Recipe Library verification code"
            body = (
                "Your Recipe Library verification code is "
                f"{code}. It will expire in {self._config.code_ttl_minutes} minutes."
            )
            self._email_sender.send_email(invited["email"], subject, body)
        except Exception:  # pragma: no cover - defensive logging
            self._logger.exception("Unable to send verification code")
            return RequestCodeResult(RequestCodeStatus.FAILED)

        return RequestCodeResult(RequestCodeStatus.SENT, invited["email"])

    def verify_access_code(self, email: str, code: str, device_id: str) -> VerifyCodeResult:
        normalized = self._normalize_email(email)
        if not normalized:
            return VerifyCodeResult(VerifyCodeStatus.NOT_FOUND)

        invited = self._repository.get_invited_user_by_email(normalized)
        if not invited:
            return VerifyCodeResult(VerifyCodeStatus.NOT_FOUND)
        if invited.get("device_id") and invited.get("device_id") != device_id:
            return VerifyCodeResult(VerifyCodeStatus.ALREADY_VERIFIED, invited.get("device_id"))

        stored_code = (invited.get("access_code") or "").strip()
        if not stored_code:
            return VerifyCodeResult(VerifyCodeStatus.INVALID)
        if stored_code != (code or "").strip():
            return VerifyCodeResult(VerifyCodeStatus.INVALID)

        generated_at = invited.get("code_generated_at")
        if isinstance(generated_at, datetime):
            now = datetime.utcnow()
            if generated_at.tzinfo is not None:
                now = datetime.now(tz=generated_at.tzinfo)
            expiry = generated_at + timedelta(minutes=self._config.code_ttl_minutes)
            if now > expiry:
                return VerifyCodeResult(VerifyCodeStatus.EXPIRED)

        try:
            self._repository.save_device_id(invited["id"], device_id)
            self._repository.clear_access_code(invited["id"])
        except Exception:  # pragma: no cover - defensive logging
            self._logger.exception("Unable to persist invite verification")
            return VerifyCodeResult(VerifyCodeStatus.FAILED)

        return VerifyCodeResult(VerifyCodeStatus.VERIFIED, device_id)

    def is_device_authorized(self, device_id: Optional[str]) -> bool:
        if not device_id:
            return False
        invited = self._repository.get_invited_user_by_device(device_id)
        return bool(invited)

    def generate_device_id(self) -> str:
        return secrets.token_hex(16)

    def _normalize_email(self, email: str) -> str:
        candidate = (email or "").strip().lower()
        if "@" not in candidate or "." not in candidate.split("@", 1)[-1]:
            return ""
        return candidate

    def _generate_code(self) -> str:
        choices = string.digits
        return "".join(secrets.choice(choices) for _ in range(self.CODE_LENGTH))
