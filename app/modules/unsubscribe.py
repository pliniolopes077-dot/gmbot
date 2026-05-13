"""Paginated unsubscribe scan across promotions, updates and inbox."""
import re
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests as req

from app.auth.gmail import get_authenticated_service
from app.db.supabase import log_unsubscribe, is_already_unsubscribed

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"<(https?://[^>]+)>")

# Covers newsletters without scanning personal emails
_QUERY = "category:promotions OR category:updates OR (in:inbox has:unsubscribe)"


def _extract_http_url(header_value: str) -> Optional[str]:
    match = _URL_PATTERN.search(header_value)
    return match.group(1) if match else None


def _fetch_metadata(service, msg_id: str) -> tuple[str, Optional[dict]]:
    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="metadata",
            metadataHeaders=["From", "Subject", "List-Unsubscribe"],
        ).execute()
        return msg_id, {h["name"]: h["value"] for h in msg["payload"]["headers"]}
    except Exception as exc:
        logger.warning("metadata %s: %s", msg_id, exc)
        return msg_id, None


def _fire(url: str) -> tuple[str, int]:
    try:
        r = req.get(url, timeout=8, allow_redirects=True)
        return ("success" if r.status_code < 400 else "failed", r.status_code)
    except req.exceptions.Timeout:
        return "failed", 0
    except req.exceptions.RequestException:
        return "failed", 0


def run_unsubscribe(
    batch_size: int = 300,
    skip_already_done: bool = True,
    page_token: Optional[str] = None,
) -> dict:
    """
    Processes one page of emails. Returns results + next_page_token
    so the client can continue pagination.
    """
    service = get_authenticated_service()

    # Fetch one page of message IDs
    list_kwargs: dict = {"userId": "me", "q": _QUERY, "maxResults": batch_size}
    if page_token:
        list_kwargs["pageToken"] = page_token

    response = service.users().messages().list(**list_kwargs).execute()
    msg_ids = [m["id"] for m in response.get("messages", [])]
    next_token = response.get("nextPageToken")

    logger.info("Batch: %d messages | next_token=%s", len(msg_ids), bool(next_token))

    # Parallel metadata fetch
    header_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(_fetch_metadata, service, mid): mid for mid in msg_ids}
        for future in as_completed(futures):
            mid, headers = future.result()
            if headers:
                header_map[mid] = headers

    # Build work list — deduplicate by sender
    seen_senders: set[str] = set()
    work: list[tuple[str, str, str, str]] = []  # (msg_id, sender, subject, url)

    for msg_id in msg_ids:
        headers = header_map.get(msg_id)
        if not headers:
            continue
        raw_unsub = headers.get("List-Unsubscribe")
        if not raw_unsub:
            continue
        sender = headers.get("From", "unknown")
        if sender in seen_senders:
            continue
        seen_senders.add(sender)
        url = _extract_http_url(raw_unsub.strip())
        if url:
            work.append((msg_id, sender, headers.get("Subject", ""), url))

    # Parallel unsubscribe requests
    results: list[dict] = []
    skipped = 0

    def _process(item: tuple[str, str, str, str]) -> Optional[dict]:
        msg_id, sender, subject, url = item
        if skip_already_done and is_already_unsubscribed(sender):
            return {"email_id": msg_id, "sender": sender, "subject": subject,
                    "unsubscribe_url": url, "status": "skipped_already_done"}
        status, code = _fire(url)
        logger.info("[%s] %s → HTTP %s", status.upper(), sender, code)
        return log_unsubscribe(email_id=msg_id, sender=sender, subject=subject,
                               unsubscribe_url=url, status=status, status_code=code)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_process, item) for item in work]
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    return {
        "results": results,
        "progress": {
            "emails_scanned": len(msg_ids),
            "has_more": next_token is not None,
            "next_page_token": next_token,
        },
    }
