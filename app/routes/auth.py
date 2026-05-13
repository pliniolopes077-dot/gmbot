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
    try:
        flow = get_oauth_flow()
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"fetch_token failed: {exc}")
    try:
        save_credentials(flow.credentials)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"save_credentials failed: {exc}")
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
