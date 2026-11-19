"""Modèles ORM — les 15 tables de la spec §5 (D-01 : couche `models`).

Tous les modèles sont importés ici pour que `Base.metadata` soit complète
(cible `target_metadata` d'Alembic). L'ordre d'import est sans effet :
les FK sont résolues au registre global.
"""
from __future__ import annotations

from app.models.audit import AuditEvent
from app.models.auth_tokens import Invitation, PasswordResetToken, Session
from app.models.base import Base
from app.models.evidences import Evidence
from app.models.engagements import Asset, AttackEdge, Engagement, Finding
from app.models.enums import (
    AssetType,
    ClientMembershipRole,
    EngagementStatus,
    FindingSeverity,
    FindingStatus,
    InvitationRole,
    TenantMembershipRole,
)
from app.models.tenancy import ClientMembership, ClientOrg, Tenant, TenantMembership
from app.models.users import PlatformAdmin, User

__all__ = [
    "Asset",
    "AssetType",
    "AttackEdge",
    "AuditEvent",
    "Base",
    "ClientMembership",
    "ClientMembershipRole",
    "ClientOrg",
    "Engagement",
    "EngagementStatus",
    "Evidence",
    "Finding",
    "FindingSeverity",
    "FindingStatus",
    "Invitation",
    "InvitationRole",
    "PasswordResetToken",
    "PlatformAdmin",
    "Session",
    "Tenant",
    "TenantMembership",
    "TenantMembershipRole",
    "User",
]
