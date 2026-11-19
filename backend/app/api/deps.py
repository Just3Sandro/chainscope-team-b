"""Dépendances FastAPI partagées (socle, spec §6 ; issue #5 : authentification).

``get_current_user`` (401 ``UNAUTHENTICATED``) et ``get_optional_user``
(``None`` au lieu de 401) résolvent la session du cookie ``cs_session``
(D-04) : lookup par **hash SHA-256** du token (``sessions.token_hash``),
contrôle d'expiration et de révocation, puis contrôle de l'utilisateur
actif. Le compte suspendu est traité comme « non connecté » (D-17 :
aucune fuite d'existence).

La session valide est posée sur ``request.state.session`` pour les routes
qui en ont besoin sans double lookup (``GET /auth/csrf``,
``POST /auth/logout``).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.exceptions import ApiError, ErrorCode
from app.models import PlatformAdmin, User
from app.security.sessions import lookup_active_session

MSG_UNAUTHENTICATED = "Non connecté"

DbSession = Annotated[Session, Depends(get_db)]
"""Dépendance FastAPI (annotation `Annotated`) : une session SQLAlchemy par
requête, ouverte puis fermée par la fonction de dépendance `get_db`
(``app.db``) — ce n'est pas un middleware."""


def get_request_id(request: Request) -> str:
    """ID de requête porté par le middleware `RequestIDMiddleware` (D-06).

    À utiliser pour journaliser (audit) et corrélérer les réponses d'erreur ;
    jamais de valeur d'en-tête client en dehors de ce chemin.
    """
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) and rid else "inconnu"


def _unauthenticated() -> ApiError:
    return ApiError(401, ErrorCode.UNAUTHENTICATED, MSG_UNAUTHENTICATED)


def _resolve_user(request: Request, db: DbSession) -> User | None:
    """Utilisateur actif de la session du cookie, ou ``None`` (état unique
    pour absent/inconnu/expirée/révocée/suspendu — T-12/T-13, D-17)."""
    settings = get_settings()
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    session = lookup_active_session(db, token) if token else None
    if session is None:
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    request.state.session = session
    request.state.user = user
    return user


def get_current_user(request: Request, db: DbSession) -> User:
    """Session valide exigée ; sinon 401 ``UNAUTHENTICATED`` normalisé."""
    user = _resolve_user(request, db)
    if user is None:
        raise _unauthenticated()
    return user


def get_optional_user(request: Request, db: DbSession) -> User | None:
    """Comme ``get_current_user`` mais sans lever 401 (renvoie ``None``).

    Usage : ``POST /auth/forgot-password`` — le CSRF n'est exigé par le
    middleware que si une session active est présente (exemption
    conditionnelle documentée, D-19, issue #5).
    """
    return _resolve_user(request, db)


AuthenticatedUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_platform_admin(user: AuthenticatedUser, db: DbSession) -> User:
    """Garde plateforme (issue #7, spec §1/§6) : ``PLATFORM_ADMIN`` UNIQUEMENT.

    Vérifie la présence de l'utilisateur dans ``platform_admins``
    (source unique des rôles — spec §8 : aucune permission déduite du
    body ni de l'URL). Toute autre session authentifiée — ``TENANT_ADMIN``,
    ``PENTESTER``, ``CLIENT_VIEWER`` — reçoit un 403 ``FORBIDDEN`` ;
    l'absence de session est déjà refusée en amont (401 ``UNAUTHENTICATED``,
    ``get_current_user``).
    """
    row = db.execute(
        select(PlatformAdmin.id).where(PlatformAdmin.user_id == user.id)
    ).scalar_one_or_none()
    if row is None:
        raise ApiError.forbidden()
    return user


PlatformAdminUser = Annotated[User, Depends(require_platform_admin)]


__all__ = [
    "AuthenticatedUser",
    "DbSession",
    "MSG_UNAUTHENTICATED",
    "OptionalUser",
    "PlatformAdminUser",
    "get_current_user",
    "get_optional_user",
    "get_request_id",
    "require_platform_admin",
]
