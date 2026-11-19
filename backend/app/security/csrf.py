"""Protection CSRF (spec §8, D-05, threat model T-15/T-16) — issue #5.

Mécanisme : jeton opaque **par session** (256 bits, ``token_urlsafe``),
dont **seul le hash** (SHA-256) est stocké dans ``sessions.csrf_token_hash``.
Le jeton en clair est exposé **uniquement** par ``GET /auth/csrf`` (rotation
à chaque émission) ; tout ``POST/PATCH/PUT/DELETE`` sous ``/api/v1`` qui
présente une session valide exige l'en-tête ``X-CSRF-Token`` correct.

La vérification est par **comparaison hachée** : hash du jeton reçu ==
hash stocké, via ``hmac.compare_digest`` (temps constant).

Exemptions (décision documentée dans la PR #5, future D-19) :

- ``POST /auth/login``, ``POST /auth/reset-password``,
  ``POST /auth/accept-invitation`` : **toujours exemptes** — contexte
  sans session de travail (utilisateur non connecté ; le flux est
  couvert par le rate limit e-mail+IP ou IP seul + token à usage unique) ;
- ``POST /auth/forgot-password`` : exempte **uniquement sans session
  active** ; si une session valide est présente, le CSRF est exigé.

Tout autre chemin ``/api/v1`` mutant : si le cookie présente une session
valide, le jeton est exigé (403 ``CSRF_INVALID`` sinon) ; sans session
valide, le middleware laisse passer et c'est la dépendance
``get_current_user`` qui répond 401 ``UNAUTHENTICATED`` (état
indiscernable, T-12/T-13).

Le middleware est **ASGI global** (pas par route) : il est installé dans
``create_app`` entre le middleware de request ID (extérieur, fournit
``request.state.request_id``) et le routeur.
"""
from __future__ import annotations

import hmac
import uuid

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.db import SessionLocal
from app.exceptions import ErrorCode
from app.schemas.common import ErrorDetail
from app.security.sessions import hash_token, lookup_active_session

CSRF_HEADER = "X-CSRF-Token"
CSRF_INVALID_MESSAGE = "Jeton CSRF manquant ou invalide."

_API_PREFIX = "/api/v1"
_MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})

# Exempts inconditionnels : flux sans session de travail (D-19, issue #5).
_CSRF_EXEMPT_PATHS: frozenset[str] = frozenset(
    {
        f"{_API_PREFIX}/auth/login",
        f"{_API_PREFIX}/auth/reset-password",
        f"{_API_PREFIX}/auth/accept-invitation",
    }
)


def csrf_token_is_valid(received: str | None, stored_hash: str) -> bool:
    """Vérification par comparaison hachée (D-05, ``hmac.compare_digest``).

    ``received`` absent/None => toujours invalide (pas de détail d'erreur
    distinct, anti-oracle).
    """
    if received is None or not received:
        return False
    return hmac.compare_digest(hash_token(received), stored_hash)


class CsrfProtectionMiddleware:
    """Exige ``X-CSRF-Token`` valide sur toute mutation ``/api/v1`` portant
    une session cookie valide (cf. docstring de module pour les exempts).

    Réponse de rejet : 403 ``CSRF_INVALID`` au format normalisé
    ``{"error": {code, message, request_id}}`` (spec §6, D-06) — le
    ``request_id`` est lu de ``scope["state"]`` (posé par le middleware
    ``RequestIDMiddleware``, installé à l'extérieur).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _MUTATING_METHODS:
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        if not path.startswith(_API_PREFIX) or path in _CSRF_EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        session_token = _cookie_session_token(scope)
        if not session_token:
            # Pas de cookie : pas de session à protéger ; la route
            # authentifiée répondra 401 si requise.
            await self.app(scope, receive, send)
            return

        session = _lookup_session(session_token)
        if session is None:
            # Session inconnue/expirée/révocée : le jeton ne peut pas être
            # vérifié ; 401 de la dépendance d'authentification (indiscernable).
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        received = request.headers.get(CSRF_HEADER)
        if not csrf_token_is_valid(received, session.csrf_token_hash):
            await _csrf_reject(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _cookie_session_token(scope: Scope) -> str | None:
    settings = get_settings()
    request = Request(scope)
    value = request.cookies.get(settings.SESSION_COOKIE_NAME)
    return value or None


def _lookup_session(session_token: str):
    """Session valide associée au cookie (lecture sur sa propre connexion —
    le middleware précède la dépendance ``get_db`` du routeur)."""
    db = SessionLocal()
    try:
        return lookup_active_session(db, session_token)
    finally:
        db.close()


async def _csrf_reject(scope: Scope, receive: Receive, send: Send) -> None:
    state = scope.get("state") or {}
    request_id = state.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        request_id = str(uuid.uuid4())
    detail = ErrorDetail(
        code=ErrorCode.CSRF_INVALID.value,
        message=CSRF_INVALID_MESSAGE,
        request_id=request_id,
    )
    response = JSONResponse(status_code=403, content={"error": detail.model_dump()})
    await response(scope, receive, send)


__all__ = [
    "CSRF_HEADER",
    "CSRF_INVALID_MESSAGE",
    "CsrfProtectionMiddleware",
    "csrf_token_is_valid",
]
