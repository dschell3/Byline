"""SCRUM-10: SMTP delivery tests without sending real email."""

from unittest.mock import patch

import pytest

import reset_mail


def test_unconfigured_smtp_does_not_send(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No provider configured means no SMTP connection."""
    for key in (
        "RESET_SMTP_HOST",
        "RESET_FROM_EMAIL",
        "RESET_WEB_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    with patch.object(reset_mail.smtplib, "SMTP") as smtp:
        reset_mail.send_reset_email("member@example.com", "test-token")
        smtp.assert_not_called()


def test_configured_smtp_sends_secure_reset_link(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The message contains the link and delivery uses TLS."""
    settings = {
        "RESET_SMTP_HOST": "smtp.example.com",
        "RESET_SMTP_PORT": "587",
        "RESET_FROM_EMAIL": "noreply@example.com",
        "RESET_WEB_BASE_URL": "https://byline.example",
        "RESET_SMTP_USERNAME": "smtp-user",
        "RESET_SMTP_PASSWORD": "test-secret",
        "RESET_SMTP_STARTTLS": "true",
    }

    for key, value in settings.items():
        monkeypatch.setenv(key, value)

    with patch.object(reset_mail.smtplib, "SMTP") as smtp_factory:
        reset_mail.send_reset_email("member@example.com", "test-token")

        smtp_factory.assert_called_once_with("smtp.example.com", 587, timeout=10)

        connection = smtp_factory.return_value.__enter__.return_value

        connection.starttls.assert_called_once()
        connection.login.assert_called_once_with("smtp-user", "test-secret")
        connection.send_message.assert_called_once()

        message = connection.send_message.call_args.args[0]

        assert message["To"] == "member@example.com"
        assert message["From"] == "noreply@example.com"
        assert "https://byline.example/reset/test-token" in message.get_content()
        assert "one hour" in message.get_content()
