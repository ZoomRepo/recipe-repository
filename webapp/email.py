"""Email sending utilities for the invite workflow."""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


class EmailSender(Protocol):
    """Protocol describing an email sender."""

    def send_email(self, to_address: str, subject: str, body: str) -> None:
        ...


class ConsoleEmailSender:
    """Development sender that logs messages instead of emailing."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(__name__)

    def send_email(self, to_address: str, subject: str, body: str) -> None:
        self._logger.info("Email to %s | %s\n%s", to_address, subject, body)


@dataclass
class SmtpSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool
    from_address: str


class SmtpEmailSender:
    """Email sender backed by :mod:`smtplib`."""

    def __init__(self, settings: SmtpSettings) -> None:
        self._settings = settings

    def send_email(self, to_address: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._settings.from_address
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        if self._settings.use_tls:
            server = smtplib.SMTP(self._settings.host, self._settings.port)
            server.starttls()
        else:
            server = smtplib.SMTP(self._settings.host, self._settings.port)
        try:
            if self._settings.username and self._settings.password:
                server.login(self._settings.username, self._settings.password)
            server.send_message(message)
        finally:
            server.quit()


def create_email_sender(settings: SmtpSettings | None, logger: logging.Logger | None = None) -> EmailSender:
    """Return an email sender for the provided *settings*."""

    if settings:
        return SmtpEmailSender(settings)
    return ConsoleEmailSender(logger)
