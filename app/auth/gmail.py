"""Gmail OAuth2 flow. Tokens are stored in Supabase (stateless-safe for Vercel)."""
import json
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings
from app.db.supabase import save_token, load_token, delete_token

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_oauth_flow() -> Flow:
    s = get_settings()
    client_config = {
        "web": {
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "redirect_uris": [s.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config, scopes=SCOPES, redirect_uri=s.google_redirect_uri
    )


def save_credentials(credentials: Credentials) -> None:
    data = json.loads(credentials.to_json())
    save_token({
        "token": data.get("token"),
        "refresh_token": data.get("refresh_token"),
        "token_uri": data.get("token_uri"),
        "client_id": data.get("client_id"),
        "client_secret": data.get("client_secret"),
        "scopes": data.get("scopes"),
    })


def load_credentials() -> Optional[Credentials]:
    data = load_token()
    if not data:
        return None
    return Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )


def revoke_credentials() -> None:
    delete_token()


def get_authenticated_service():
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Not authenticated. Visit /auth/login first.")
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        save_credentials(creds)
    return build("gmail", "v1", credentials=creds)
