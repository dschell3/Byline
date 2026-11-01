"""SMTP password-reset email delivery for SCRUM-10.

No email is sent until SMTP settings are configured.
Never log or return the raw reset token.
"""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def send_reset_email(recipient: str, token: str) -> None:
    """Send a reset link using an environment-configured SMTP server."""
    host = os.getenv("RESET_SMTP_HOST")
    sender = os.getenv("RESET_FROM_EMAIL")
    base_url = os.getenv("RESET_WEB_BASE_URL")

    if not all((host, sender, base_url)):
        logger.warning("Password-reset email delivery is not configured")
        return

    try:
        port = int(os.getenv("RESET_SMTP_PORT", "587"))
    except ValueError:
        logger.error("Invalid password-reset SMTP port")
        return

    username = os.getenv("RESET_SMTP_USERNAME")
    password = os.getenv("RESET_SMTP_PASSWORD")
    starttls = os.getenv("RESET_SMTP_STARTTLS", "true").lower() == "true"

    if (username or password) and not starttls:
        logger.error("Authenticated SMTP requires TLS")
        return

    url = f"{base_url.rstrip('/')}/reset/{quote(token, safe='')}"

    message = EmailMessage()
    message["Subject"] = "Reset your Byline password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "We received a request to reset your Byline password.\n\n"
        f"Open this link to choose a new password:\n{url}\n\n"
        "The link expires in one hour and can only be used once.\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if starttls:
                smtp.starttls(context=ssl.create_default_context())
            if username and password:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Password-reset email delivery failed")
