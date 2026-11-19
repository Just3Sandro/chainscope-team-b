"""Service plateforme (issue #7, spec §1/§6 : ``/platform/tenants``).

Règles :

- **Pas de lecture métier** (spec §1 ; THREAT_MODEL T-05) : seule la fiche
  tenant (id, nom, slug, état, date de création) et des **compteurs
  agrégés** (``SELECT COUNT``) sont renvoyés — jamais de findings,
  actifs, preuves, noms de clients ;
- ``member_count`` minimal (nombre de ``tenant_memberships``) ; les
  agrégats avancés de l'écran d'administration plateforme sont l'objet de
  l'issue #27 (P2, hors contrat spec §6) ;
- création de tenant (transaction unique) : ``is_active=true``,
  ``slug`` unique (409 ``CONFLICT`` sinon), invitation ``TENANT_ADMIN``
  de l'administrateur (spec §3 flux 2) — token 256 bits, **haché** en
  base (SHA-256, spec §8), expiration ``INVITATION_LIFETIME_HOURS`` ;
- e-mail d'invitation via le transport ``app.security.email`` (D-12) :
  expédié **après commit**, comme le reset de mot de passe (issue #5) —
  le token brut n'existe que dans ce canal (F18/T-23) ;
- F18/T-47 : l'audit ne porte que des métadonnées non sensibles
  (slug, e-mail normalisé, état) — jamais de token d'invitation.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.config import get_settings
from app.exceptions import ApiError
from app.models import (
    ClientOrg,
    Engagement,
    Invitation,
    InvitationRole,
    Tenant,
    TenantMembership,
)
from app.security import email as email_security
from app.security import sessions as session_security
from app.services import auth_service
from app.services.audit import (
    A_PLATFORM_TENANT_CREATED,
    A_PLATFORM_TENANT_REACTIVATED,
    A_PLATFORM_TENANT_SUSPENDED,
    AuditContext,
    ENTITY_TENANT,
    record,
)

# Entropie invitation : 256 bits, encodage URL-safe (T-20, même règle que
# les tokens reset/sessions — cf. ``RESET_TOKEN_URLSAFE_CHARS``).
INVITATION_TOKEN_URLSAFE_CHARS = 32

INVITATION_EMAIL_SUBJECT = "Invitation ChainScope — administrateur de cabinet"

MSG_SLUG_TAKEN = "Un tenant avec ce slug existe déjà."


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _count_subquery(model, tenant_key):
    """Compteur agrégé lecture seule (sous-requête scalaire) corrélé au
    tenant courant de la requête parente."""
    return (
        select(func.count(model.id))
        .where(tenant_key == Tenant.id)
        .correlate(Tenant)
        .scalar_subquery()
    )


def list_tenants(db: DbSession, *, limit: int, offset: int) -> tuple[list[dict], int]:
    """Page de tenants (D-11) + total.

    Chaque item ne porte que la fiche tenant et les compteurs agrégés
    (``member_count`` / ``client_org_count`` / ``engagement_count``) —
    aucune donnée métier (spec §1, THREAT_MODEL T-05). Tri déterministe
    (nom puis id) pour une pagination stable.
    """
    member_sq = _count_subquery(TenantMembership, TenantMembership.tenant_id)
    client_sq = _count_subquery(ClientOrg, ClientOrg.tenant_id)
    engagement_sq = _count_subquery(Engagement, Engagement.tenant_id)

    total = db.execute(select(func.count()).select_from(Tenant)).scalar_one()
    rows = db.execute(
        select(Tenant, member_sq, client_sq, engagement_sq)
        .order_by(Tenant.name, Tenant.id)
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "is_active": tenant.is_active,
            "created_at": tenant.created_at,
            "member_count": member_count,
            "client_org_count": client_count,
            "engagement_count": engagement_count,
        }
        for tenant, member_count, client_count, engagement_count in rows
    ]
    return items, total


def create_tenant(
    db: DbSession,
    context: AuditContext,
    *,
    name: str,
    slug: str,
    admin_email: str,
) -> Tenant:
    """Crée le tenant (``is_active=true``) **et** l'invitation
    ``TENANT_ADMIN`` pour ``admin_email`` (spec §3 flux 2).

    - ``slug`` existant => 409 ``CONFLICT`` (avant tout écrit) ;
    - tenant + invitation + audit dans la **même transaction** ;
    - e-mail expédié après commit (D-12 ; même ordre que le reset,
      issue #5) : en cas d'échec du transport, le tenant existe avec son
      invitation — le superadministrateur peut retenter l'invitation via
      le flux cabinet dès l'issue #6 (effet de bord documenté, PR #7).
    """
    settings = get_settings()
    if (
        db.execute(select(Tenant.id).where(Tenant.slug == slug)).first()
        is not None
    ):
        raise ApiError.conflict(MSG_SLUG_TAKEN)

    email_norm = auth_service.normalize_email(admin_email)
    tenant = Tenant(name=name, slug=slug, is_active=True)
    db.add(tenant)
    db.flush()

    token = secrets.token_urlsafe(INVITATION_TOKEN_URLSAFE_CHARS)
    db.add(
        Invitation(
            email=email_norm,
            token_hash=session_security.hash_token(token),
            tenant_id=tenant.id,
            role=InvitationRole.TENANT_ADMIN,
            expires_at=_utcnow()
            + timedelta(hours=settings.INVITATION_LIFETIME_HOURS),
        )
    )
    record(
        context,
        action=A_PLATFORM_TENANT_CREATED,
        entity_type=ENTITY_TENANT,
        entity_id=tenant.id,
        metadata={"slug": slug, "admin_email": email_norm},
    )
    db.commit()
    db.refresh(tenant)
    _send_tenant_admin_email(tenant.name, email_norm, token, settings)
    return tenant


def _send_tenant_admin_email(
    tenant_name: str, admin_email: str, token: str, settings
) -> None:
    """Corps de l'invitation : lien complet vers la route frontend
    ``/invite`` (D-12) — le token brut n'existe que dans cet e-mail."""
    link = f"{settings.PUBLIC_BASE_URL}/invite?token={token}"
    body = (
        "Bonjour,\n\n"
        f"Le cabinet « {tenant_name} » a été créé sur ChainScope et vous y êtes"
        " invité en tant qu'administrateur.\n\n"
        f"Lien d'invitation : {link}\n\n"
        f"Ce lien est valable {settings.INVITATION_LIFETIME_HOURS} heures "
        "et à usage unique. Pour accéder à votre espace, définissez un "
        "mot de passe à l'ouverture du lien.\n\n"
        "L'équipe ChainScope"
    )
    email_security.send_email(
        to=admin_email, subject=INVITATION_EMAIL_SUBJECT, body=body, token=token
    )


def set_tenant_active(
    db: DbSession,
    context: AuditContext,
    *,
    tenant_id: uuid.UUID,
    is_active: bool,
) -> Tenant:
    """Suspend (``is_active=false``) ou réactive un tenant (issue #7).

    - tenant inconnu => 404 ``NOT_FOUND`` ;
    - valeur inchangée => 200 sans effet, **sans audit** (idempotence
      documentée) ;
    - changement d'état => audit ``platform.tenant.suspended`` /
      ``platform.tenant.reactivated`` (F18 : métadonnées sans secret).
    """
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise ApiError.not_found()
    if tenant.is_active is is_active:
        return tenant

    tenant.is_active = is_active
    action = (
        A_PLATFORM_TENANT_REACTIVATED if is_active else A_PLATFORM_TENANT_SUSPENDED
    )
    record(
        context,
        action=action,
        entity_type=ENTITY_TENANT,
        entity_id=tenant.id,
        metadata={"slug": tenant.slug, "is_active": is_active},
    )
    db.commit()
    return tenant


__all__ = [
    "INVITATION_EMAIL_SUBJECT",
    "create_tenant",
    "list_tenants",
    "set_tenant_active",
]
