"""Notification helpers for trade alerts."""

from __future__ import annotations

import smtplib
import requests
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

import yaml

CONFIG_FILE = Path(__file__).resolve().parents[1] / "config.yaml"


def _load_config(config_file: Path = CONFIG_FILE) -> dict:
    if config_file.exists():
        with open(config_file, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def _send_email(to_addr: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "noreply@example.com"
    msg["To"] = to_addr
    msg.set_content(body)

    try:
        with smtplib.SMTP("localhost") as s:
            s.send_message(msg)
    except Exception as exc:
        print(f"Failed to send email: {exc}")


def _send_webhook(url: str, body: str) -> None:
    try:
        requests.post(url, json={"text": body}, timeout=5)
    except Exception as exc:
        print(f"Failed to send webhook: {exc}")


def send_notification(message: str, *, subject: str = "Trade Alert", config_file: Path = CONFIG_FILE) -> None:
    """Send ``message`` using configured notification methods."""
    cfg = _load_config(config_file)
    email = cfg.get("email")
    webhook_url = cfg.get("webhook_url")

    if email:
        _send_email(email, subject, message)
    if webhook_url:
        _send_webhook(webhook_url, message)
