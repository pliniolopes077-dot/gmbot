"""Reads inbox, extracts List-Unsubscribe headers, fires GET requests, logs to Supabase."""
import re
import logging
from typing import Optional

import requests

from app.auth.gmail import get_authenticated_service
from app.db.supabase import log_unsubscribe, is_already_unsubscribed

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"<(https?://[^>]+)>")


def _extract_http_url(header_value: str) -> Optional[str]:
    match = _URL_PATTERN.search(header_value)
    return match.group(1) if match else None


def _fire_unsubscribe(url: str, timeout: int = 10) -> tuple[str, int]:
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        return ("success" if resp.status_code < 400 else "failed", resp.status_code)
    except requests.exceptions.Timeout:
        return "failed", 0
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error for %s: %s", url, exc)
        return "failed", 0


def run_unsubscribe(max_emails: int = 50, skip_already_done: bool = True) -> list[dict]:
    service = get_authenticated_service()
    results = []

    response = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_emails
    ).execute()

    for msg_ref in response.get("messages", []):
        msg_id = msg_ref["id"]
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="metadata",
                metadataHeaders=["From", "Subject", "List-Unsubscribe"],
            ).execute()
        except Exception as exc:
            logger.warning("Could not fetch %s: %s", msg_id, exc)
            continue

        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        raw_unsub = headers.get("List-Unsubscribe")
        if not raw_unsub:
            continue

        sender = headers.get("From", "unknown")
        subject = headers.get("Subject", "(no subject)")
        url = _extract_http_url(raw_unsub.strip())

        if not url:
            results.append({"email_id": msg_id, "sender": sender, "subject": subject,
                            "unsubscribe_url": None, "status": "skipped_mailto_only"})
            continue

        if skip_already_done and is_already_unsubscribed(sender):
            results.append({"email_id": msg_id, "sender": sender, "subject": subject,
                            "unsubscribe_url": url, "status": "skipped_already_done"})
            continue

        status, code = _fire_unsubscribe(url)
        logger.info("[%s] %s → HTTP %s", status.upper(), sender, code)

        record = log_unsubscribe(
            email_id=msg_id, sender=sender, subject=subject,
            unsubscribe_url=url, status=status, status_code=code,
        )
        results.append(record)

    return results
