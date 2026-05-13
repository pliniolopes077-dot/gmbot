"""Supabase client and unsubscribe logging."""
from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client

from app.config import get_settings

_client: Optional[Client] = None


def get_client() -> Client:
    global _client
    if _client is None:
        s = get_settings()
        _client = create_client(s.supabase_url, s.supabase_service_key)
    return _client


def log_unsubscribe(
    email_id: str,
    sender: str,
    subject: str,
    unsubscribe_url: str,
    status: str,
    status_code: Optional[int] = None,
    error_message: Optional[str] = None,
) -> dict:
    record = {
        "email_id": email_id,
        "sender": sender,
        "subject": subject,
        "unsubscribe_url": unsubscribe_url,
        "status": status,
        "status_code": status_code,
        "error_message": error_message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = get_client().table("unsubscribes").insert(record).execute()
    return result.data[0] if result.data else record


def get_unsubscribe_history(limit: int = 50) -> list:
    result = (
        get_client()
        .table("unsubscribes")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def is_already_unsubscribed(sender: str) -> bool:
    result = (
        get_client()
        .table("unsubscribes")
        .select("id")
        .eq("sender", sender)
        .eq("status", "success")
        .limit(1)
        .execute()
    )
    return len(result.data) > 0
