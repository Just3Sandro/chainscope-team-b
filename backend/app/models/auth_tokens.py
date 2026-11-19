"""Jetons d'authentification (spec §5 : `sessions`, `invitations`,
`password_reset_tokens`).

Tous les secrets (token de session, token CSRF, tokens d'invitation et de
réinitialisation) sont stockés hachés (SHA-256, 64 caractères hexadécimaux) ;
les valeurs claires ne transitent que via la route correspondante (spec §8).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import InvitationRole

if TYPE_CHECKING:
    from app.models.tenancy import ClientOrg, Tenant
    from app.models.users import User


class Session(Base):
    """Session opaque côté serveur (spec §8 : révocation déconnexion/changement
    de mot de passe) ; `token_hash` indexe la session, `expires_at` sa durée."""

    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_sessions_user"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class Invitation(Base):
    """Invitation à durée limitée, usage unique (spec §3.3, §8).

    Rattachement au cabinet (rôles tenant) OU à une entreprise cliente
    (rôle client) — exactement l'un des deux selon le rôle ; contrôle en
    service (la contrainte de non-null d'un des deux n'est pas exprimable
    en FK simple).
    """

    __tablename__ = "invitations"
    __table_args__ = (Index("ix_invitations_tenant_id", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", name="fk_invitations_tenant"), nullable=True
    )
    client_org_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("client_orgs.id", name="fk_invitations_client_org"), nullable=True
    )
    role: Mapped[InvitationRole] = mapped_column(
        Enum(InvitationRole, name="invitation_role"), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tenant: Mapped[Tenant | None] = relationship(back_populates="invitations")
    client_org: Mapped[ClientOrg | None] = relationship(
        back_populates="invitations"
    )


class PasswordResetToken(Base):
    """Lien de réinitialisation à usage unique et à expiration courte (spec §3.4)."""

    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_user_id", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_password_reset_tokens_user"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")
