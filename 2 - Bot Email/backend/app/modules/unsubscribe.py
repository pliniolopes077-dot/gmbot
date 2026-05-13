"""Unsubscribe module: reads inbox, extracts List-Unsubscribe headers, fires GET requests."""
import re
import base64
import logging
from typing import Optional

import requests

from app.auth.gmail import get_authenticated_service
from app.db.supabase import log_unsubscribe, is_already_unsubscribed

logger = logging.getLogger(__name__)

# Matches http/https URLs inside angle brackets: <https://...>
_URL_PATTERN = re.compile(r"<(https?://[^>]+)>")


def _extract_http_url(header_value: str) -> Optional[str]:
    """Pulls the first HTTP URL from a List-Unsubscribe header value."""
    match = _URL_PATTERN.search(header_value)
    return match.group(1) if match else None


def _decode_header(raw: str) -> str:
    """Gmail returns header values as plain strings already decoded."""
    return raw.strip()


def _get_message_headers(service, msg_id: str) -> dict:
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From", "Subject", "List-Unsubscribe"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    return headers


def _fire_unsubscribe_request(url: str, timeout: int = 10) -> tuple[str, int]:
    """
    Sends GET to the unsubscribe URL.
    Returns (status, http_status_code).
    """
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        if resp.status_code < 400:
            return "success", resp.status_code
        return "failed", resp.status_code
    except requests.exceptions.Timeout:
        return "failed", 0
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error for %s: %s", url, exc)
        return "failed", 0


def run_unsubscribe(
    max_emails: int = 50,
    skip_already_done: bool = True,
) -> list[dict]:
    """
    Main entry point. Scans inbox for emails with List-Unsubscribe,
    fires the unsubscribe URL, and logs results to Supabase.

    Returns a list of result dicts for each processed email.
    """
    service = get_authenticated_service()
    results = []

    # Fetch messages that have a List-Unsubscribe header (Gmail doesn't filter
    # by header natively, so we fetch recent inbox messages and inspect locally)
    response = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=max_emails,
    ).execute()

    messages = response.get("messages", [])
    logger.info("Fetched %d messages to inspect", len(messages))

    for msg_ref in messages:
        msg_id = msg_ref["id"]
        try:
            headers = _get_message_headers(service, msg_id)
        except Exception as exc:
            logger.warning("Could not fetch headers for %s: %s", msg_id, exc)
            continue

        raw_unsub = headers.get("List-Unsubscribe")
        if not raw_unsub:
            continue

        sender = headers.get("From", "unknown")
        subject = headers.get("Subject", "(no subject)")
        url = _extract_http_url(_decode_header(raw_unsub))

        if not url:
            # Only mailto: present — skip (no HTTP unsubscribe available)
            logger.debug("No HTTP URL in List-Unsubscribe for %s", sender)
            results.append({
                "email_id": msg_id,
                "sender": sender,
                "subject": subject,
                "unsubscribe_url": None,
                "status": "skipped_mailto_only",
                "status_code": None,
            })
            continue

        if skip_already_done and is_already_unsubscribed(sender):
            logger.info("Already unsubscribed from %s, skipping", sender)
            results.append({
                "email_id": msg_id,
                "sender": sender,
                "subject": subject,
                "unsubscribe_url": url,
                "status": "skipped_already_done",
                "status_code": None,
            })
            continue

        status, code = _fire_unsubscribe_request(url)
        logger.info("[%s] %s → %s (HTTP %s)", status.upper(), sender, url, code)

        db_record = log_unsubscribe(
            email_id=msg_id,
            sender=sender,
            subject=subject,
            unsubscribe_url=url,
            status=status,
            status_code=code,
        )
        results.append(db_record)

    return results
