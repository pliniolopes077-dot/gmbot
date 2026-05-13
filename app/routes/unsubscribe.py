from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.modules.unsubscribe import run_unsubscribe
from app.db.supabase import get_unsubscribe_history

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])


@router.get("/run")
@router.post("/run")
def trigger_unsubscribe(
    batch_size: int = Query(default=300, ge=1, le=500),
    skip_already_done: bool = Query(default=True),
    page_token: Optional[str] = Query(default=None),
):
    try:
        data = run_unsubscribe(
            batch_size=batch_size,
            skip_already_done=skip_already_done,
            page_token=page_token,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    items = data["results"]
    summary = {
        "total": len(items),
        "success": sum(1 for r in items if r.get("status") == "success"),
        "failed": sum(1 for r in items if r.get("status") == "failed"),
        "skipped": sum(1 for r in items if "skipped" in (r.get("status") or "")),
    }
    return {"summary": summary, "results": items, "progress": data["progress"]}


@router.get("/history")
def unsubscribe_history(limit: int = Query(default=100, ge=1, le=500)):
    try:
        data = get_unsubscribe_history(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"count": len(data), "items": data}
