"""Preuves (spec §5 : `evidences`).

Le chemin de stockage (`storage_key`) est unique et généré par le serveur
(D-09) ; aucun accès statique au volume (spec §2/§4). FK composites pour la
cohérence tenant/engagement/constat (spec §5).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.engagements import Engagement, Finding
    from app.models.users import User


class Evidence(Base):
    __tablename__ = "evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_evidences_tenant_engagement",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "engagement_id", "finding_id"],
            ["findings.tenant_id", "findings.engagement_id", "findings.id"],
            name="fk_evidences_finding",
        ),
        CheckConstraint("size_bytes >= 0", name="ck_evidences_size_non_negative"),
        Index("ix_evidences_tenant_id", "tenant_id"),
        Index("ix_evidences_engagement_id", "engagement_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    engagement_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    finding_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    client_visible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_evidences_created_by"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- relations ---
    engagement: Mapped[Engagement] = relationship(
        back_populates="evidences", foreign_keys=[engagement_id]
    )
    finding: Mapped[Finding] = relationship(
        back_populates="evidences", foreign_keys=[finding_id]
    )
    author: Mapped[User] = relationship(back_populates="evidences_created")
