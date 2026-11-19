"""Schémas des routes d'authentification (spec §6, D-04/D-05/D-17 — issue #5).

Les schémas d'écriture interdisent les champs inattendus
(``extra="forbid"``, T-45) : aucun ``tenant_id``/``role``/jeton ne peut
être injecté depuis le body.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Body de ``POST /auth/reset-password`` (issue #5).

    La confirmation doit répéter le mot de passe : en cas de divergence,
    422 (contrat issue #5) — avant toute vérification du token, donc sans
    information exploitable sur l'état du compte.
    """

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    password_confirmation: str = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def _confirmations_must_match(self) -> "ResetPasswordRequest":
        if self.password != self.password_confirmation:
            raise ValueError("La confirmation ne correspond pas au mot de passe.")
        return self


class TenantMembershipOut(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    slug: str
    role: str


class ClientMembershipOut(BaseModel):
    client_org_id: uuid.UUID
    client_org_name: str
    tenant_id: uuid.UUID


class AuthMe(BaseModel):
    """Contrat figé D-17 de ``GET /auth/me`` (identique pour le login).

    Arrays ``[]`` si vides (jamais ``null``) ; ``platform_admin`` booléen ;
    aucune donnée sensible (hash, storage_key, token).
    """

    id: uuid.UUID
    email: str
    is_active: bool
    platform_admin: bool
    tenant_memberships: list[TenantMembershipOut]
    client_memberships: list[ClientMembershipOut]


class CsrfResponse(BaseModel):
    csrf_token: str = Field(min_length=1)


__all__ = [
    "AuthMe",
    "ClientMembershipOut",
    "CsrfResponse",
    "ForgotPasswordRequest",
    "LoginRequest",
    "ResetPasswordRequest",
    "TenantMembershipOut",
]
