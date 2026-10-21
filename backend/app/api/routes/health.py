from fastapi import APIRouter, Response, status
from redis import Redis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: the API process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response) -> dict:
    """Readiness: the API can reach Postgres and Redis."""
    checks: dict[str, str] = {}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        checks["postgres"] = f"error: {type(exc).__name__}"

    try:
        Redis.from_url(settings.redis_url).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {type(exc).__name__}"

    all_ok = all(value == "ok" for value in checks.values())
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if all_ok else "degraded", "checks": checks}
