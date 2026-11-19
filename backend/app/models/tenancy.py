"""Frontière tenant : cabinets, membres, entreprises clientes (spec §5).

`tenants`, `tenant_memberships`, `client_orgs`, `client_memberships`.
Le tenant est la frontière principale d'isolation (spec §1) : les tables
portant `tenant_id` s'appuient sur des clés étrangères composites
(spéc §5, « lorsque praticable ») pour interdire les références cross-tenant.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Uuid,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ClientMembershipRole, TenantMembershipRole

if TYPE_CHECKING:
    from app.models.audit import AuditEvent
    from app.models.auth_tokens import Invitation
    from app.models.engagements import Engagement
    from app.models.users import User


class Tenant(Base):
    """Cabinet de pentest (tenant)."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    # Issue #7 : le contrat de lecture/création plateforme exige `created_at`
    # (spéc §5 se contentait de id/name/slug/is_active — écart documenté).
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- relations ---
    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")
    client_orgs: Mapped[list["ClientOrg"]] = relationship(back_populates="tenant")
    engagements: Mapped[list["Engagement"]] = relationship(back_populates="tenant")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="tenant")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="tenant")


class TenantMembership(Base):
    """Appartenance d'un user à un cabinet + rôle (spec §1)."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_tenant_memberships_user_tenant"),
        Index("ix_tenant_memberships_user_id", "user_id"),
        Index("ix_tenant_memberships_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_tenant_memberships_user"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", name="fk_tenant_memberships_tenant"), nullable=False
    )
    role: Mapped[TenantMembershipRole] = mapped_column(
        Enum(TenantMembershipRole, name="tenant_membership_role"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="tenant_memberships")
    tenant: Mapped[Tenant] = relationship(back_populates="memberships")


class ClientOrg(Base):
    """Entreprise auditée, rattachée à un seul tenant (spec §1)."""

    __tablename__ = "client_orgs"
    __table_args__ = (
        # Cible des FK composites des engagements (cohérence tenant, spec §5).
        UniqueConstraint("tenant_id", "id", name="uq_client_orgs_tenant_id"),
        Index("ix_client_orgs_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", name="fk_client_orgs_tenant"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # --- relations ---
    tenant: Mapped[Tenant] = relationship(back_populates="client_orgs")
    memberships: Mapped[list["ClientMembership"]] = relationship(
        back_populates="client_org"
    )
    engagements: Mapped[list["Engagement"]] = relationship(
        back_populates="client_org", overlaps="engagements"
    )
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="client_org")


class ClientMembership(Base):
    """Appartenance d'un user à une entreprise cliente + rôle (spec §1)."""

    __tablename__ = "client_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "client_org_id", name="uq_client_memberships_user_org"),
        Index("ix_client_memberships_user_id", "user_id"),
        Index("ix_client_memberships_client_org_id", "client_org_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_client_memberships_user"), nullable=False
    )
    client_org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client_orgs.id", name="fk_client_memberships_client_org"),
        nullable=False,
    )
    role: Mapped[ClientMembershipRole] = mapped_column(
        Enum(ClientMembershipRole, name="client_membership_role"), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="client_memberships")
    client_org: Mapped[ClientOrg] = relationship(back_populates="memberships")
