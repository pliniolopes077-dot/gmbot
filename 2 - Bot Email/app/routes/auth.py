from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.auth.gmail import get_oauth_flow, save_credentials, load_credentials, revoke_credentials
from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
def login():
    flow = get_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(code: str, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    flow = get_oauth_flow()
    flow.fetch_token(code=code)
    save_credentials(flow.credentials)
    settings = get_settings()
    return RedirectResponse(f"{settings.frontend_url}?auth=success")


@router.get("/status")
def status():
    creds = load_credentials()
    if creds is None:
        return {"authenticated": False}
    return {"authenticated": True, "expired": creds.expired}


@router.post("/logout")
def logout():
    revoke_credentials()
    return {"message": "Logged out"}
