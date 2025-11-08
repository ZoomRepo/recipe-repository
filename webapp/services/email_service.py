"""Utility for sending transactional email from the web application."""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.text import MIMEText

from ..config import MailConfig

logger = logging.getLogger(__name__)


class EmailService:
    """Send transactional messages such as login codes."""

    def __init__(self, config: MailConfig) -> None:
        self._config = config

    def send_login_code(self, recipient: str, code: str) -> None:
        """Send the temporary login *code* to *recipient*."""

        subject = "Your Recipe Repository access code"
        body = (
            "Use the code below to finish signing in to the Recipe Repository:\n\n"
            f"{code}\n\n"
            "The code expires shortly, so please use it soon."
        )
        self._send_email(recipient, subject, body)

    def _send_email(self, recipient: str, subject: str, body: str) -> None:
        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = self._config.sender
        message["To"] = recipient

        if not self._config.enabled:
            logger.info(
                "Email sending disabled; would have sent message to %s", recipient
            )
            return

        context = ssl.create_default_context()
        with smtplib.SMTP(self._config.host, self._config.port) as server:
            if self._config.use_tls:
                server.starttls(context=context)
            if self._config.username and self._config.password:
                server.login(self._config.username, self._config.password)
            server.sendmail(self._config.sender, [recipient], message.as_string())
