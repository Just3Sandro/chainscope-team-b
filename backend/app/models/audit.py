"""Journal d'audit append-only (spec §4 « Historique », D-06).

`request_id` relie l'événement au middleware X-Request-ID ; `metadata_json`
porte des métadonnées non sensibles uniquement (spec §3.9, §8 : jamais de
token ni de mot de passe — test F18). `actor_id` est nullable (migration
0002, issue #5) : les échecs de login sur e-mail inconnu n'ont pas
d'acteur identifié.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tenancy import Tenant
    from app.models.users import User


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_tenant_id", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", name="fk_audit_events_tenant"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", name="fk_audit_events_actor"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    tenant: Mapped[Tenant | None] = relationship(back_populates="audit_events")
    actor: Mapped[User] = relationship(back_populates="audit_events")
