"""Service d'authentification (issue #5, spec §3 flux 1/4, §6, §8).

Règles implémentées :

- login : e-mail normalisé (lower + trim), verify Argon2id, **verify
  fantôme** sur hash canard si e-mail inconnu (délai de calcul identique,
  T-21/D-07), 401 ``INVALID_CREDENTIALS`` générique (DESIGN P1), audit
  succès/échec (acteur nul si e-mail inconnu — migration 0002) ;
- logout : révocation de la session + audit ;
- forgot_password : réponse **identique** (200 neutre) que le compte
  existe ou non (T-21) ; token reset 30 min (Settings) créé uniquement
  si l'utilisateur existe et est actif ; e-mail via ``app.security.email`` ;
- reset_password : token usage unique (consommation atomique, T-18),
  politique mot de passe (422), nouveau hash Argon2id, **révocation de
  toutes les sessions** de l'utilisateur (T-11), audit ;
- F18 : aucun mot de passe ni token dans les métadonnées d'audit.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.exceptions import ApiError, ErrorCode
from app.models import (
    ClientMembership,
    ClientOrg,
    PasswordResetToken,
    Session,
    Tenant,
    TenantMembership,
    User,
)
from app.security import email as email_security
from app.security import sessions as session_security
from app.security.passwords import (
    dummy_password_hash,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.security.rate_limit import (
    KEY_FORGOT_PASSWORD,
    KEY_LOGIN,
    KEY_RESET_PASSWORD,
    build_key,
    get_rate_limiter,
)
from app.services.audit import (
    A_LOGOUT,
    A_LOGIN_FAILURE,
    A_LOGIN_SUCCESS,
    A_PASSWORD_RESET,
    A_PASSWORD_RESET_REQUESTED,
    AuditContext,
    ENTITY_PASSWORD_RESET_TOKEN,
    ENTITY_SESSION,
    ENTITY_USER,
    record,
)

# --- Messages publics (DESIGN P1 §1.5 : jamais de révélation d'existence) ---
MSG_INVALID_CREDENTIALS = "E-mail ou mot de passe incorrect."
MSG_FORGOT_OK = (
    "Si un compte existe pour cette adresse, un e-mail de réinitialisation a été envoyé."
)
MSG_RESET_OK = "Mot de passe réinitialisé. Vous pouvez vous connecter."
# T-19 : expiré, consommé, inconnu ou compte suspendu => même réponse 400.
MSG_INVALID_RESET_LINK = "Lien de réinitialisation invalide ou expiré."

RESET_EMAIL_SUBJECT = "Réinitialisation de mot de passe — ChainScope"

# Entropie reset : 256 bits, encodage URL-safe (T-20 ; cf. sessions.py).
RESET_TOKEN_URLSAFE_CHARS = 32


@dataclass
class LoginResult:
    """Résultat d'un login réussi : user, ligne de session, token en clair
    (à poser en cookie — D-04) et payload D-17 prêt à sérialiser."""

    user: User
    session: Session
    session_token: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(raw: str) -> str:
    """Normalisation contractuelle : minuscules + espaces extrêmes retirés."""
    return raw.strip().lower()


def _lookup_user_by_email(db: DbSession, email_normalized: str) -> User | None:
    """Recherche insensible à la casse (index fonctionnel ``lower(email)``)."""
    stmt = select(User).where(func.lower(User.email) == email_normalized)
    return db.execute(stmt).scalar_one_or_none()


def _reject_if_rate_limited(key: str) -> None:
    limiter = get_rate_limiter()
    if not limiter.allow(key):
        raise ApiError.rate_limited(retry_after=limiter.retry_after(key))


def login(
    db: DbSession,
    context: AuditContext,
    *,
    email: str,
    password: str,
    client_ip: str,
) -> LoginResult:
    """Connexion (spec §6 ``POST /auth/login``).

    Le même 401 ``INVALID_CREDENTIALS`` est renvoyé pour : e-mail inconnu,
    mot de passe erroné, compte suspendu (T-21 : aucune fuite d'existence).
    """
    settings = get_settings()
    email_norm = normalize_email(email)
    _reject_if_rate_limited(build_key(KEY_LOGIN, email_norm, client_ip))

    user = _lookup_user_by_email(db, email_norm)
    if user is None:
        # Verify « fantôme » (T-21, D-07) : délai de calcul identique à un
        # verify réel — le compte ne peut pas être sondé par le timing.
        verify_password(password, dummy_password_hash())
        record(
            context,
            action=A_LOGIN_FAILURE,
            entity_type=ENTITY_USER,
            metadata={"email_normalise": email_norm},
        )
        db.commit()
        raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, MSG_INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash) or not user.is_active:
        context.actor_id = user.id
        record(
            context,
            action=A_LOGIN_FAILURE,
            entity_type=ENTITY_USER,
            entity_id=user.id,
            metadata={"email_normalise": email_norm},
        )
        db.commit()
        raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, MSG_INVALID_CREDENTIALS)

    session, session_token = session_security.create_session(db, user.id, settings)
    context.actor_id = user.id
    record(
        context,
        action=A_LOGIN_SUCCESS,
        entity_type=ENTITY_USER,
        entity_id=user.id,
        metadata={"email_normalise": email_norm},
    )
    db.commit()
    return LoginResult(user=user, session=session, session_token=session_token)


def logout(
    db: DbSession,
    context: AuditContext,
    *,
    session: Session,
    user: User,
) -> None:
    """Déconnexion : révocation de la session courante + audit (T-10)."""
    session_security.revoke_session(db, session)
    record(
        context,
        action=A_LOGOUT,
        entity_type=ENTITY_SESSION,
        entity_id=session.id,
        metadata={"email_normalise": user.email},
    )
    db.commit()


def me_payload(db: DbSession, user: User) -> dict:
    """Payload du contrat D-17 (``GET /auth/me`` et ``POST /auth/login``).

    Clés exactes ; arrays vides ``[]`` (jamais ``null``) ; ``platform_admin``
    booléen (présence dans ``platform_admins``) ; ordres déterministes
    (noms) pour une navigation stable côté client.
    """
    tenant_rows = db.execute(
        select(TenantMembership, Tenant)
        .join(Tenant, Tenant.id == TenantMembership.tenant_id)
        .where(TenantMembership.user_id == user.id)
        .order_by(Tenant.name)
    ).all()
    client_rows = db.execute(
        select(ClientMembership, ClientOrg, Tenant)
        .join(ClientOrg, ClientOrg.id == ClientMembership.client_org_id)
        .join(Tenant, Tenant.id == ClientOrg.tenant_id)
        .where(ClientMembership.user_id == user.id)
        .order_by(ClientOrg.name)
    ).all()
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "platform_admin": user.platform_admin is not None,
        "tenant_memberships": [
            {
                "tenant_id": tenant.id,
                "tenant_name": tenant.name,
                "slug": tenant.slug,
                "role": membership.role.value,
            }
            for membership, tenant in tenant_rows
        ],
        "client_memberships": [
            {
                "client_org_id": client_org.id,
                "client_org_name": client_org.name,
                "tenant_id": tenant.id,
            }
            for _membership, client_org, tenant in client_rows
        ],
    }


def forgot_password(
    db: DbSession,
    context: AuditContext,
    *,
    email: str,
    client_ip: str,
) -> None:
    """Demande de réinitialisation (T-21, T-25, D-12).

    Réponse toujours neutre : aucun effet observable ne distingue « compte
    inconnu » de « compte actif » (pas d'e-mail, pas d'audit, pas de token
    si le compte est inconnu ou suspendu). Les tokens reset antérieurs non
    consommés sont clôturés à chaque émission (T-25 : pas d'accumulation).
    """
    settings = get_settings()
    email_norm = normalize_email(email)
    _reject_if_rate_limited(build_key(KEY_FORGOT_PASSWORD, email_norm, client_ip))

    user = _lookup_user_by_email(db, email_norm)
    if user is None or not user.is_active:
        return

    now = _utcnow()
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    token = secrets.token_urlsafe(RESET_TOKEN_URLSAFE_CHARS)
    token_row = PasswordResetToken(
        user_id=user.id,
        token_hash=session_security.hash_token(token),
        expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_LIFETIME_MINUTES),
    )
    db.add(token_row)
    db.flush()
    context.actor_id = user.id
    record(
        context,
        action=A_PASSWORD_RESET_REQUESTED,
        entity_type=ENTITY_PASSWORD_RESET_TOKEN,
        entity_id=token_row.id,
        metadata={"email_normalise": user.email},
    )
    db.commit()
    _send_reset_email(user.email, token, settings.PASSWORD_RESET_LIFETIME_MINUTES)


def _send_reset_email(to_email: str, token: str, lifetime_minutes: int) -> None:
    """Corps de l'e-mail de réinitialisation : lien complet (D-12) — le
    token brut n'existe que dans ce canal (F18/T-23)."""
    link = email_security.build_reset_link(token)
    body = (
        "Bonjour,\n\n"
        f"Un lien de réinitialisation de mot de passe a été demandé pour le compte {to_email}.\n\n"
        f"Lien : {link}\n\n"
        f"Ce lien est valable {lifetime_minutes} minutes et à usage unique. "
        "Après la réinitialisation, toutes vos sessions seront déconnectées.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail : "
        "aucun changement ne sera effectué.\n\n"
        "L'équipe ChainScope"
    )
    email_security.send_email(
        to=to_email, subject=RESET_EMAIL_SUBJECT, body=body, token=token
    )


def reset_password(
    db: DbSession,
    context: AuditContext,
    *,
    token: str,
    new_password: str,
    client_ip: str,
) -> None:
    """Réinitialisation (T-18 usage unique, T-19 expiration, T-11 sessions).

    - politique mot de passe d'abord : 422 message unique (anti-oracle) ;
    - token inconnu/expiré/consommé/compte suspendu : 400 générique
      identique (aucun détail distinctif) ;
    - succès : consommation **atomique** (UPDATE WHERE consumed_at IS NULL),
      nouveau hash, révocation de toutes les sessions, audit.
    """
    _reject_if_rate_limited(build_key(KEY_RESET_PASSWORD, client_ip))

    policy_error = validate_password_policy(new_password)
    if policy_error is not None:
        raise ApiError(422, ErrorCode.VALIDATION, policy_error)

    now = _utcnow()
    token_hash = session_security.hash_token(token)
    token_row = (
        db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        .scalar_one_or_none()
    )
    if (
        token_row is None
        or token_row.consumed_at is not None
        or token_row.expires_at <= now
    ):
        raise ApiError(400, ErrorCode.INVALID_TOKEN, MSG_INVALID_RESET_LINK)

    user = db.get(User, token_row.user_id)
    if user is None or not user.is_active:
        raise ApiError(400, ErrorCode.INVALID_TOKEN, MSG_INVALID_RESET_LINK)

    # Consommation atomique (course T-18) : si le token a été consommé entre
    # le SELECT ci-dessus et cet UPDATE, rowcount == 0 => refus générique.
    result = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.id == token_row.id,
            PasswordResetToken.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    if not result.rowcount:
        raise ApiError(400, ErrorCode.INVALID_TOKEN, MSG_INVALID_RESET_LINK)

    user.password_hash = hash_password(new_password)
    session_security.revoke_user_sessions(db, user.id)
    context.actor_id = user.id
    record(
        context,
        action=A_PASSWORD_RESET,
        entity_type=ENTITY_USER,
        entity_id=user.id,
        metadata={"email_normalise": user.email},
    )
    db.commit()


__all__ = [
    "LoginResult",
    "MSG_FORGOT_OK",
    "MSG_INVALID_CREDENTIALS",
    "MSG_INVALID_RESET_LINK",
    "MSG_RESET_OK",
    "RESET_EMAIL_SUBJECT",
    "forgot_password",
    "login",
    "logout",
    "me_payload",
    "normalize_email",
    "reset_password",
]
