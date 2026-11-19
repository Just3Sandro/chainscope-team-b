"""Sessions opaques côté serveur (spec §8, D-04, threat model T-10…T-14).

Contrais de stockage :

- token opaque de **256 bits** (``secrets.token_hex(32)``) ;
- **seul le hash SHA-256** du token est stocké (colonne ``sessions.token_hash``,
  déjà unique — pas d'index sur le token clair) : toute altération du cookie
  ne correspond à aucun hash => 401 identique (T-12) ;
- expiration ``expires_at = now + SESSION_LIFETIME_HOURS`` (Settings) ;
- révocation ``revoked_at`` : déconnexion et changement de mot de passe
  (spec §8, T-10/T-11).

Le jeton CSRF de la session est haché de la même façon
(``csrf_token_hash``, D-05) — voir ``app.security.csrf``.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.models import Session

# Entropie : 256 bits (spec §8 ; T-20 : entropie >= 256 bits).
SESSION_TOKEN_HEX_CHARS = 32
CSRF_TOKEN_URLSAFE_CHARS = 32


def hash_token(token: str) -> str:
    """SHA-256 (64 caractères hexadécimaux) d'un token en clair.

    Fonction de hachage **non salée** : le token est à haute entropie
    (256 bits), le salt n'apporte rien et le hash doit être reproductible
    pour la comparaison (sessions et CSRF, D-05).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    """Token de session opaque : 256 bits aléatoires (hex, 64 caractères)."""
    return secrets.token_hex(SESSION_TOKEN_HEX_CHARS)


def new_csrf_token() -> str:
    """Jeton CSRF : 256 bits aléatoires, encodage URL-safe (D-05)."""
    return secrets.token_urlsafe(CSRF_TOKEN_URLSAFE_CHARS)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_session(db: DbSession, user_id: uuid.UUID, settings: Settings) -> tuple[Session, str]:
    """Crée une session pour ``user_id`` et renvoie ``(ligne, token en clair)``.

    Le token en clair n'est stocké nulle part : il est renvoyé une fois
    pour être posé en cookie (D-04). ``csrf_token_hash`` est initialisé
    avec un jeton non exposé — le premier ``GET /auth/csrf`` le remplace
    par rotation (``rotate_csrf_token``) et seul ce jeton est servi.
    """
    token = new_session_token()
    session = Session(
        user_id=user_id,
        token_hash=hash_token(token),
        csrf_token_hash=hash_token(new_csrf_token()),
        expires_at=_utcnow() + timedelta(hours=settings.SESSION_LIFETIME_HOURS),
    )
    db.add(session)
    db.flush()
    return session, token


def lookup_active_session(db: DbSession, token: str) -> Session | None:
    """Recherche une session **valide** par le hash du token du cookie.

    Retourne ``None`` si : token inconnu, session révoquée ou session
    expirée — les trois états sont indiscernables pour l'appelant
    (401 ``UNAUTHENTICATED``, T-12/T-13, D-17 : compte suspendu =
    « non connecté »).
    """
    row = (
        db.query(Session).filter(Session.token_hash == hash_token(token)).one_or_none()
    )
    if row is None:
        return None
    if row.revoked_at is not None or row.expires_at <= _utcnow():
        return None
    return row


def revoke_session(db: DbSession, session: Session) -> None:
    """Révoque une session (``revoked_at = now``) — idempotent."""
    if session.revoked_at is None:
        session.revoked_at = _utcnow()
        db.flush()


def revoke_user_sessions(db: DbSession, user_id: uuid.UUID) -> int:
    """Révoque **toutes** les sessions de l'utilisateur (spec §8 :
    révocation au changement de mot de passe, T-11). Renvoie le nombre
    de sessions révoquées (0 si aucune active)."""
    result = db.execute(
        update(Session)
        .where(Session.user_id == user_id, Session.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
    )
    return result.rowcount or 0


def rotate_csrf_token(db: DbSession, session: Session) -> str:
    """Émet un nouveau jeton CSRF pour la session (rotation, D-05).

    Le hash est remplacé dans ``sessions.csrf_token_hash`` : le jeton
    précédent cesse d'être valide. Seul le hash est persisté ; le jeton
    en clair n'existe que dans la réponse ``GET /auth/csrf``.
    """
    token = new_csrf_token()
    session.csrf_token_hash = hash_token(token)
    db.flush()
    return token


__all__ = [
    "CSRF_TOKEN_URLSAFE_CHARS",
    "SESSION_TOKEN_HEX_CHARS",
    "create_session",
    "hash_token",
    "lookup_active_session",
    "new_csrf_token",
    "new_session_token",
    "revoke_session",
    "revoke_user_sessions",
    "rotate_csrf_token",
]
