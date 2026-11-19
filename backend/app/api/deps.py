"""Dépendances FastAPI partagées (socle, spec §6)."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db


def get_request_id(request: Request) -> str:
    """ID de requête porté par le middleware `RequestIDMiddleware` (D-06).

    À utiliser pour journaliser (audit) et corrélérer les réponses d'erreur ;
    jamais de valeur d'en-tête client en dehors de ce chemin.
    """
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) and rid else "inconnu"


DbSession = Annotated[Session, Depends(get_db)]
"""Dépendance FastAPI (annotation `Annotated`) : une session SQLAlchemy par
requête, ouverte puis fermée par la fonction de dépendance `get_db`
(`app.db`) — ce n'est pas un middleware."""


__all__ = ["DbSession", "get_request_id"]
