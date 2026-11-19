"""Énumérations du domaine (spec §1, §4, §5).

Les valeurs stockées en base sont les NOMS des membres (majuscules),
identiques dans les modèles ORM et dans la migration initiale.
"""
from __future__ import annotations

from enum import Enum


class TenantMembershipRole(str, Enum):
    """Rôles du cabinet, stockés dans `tenant_memberships` (spec §1)."""

    TENANT_ADMIN = "TENANT_ADMIN"
    PENTESTER = "PENTESTER"


class ClientMembershipRole(str, Enum):
    """Rôle client, stocké dans `client_memberships` (spec §1)."""

    CLIENT_VIEWER = "CLIENT_VIEWER"


class InvitationRole(str, Enum):
    """Rôle attribué à l'acceptation d'une invitation (spec §3.3)."""

    TENANT_ADMIN = "TENANT_ADMIN"
    PENTESTER = "PENTESTER"
    CLIENT_VIEWER = "CLIENT_VIEWER"


class EngagementStatus(str, Enum):
    """Cycle de vie d'une mission (spec §4)."""

    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class AssetType(str, Enum):
    """Types d'actifs (spec §4)."""

    WEB = "WEB"
    SERVER = "SERVER"
    DATABASE = "DATABASE"
    WORKSTATION = "WORKSTATION"
    OTHER = "OTHER"


class FindingSeverity(str, Enum):
    """Sévérité d'un constat (spec §4)."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, Enum):
    """Statut d'un constat (spec §4). `REMEDIATED` invalide les chemins qui
    s'appuient sur lui ; `ACCEPTED_RISK` reste exploitable dans le calcul."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    REMEDIATED = "REMEDIATED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
