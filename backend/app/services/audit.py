"""Journal d'audit append-only (spec §4 « Historique », T-48, F18).

Garanties applicatives :

- **INSERT uniquement** : aucune API de modification ni de suppression
  d'un ``AuditEvent`` (pas de ``record(...)`` de mise à jour ; les routes
  de la spec §6 n'exposent jamais d'écriture directe sur ``audit_events``) ;
- ``actor_id`` est **dérivé de la session** (jamais du body, T-48) ;
  nullable : un échec de login sur e-mail inconnu n'a pas d'acteur
  (migration 0002, issue #5) ;
- ``request_id`` relie l'événement au middleware X-Request-ID (D-06) ;
- **métadonnées non sensibles** (F18, T-47) : IDs, statuts, e-mail
  normalisé — **jamais de mot de passe, ni de token, ni de payload**
  (vérifié par le test F18 sur ``metadata_json``).

Les actions normatives de l'issue #5 sont des constantes nommées ici
(``A_*``) pour interdire l'écriture de chaînes libres dans les services.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.models import AuditEvent

# --- Actions (issue #5) ------------------------------------------------------
A_LOGIN_SUCCESS: str = "login.success"
A_LOGIN_FAILURE: str = "login.failure"
A_LOGOUT: str = "logout"
A_PASSWORD_RESET_REQUESTED: str = "password.reset_requested"
A_PASSWORD_RESET: str = "password.reset"
A_PLATFORM_ADMIN_CREATED: str = "platform_admin.created"
A_PLATFORM_ADMIN_EXISTING: str = "platform_admin.existing"

# --- Actions (issue #7, plateforme) -------------------------------------------
A_PLATFORM_TENANT_CREATED: str = "platform.tenant.created"
A_PLATFORM_TENANT_SUSPENDED: str = "platform.tenant.suspended"
A_PLATFORM_TENANT_REACTIVATED: str = "platform.tenant.reactivated"

# --- Types d'entité ----------------------------------------------------------
ENTITY_USER: str = "user"
ENTITY_SESSION: str = "session"
ENTITY_PASSWORD_RESET_TOKEN: str = "password_reset_token"
ENTITY_PLATFORM_ADMIN: str = "platform_admin"
ENTITY_TENANT: str = "tenant"


@dataclass
class AuditContext:
    """Contexte de journalisation d'une opération (session de base +
    request ID ; l'acteur et le tenant sont renseignés au besoin)."""

    db: DbSession
    request_id: str | None = None
    actor_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None


def record(
    context: AuditContext,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Crée un ``AuditEvent`` (INSERT) dans la transaction courante.

    Le commit est le fait de l'appelant (unité de travail explicite) ;
    ``metadata`` doit être non sensible (F18) — la fonction ne filtre
    pas, elle documente le contrat.
    """
    event = AuditEvent(
        tenant_id=context.tenant_id,
        actor_id=context.actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=dict(metadata or {}),
        request_id=context.request_id,
    )
    context.db.add(event)
    return event


__all__ = [
    "A_LOGIN_FAILURE",
    "A_LOGIN_SUCCESS",
    "A_LOGOUT",
    "A_PASSWORD_RESET",
    "A_PASSWORD_RESET_REQUESTED",
    "A_PLATFORM_ADMIN_CREATED",
    "A_PLATFORM_ADMIN_EXISTING",
    "A_PLATFORM_TENANT_CREATED",
    "A_PLATFORM_TENANT_REACTIVATED",
    "A_PLATFORM_TENANT_SUSPENDED",
    "AuditContext",
    "ENTITY_PASSWORD_RESET_TOKEN",
    "ENTITY_PLATFORM_ADMIN",
    "ENTITY_SESSION",
    "ENTITY_TENANT",
    "ENTITY_USER",
    "record",
]
