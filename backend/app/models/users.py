"""Utilisateurs et administrateurs plateforme (spec §5 : `users`, `platform_admins`)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.audit import AuditEvent
    from app.models.auth_tokens import PasswordResetToken, Session
    from app.models.evidences import Evidence
    from app.models.engagements import Finding
    from app.models.tenancy import ClientMembership, TenantMembership


class User(Base):
    """Identité globale (e-mail unique) ; permissions par memberships explicites."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # E-mail unique insensible à la casse (index fonctionnel sur lower(email)).
    __table_args__ = (Index("ix_users_email_lower", func.lower(email), unique=True),)

    # --- relations ---
    platform_admin: Mapped["PlatformAdmin | None"] = relationship(
        back_populates="user", uselist=False
    )
    tenant_memberships: Mapped[list["TenantMembership"]] = relationship(
        back_populates="user"
    )
    client_memberships: Mapped[list["ClientMembership"]] = relationship(
        back_populates="user"
    )
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    findings_created: Mapped[list["Finding"]] = relationship(back_populates="author")
    evidences_created: Mapped[list["Evidence"]] = relationship(back_populates="author")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="actor")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        back_populates="user"
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: object) -> object:
        """Invariant : e-mail normalisé (espaces retirés, minuscules) à l'insertion."""
        if isinstance(value, str):
            return value.strip().lower()
        return value


class PlatformAdmin(Base):
    """Superadministrateur plateforme (spec §1) : une seule ligne par user."""

    __tablename__ = "platform_admins"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name="fk_platform_admins_user"),
        unique=True,
        nullable=False,
    )

    user: Mapped[User] = relationship(
        back_populates="platform_admin", foreign_keys=[user_id]
    )
