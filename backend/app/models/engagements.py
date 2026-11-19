"""Missions, actifs, constats et relations du graphe (spec §5 : 4 tables).

`engagements`, `assets`, `findings`, `attack_edges`.
Cohérence tenant/engagement garantie en base par FK composites (spec §5,
« lorsque praticable ») et par les CHECK de domaine (CVSS 0–10, criticité 1–5).
Ordre des classes : les relations à FK composites précisent `foreign_keys`
du côté où la colonne est locale (classe définie avant le partenaire).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (
    CRITICALITY_DEFAULT,
    CRITICALITY_MAX,
    CRITICALITY_MIN,
    CVSS_MAX,
    CVSS_MIN,
)
from app.models.base import Base
from app.models.evidences import Evidence
from app.models.enums import (
    AssetType,
    EngagementStatus,
    FindingSeverity,
    FindingStatus,
)
from app.models.tenancy import ClientOrg, Tenant
from app.models.users import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    """Actif du graphe (spec §4) : position x/y persistée côté serveur.

    FK composite (tenant_id, engagement_id) => engagements(tenant_id, id) :
    interdit en base tout actif rattaché à un engagement d'un autre tenant.
    """

    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_assets_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_assets_tenant_engagement",
        ),
        CheckConstraint(
            f"criticality >= {CRITICALITY_MIN} AND criticality <= {CRITICALITY_MAX}",
            name="ck_assets_criticality_range",
        ),
        Index("ix_assets_tenant_id", "tenant_id"),
        Index("ix_assets_engagement_id", "engagement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    engagement_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_entry_point: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_crown_jewel: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    criticality: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=CRITICALITY_DEFAULT,
        server_default=text(str(CRITICALITY_DEFAULT)),
    )
    x: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0")
    )
    y: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default=text("0")
    )

    # --- relations ---
    engagement: Mapped["Engagement"] = relationship(
        back_populates="assets", foreign_keys=[engagement_id]
    )
    # Deux FK composites lient assets <-> attack_edges (source ET cible) :
    # le primaryjoin explicite lève l'ambiguité (côté "many" défini ensuite).
    edges_out: Mapped[list["AttackEdge"]] = relationship(
        back_populates="source_asset",
        primaryjoin="AttackEdge.source_asset_id == Asset.id",
    )
    edges_in: Mapped[list["AttackEdge"]] = relationship(
        back_populates="target_asset",
        primaryjoin="AttackEdge.target_asset_id == Asset.id",
    )


class Finding(Base):
    """Constat de vulnérabilité (spec §4 : champs obligatoires, CVSS 0–10)."""

    __tablename__ = "findings"
    __table_args__ = (
        # Cible des FK composites des `attack_edges` et `evidences`.
        UniqueConstraint(
            "tenant_id", "engagement_id", "id", name="uq_findings_tenant_engagement_id"
        ),
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_findings_tenant_engagement",
        ),
        CheckConstraint(
            f"cvss >= {CVSS_MIN} AND cvss <= {CVSS_MAX}", name="ck_findings_cvss_range"
        ),
        Index("ix_findings_tenant_id", "tenant_id"),
        Index("ix_findings_engagement_id", "engagement_id"),
        Index("ix_findings_engagement_status", "engagement_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    engagement_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    cvss: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, name="finding_status"),
        nullable=False,
        default=FindingStatus.OPEN,
        server_default="OPEN",
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_findings_created_by"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=_utcnow,
    )

    # --- relations ---
    engagement: Mapped["Engagement"] = relationship(
        back_populates="findings", foreign_keys=[engagement_id]
    )
    author: Mapped[User] = relationship(back_populates="findings_created")
    edges: Mapped[list["AttackEdge"]] = relationship(back_populates="finding")
    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="finding", overlaps="engagement"
    )


class AttackEdge(Base):
    """Relation orientée source→cible supportée par un constat (spec §4).

    Source et cible distinctes ; les trois objets appartiennent au même
    engagement et au même tenant (FK composites, spec §5).
    """

    __tablename__ = "attack_edges"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_attack_edges_tenant_engagement",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "source_asset_id"],
            ["assets.tenant_id", "assets.id"],
            name="fk_attack_edges_source_asset",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "target_asset_id"],
            ["assets.tenant_id", "assets.id"],
            name="fk_attack_edges_target_asset",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id", "finding_id"],
            ["findings.tenant_id", "findings.engagement_id", "findings.id"],
            name="fk_attack_edges_finding",
        ),
        UniqueConstraint(
            "source_asset_id", "target_asset_id", "finding_id",
            name="uq_attack_edges_source_target_finding",
        ),
        CheckConstraint(
            "source_asset_id <> target_asset_id",
            name="ck_attack_edges_source_target_distinct",
        ),
        Index("ix_attack_edges_tenant_id", "tenant_id"),
        Index("ix_attack_edges_engagement_id", "engagement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    engagement_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    source_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_asset_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    finding_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)

    # --- relations (foreign_keys explicites : 4 FK composites impliquées) ---
    engagement: Mapped["Engagement"] = relationship(
        back_populates="edges", foreign_keys=[engagement_id], overlaps="edges"
    )
    source_asset: Mapped[Asset] = relationship(
        back_populates="edges_out", foreign_keys=[source_asset_id]
    )
    target_asset: Mapped[Asset] = relationship(
        back_populates="edges_in", foreign_keys=[target_asset_id]
    )
    finding: Mapped[Finding] = relationship(
        back_populates="edges", foreign_keys=[finding_id]
    )


class Engagement(Base):
    """Mission de pentest, rattachée à un client et à son tenant (spec §1).

    Définie en dernier : ses relations to-one utilisent les colonnes des
    classes précédentes (FK composites).
    """

    __tablename__ = "engagements"
    __table_args__ = (
        # Cible des FK composites des tables descendantes (cohérence tenant).
        UniqueConstraint("tenant_id", "id", name="uq_engagements_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "client_org_id"],
            ["client_orgs.tenant_id", "client_orgs.id"],
            name="fk_engagements_tenant_client_org",
        ),
        Index("ix_engagements_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", name="fk_engagements_tenant"), nullable=False
    )
    client_org_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[EngagementStatus] = mapped_column(
        Enum(EngagementStatus, name="engagement_status"),
        nullable=False,
        default=EngagementStatus.DRAFT,
        server_default="DRAFT",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=_utcnow,
    )

    # --- relations ---
    tenant: Mapped[Tenant] = relationship(
        back_populates="engagements", overlaps="engagements"
    )
    client_org: Mapped[ClientOrg] = relationship(
        back_populates="engagements", foreign_keys=[client_org_id]
    )
    assets: Mapped[list[Asset]] = relationship(
        back_populates="engagement", foreign_keys=[Asset.engagement_id]
    )
    findings: Mapped[list[Finding]] = relationship(
        back_populates="engagement", foreign_keys=[Finding.engagement_id]
    )
    edges: Mapped[list[AttackEdge]] = relationship(
        back_populates="engagement",
        foreign_keys=[AttackEdge.engagement_id],
        overlaps="edges",
    )
    evidences: Mapped[list[Evidence]] = relationship(
        back_populates="engagement",
        foreign_keys=[Evidence.engagement_id],
        overlaps="evidences",
    )
