from fastapi import APIRouter, Query, HTTPException

from app.modules.unsubscribe import run_unsubscribe
from app.db.supabase import get_unsubscribe_history

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


@router.get("/run")
@router.post("/run")
def trigger_unsubscribe(
    max_emails: int = Query(default=50, ge=1, le=500),
    skip_already_done: bool = Query(default=True),
):
    try:
        results = run_unsubscribe(max_emails=max_emails, skip_already_done=skip_already_done)
    except RuntimeError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "skipped": sum(1 for r in results if "skipped" in (r.get("status") or "")),
    }
    return {"summary": summary, "results": results}


@router.get("/history")
def unsubscribe_history(limit: int = Query(default=50, ge=1, le=500)):
    try:
        data = get_unsubscribe_history(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"count": len(data), "items": data}
