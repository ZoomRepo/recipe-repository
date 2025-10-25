"""SMS sending utilities."""
from __future__ import annotations

import logging
from typing import Protocol

from .config import SmsConfig


class SmsGateway(Protocol):
    """Protocol describing an SMS sender."""

    def send_text(self, to_number: str, body: str) -> None:
        ...


class ConsoleSmsGateway:
    """Fallback gateway that logs SMS messages for development."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def send_text(self, to_number: str, body: str) -> None:
        self._logger.info("SMS to %s: %s", to_number, body)


class TwilioSmsGateway:
    """Twilio based SMS gateway."""

    def __init__(self, config: SmsConfig) -> None:
        from twilio.rest import Client  # lazy import to avoid dependency unless needed

        self._client = Client(config.account_sid, config.auth_token)
        self._from_number = config.from_number

    def send_text(self, to_number: str, body: str) -> None:
        self._client.messages.create(to=to_number, from_=self._from_number, body=body)


def create_sms_gateway(config: SmsConfig, logger: logging.Logger | None = None) -> SmsGateway:
    """Return an SMS gateway instance based on *config*."""

    if config.account_sid and config.auth_token and config.from_number:
        return TwilioSmsGateway(config)
    return ConsoleSmsGateway(logger)
