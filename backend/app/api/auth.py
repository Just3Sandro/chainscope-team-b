"""Routes d'authentification (spec §6, issue #5) : ``/auth/*``.

- ``POST /auth/login``          -> 200 + objet D-17 + cookie ``cs_session``
  (HttpOnly, SameSite=Lax, Secure en production — D-04) ;
- ``GET  /auth/me``             -> contrat D-17 figé (401 sinon) ;
- ``GET  /auth/csrf``          -> ``{csrf_token}`` (rotation D-05) ;
- ``POST /auth/logout``         -> 204 (révocation + cookie supprimé) ;
- ``POST /auth/forgot-password``-> 200 neutre identique (T-21, D-19) ;
- ``POST /auth/reset-password`` -> 200 / 400 ``INVALID_TOKEN`` / 422
  (politique mot de passe, usage unique T-18, T-19).

Le CSRF est exigé par le middleware global (``app.security.csrf``) sur
toute mutation portant une session valide — la seule exemption de ce
routeur est ``forgot-password`` sans session active (D-19).
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi import status as http_status

from app.api.deps import AuthenticatedUser, DbSession, get_request_id
from app.config import get_settings
from app.schemas.auth import (
    AuthMe,
    CsrfResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
)
from app.security import sessions as session_security
from app.security.rate_limit import client_ip
from app.services import auth_service
from app.services.audit import AuditContext

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    """Cookie de session (D-04) : HttpOnly, SameSite=Lax, Secure si
    ``SESSION_COOKIE_SECURE`` (défaut : dérivé de ``ENV``), ``Path=/api``
    (arbitrage Cyber T-14, PR #32 : le backend ne sert que ``/api/v1``,
    le path le plus étroit possible limite la portée du cookie)."""
    settings = get_settings()
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.SESSION_LIFETIME_HOURS * 3600,
        path="/api",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


def _delete_session_cookie(response: Response) -> None:
    """Suppression du cookie avec des attributs **identiques** au set
    (D-04, issue #5 ; arbitrage Cyber T-14 : ``Path=/api`` comme la pose) :
    un cookie ne se supprime que posé sur le même chemin avec les mêmes
    attributs de sécurité."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/api",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


@router.post("/login", response_model=AuthMe)
def login(
    payload: LoginRequest,
    request: Request,
    db: DbSession,
    response: Response,
) -> AuthMe:
    """Connexion : e-mail normalisé, Argon2id, 401 générique, rate limit
    e-mail+IP (D-07), audit succès/échec (issue #5). Exempt CSRF
    (contexte sans session — D-19)."""
    result = auth_service.login(
        db,
        AuditContext(db=db, request_id=get_request_id(request)),
        email=payload.email,
        password=payload.password,
        client_ip=client_ip(request),
    )
    _set_session_cookie(response, result.session_token)
    return AuthMe(**auth_service.me_payload(db, result.user))


@router.get("/me", response_model=AuthMe)
def me(user: AuthenticatedUser, db: DbSession) -> AuthMe:
    """Contrat D-17 exact : 401 si non connecté ou compte suspendu ;
    arrays vides ``[]`` ; ``platform_admin`` booléen."""
    return AuthMe(**auth_service.me_payload(db, user))


@router.get("/csrf", response_model=CsrfResponse)
def csrf_token(request: Request, user: AuthenticatedUser, db: DbSession) -> CsrfResponse:
    """Jeton CSRF de la session courante (D-05) : rotation à chaque
    émission — seul le hash est stocké ; le jeton en clair ne circule
    que dans cette réponse."""
    session = request.state.session
    token = session_security.rotate_csrf_token(db, session)
    db.commit()
    return CsrfResponse(csrf_token=token)


@router.post("/logout", status_code=http_status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    user: AuthenticatedUser,
    db: DbSession,
    response: Response,
) -> None:
    """Déconnexion : révocation de la session (T-10), cookie supprimé avec
    attributs identiques (D-04), audit. CSRF exigé (session valide —
    mutation authentifiée)."""
    auth_service.logout(
        db,
        AuditContext(
            db=db,
            request_id=get_request_id(request),
            actor_id=user.id,
        ),
        session=request.state.session,  # type: ignore[attr-defined]
        user=user,
    )
    _delete_session_cookie(response)
    return None


@router.post("/forgot-password")
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: DbSession,
) -> dict:
    """Demande de réinitialisation : réponse **identique** (200 neutre) que
    le compte existe ou non (T-21, D-19). Rate limit e-mail+IP. Exempt CSRF
    uniquement sans session active (middleware : session => exigé)."""
    auth_service.forgot_password(
        db,
        AuditContext(db=db, request_id=get_request_id(request)),
        email=payload.email,
        client_ip=client_ip(request),
    )
    return {"code": "OK", "message": auth_service.MSG_FORGOT_OK}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: DbSession,
) -> dict:
    """Réinitialisation : token usage unique 30 min, politique mot de
    passe (422 message unique), révocation de toutes les sessions (T-11),
    audit. Exempt CSRF (flux sans session de travail — D-19)."""
    auth_service.reset_password(
        db,
        AuditContext(db=db, request_id=get_request_id(request)),
        token=payload.token,
        new_password=payload.password,
        client_ip=client_ip(request),
    )
    return {"code": "OK", "message": auth_service.MSG_RESET_OK}


__all__ = ["router"]
