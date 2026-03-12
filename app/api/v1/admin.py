from fastapi import APIRouter, Depends

from app.api.deps import require_admin_token

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/ping", dependencies=[Depends(require_admin_token)])
def admin_ping() -> dict[str, str]:
    return {"status": "ok"}
