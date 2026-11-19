"""Endpoint de santé du socle (pas d'endpoint métier ici — issue #4).

`GET /api/v1/health` => 200 `{"status":"ok","db":"up"}` si la base est
joignable ; 503 `{"status":"error","db":"down"}` sinon. Contrat volontairement
simple : le healthcheck ne révèle ni version, ni stack trace.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession

router = APIRouter(tags=["health"])

_HEALTH_QUERY = text("SELECT 1")
_HEALTH_OK: dict[str, str] = {"status": "ok", "db": "up"}
_HEALTH_DOWN: dict[str, str] = {"status": "error", "db": "down"}


@router.get("/health", response_model=None)
def health(db: DbSession) -> dict[str, str] | JSONResponse:
    try:
        db.execute(_HEALTH_QUERY)
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content=_HEALTH_DOWN)
    return _HEALTH_OK
