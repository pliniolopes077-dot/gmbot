"""Reads inbox + promotions + updates, extracts List-Unsubscribe, fires GET requests."""
import re
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from app.auth.gmail import get_authenticated_service
from app.db.supabase import log_unsubscribe, is_already_unsubscribed

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"<(https?://[^>]+)>")

# Labels where newsletters live
_SEARCH_QUERIES = [
    "category:promotions",
    "category:updates",
    "in:inbox has:unsubscribe",
]


def _extract_http_url(header_value: str) -> Optional[str]:
    match = _URL_PATTERN.search(header_value)
    return match.group(1) if match else None


def _fetch_metadata(service, msg_id: str) -> tuple[str, Optional[dict]]:
    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["From", "Subject", "List-Unsubscribe"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        return msg_id, headers
    except Exception as exc:
        logger.warning("Could not fetch %s: %s", msg_id, exc)
        return msg_id, None


def _fire_unsubscribe(url: str, timeout: int = 8) -> tuple[str, int]:
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        return ("success" if resp.status_code < 400 else "failed", resp.status_code)
    except requests.exceptions.Timeout:
        return "failed", 0
    except requests.exceptions.RequestException as exc:
        logger.warning("Request error for %s: %s", url, exc)
        return "failed", 0


def run_unsubscribe(max_emails: int = 200, skip_already_done: bool = True) -> list[dict]:
    service = get_authenticated_service()

    # Collect unique message IDs from all label searches
    seen_ids: set[str] = set()
    msg_ids: list[str] = []

    per_query = max(max_emails // len(_SEARCH_QUERIES), 50)
    for query in _SEARCH_QUERIES:
        try:
            resp = service.users().messages().list(
                userId="me", q=query, maxResults=per_query
            ).execute()
            for m in resp.get("messages", []):
                if m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    msg_ids.append(m["id"])
        except Exception as exc:
            logger.warning("List query '%s' failed: %s", query, exc)

    logger.info("Fetching metadata for %d messages (parallel)", len(msg_ids))

    # Fetch all metadata in parallel (10 workers)
    header_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_metadata, service, mid): mid for mid in msg_ids}
        for future in as_completed(futures):
            mid, headers = future.result()
            if headers:
                header_map[mid] = headers

    # Process — deduplicate by sender so we don't unsubscribe the same address twice
    results: list[dict] = []
    seen_senders: set[str] = set()

    for msg_id in msg_ids:
        headers = header_map.get(msg_id)
        if not headers:
            continue

        raw_unsub = headers.get("List-Unsubscribe")
        if not raw_unsub:
            continue

        sender = headers.get("From", "unknown")
        subject = headers.get("Subject", "(no subject)")

        if sender in seen_senders:
            continue
        seen_senders.add(sender)

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
