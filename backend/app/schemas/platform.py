"""Schémas de la plateforme (issue #7, spec §6 : ``/platform/tenants``).

Écriture — ``extra="forbid"`` (THREAT_MODEL T-45, mass assignment) :
aucun ``role`` / ``tenant_id`` / ``created_at`` ne peut être injecté depuis
le body ; ``is_active`` n'est modifiable que via le PATCH de suspension,
jamais au POST de création (toujours ``true``, spec §5).

Lecture — compteurs agrégés uniquement (``member_count``,
``client_org_count``, ``engagement_count``) : **jamais de données métier**
(findings, actifs, preuves, clients par nom — spec §1, THREAT_MODEL T-05).
Le ``member_count`` minimal est l'objet de l'issue #7 ; les agrégats
avancés de l'écran d'administration plateforme sont suivis par l'issue
#27 (P2, hors contrat spec §6).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

#: Contrat de l'issue #7 : minuscules, chiffres, tirets ; 2–64 caractères.
SLUG_PATTERN: str = r"^[a-z0-9-]{2,64}$"


class TenantCreateRequest(BaseModel):
    """Body de ``POST /platform/tenants`` (issue #7)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=SLUG_PATTERN)
    admin_email: EmailStr

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Le nom du tenant est vide.")
        return stripped


class TenantPatchRequest(BaseModel):
    """Body de ``PATCH /platform/tenants/{tenant_id}`` : ``is_active``
    exigé (le toggle de suspension) — un body vide ou sans ce champ est
    refusé (422). ``extra="forbid"`` : aucun autre champ accepté."""

    model_config = ConfigDict(extra="forbid")

    is_active: bool


class TenantOut(BaseModel):
    """Réponse d'écriture (POST 201 / PATCH 200) — issue #7 :
    ``{ id, name, slug, is_active, created_at }``, sans compteurs."""

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime


class TenantSummary(BaseModel):
    """Item de la liste paginée (GET) : fiche tenant + compteurs agrégés
    lecture seule — aucune donnée métier (spec §1, THREAT_MODEL T-05)."""

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    member_count: int = Field(ge=0, description="Nombre de `tenant_memberships`.")
    client_org_count: int = Field(ge=0, description="Nombre d'entreprises clientes.")
    engagement_count: int = Field(ge=0, description="Nombre de missions.")


__all__ = [
    "SLUG_PATTERN",
    "TenantCreateRequest",
    "TenantOut",
    "TenantPatchRequest",
    "TenantSummary",
]
