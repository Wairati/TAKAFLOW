from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness check — no dependencies, just confirms the API process is up."""
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness check — confirms the configured DATABASE_URL is reachable."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable"}
