"""Tests du socle backend (issue #4) — aucun endpoint métier dans ce socle.

Couvre : health, format d'erreur normalisé + X-Request-ID (spec §6, D-06),
rejets de base (CVSS, criticité, e-mail dupliqué, membership dupliquée) et
reproductibilité de la migration (2× `alembic upgrade head`).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.exceptions import ErrorCode, classify_integrity_error
from app.models import (
    Asset,
    AssetType,
    ClientOrg,
    Engagement,
    Finding,
    FindingSeverity,
    Tenant,
    TenantMembership,
    TenantMembershipRole,
    User,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]


@dataclass
class Context:
    """Arborescence parentale minimale (données fictives), unique par test."""

    user: User
    tenant: Tenant
    client_org: ClientOrg
    engagement: Engagement


def _build_context(db, suffix: str) -> Context:
    user = User(email=f"pentester.{suffix}@exemplif.fr", password_hash="argon2id$exemplif")
    tenant = Tenant(name=f"Cabinet {suffix}", slug=f"cabinet-{suffix}")
    db.add_all([user, tenant])
    db.flush()
    db.add(
        TenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantMembershipRole.TENANT_ADMIN
        )
    )
    client_org = ClientOrg(tenant_id=tenant.id, name=f"Client {suffix}")
    db.add(client_org)
    db.flush()
    engagement = Engagement(
        tenant_id=tenant.id,
        client_org_id=client_org.id,
        name=f"Mission {suffix}",
        scope="périmètre fictif de test",
    )
    db.add(engagement)
    db.commit()
    return Context(user=user, tenant=tenant, client_org=client_org, engagement=engagement)


@pytest.fixture
def context(db) -> Context:
    return _build_context(db, uuid.uuid4().hex[:10])


# --- API socle --------------------------------------------------------------
@pytest.mark.asyncio
async def test_health_200(client) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "up"}
    # En-têtes de base (middleware)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"  # T-47
    # X-Request-ID généré si absent (D-06)
    assert response.headers["x-request-id"]


@pytest.mark.asyncio
async def test_unknown_route_404_format_normalise(client) -> None:
    response = await client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    payload = response.json()
    assert set(payload) == {"error"}
    error = payload["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]
    # Le request_id du corps est celui de l'en-tête (D-06)
    assert response.headers["x-request-id"] == error["request_id"]


@pytest.mark.asyncio
async def test_request_id_client_propage(client) -> None:
    incoming = str(uuid.uuid4())
    response = await client.get(
        "/api/v1/health", headers={"X-Request-ID": incoming}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == incoming


@pytest.mark.asyncio
async def test_request_id_conforme_court_propage(client) -> None:
    """ID conforme au pattern (ex. `abc-123`) : propagé tel quel (issue #31)."""
    response = await client.get(
        "/api/v1/health", headers={"X-Request-ID": "abc-123"}
    )
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "abc-123"


@pytest.mark.asyncio
async def test_request_id_trop_long_ignore_genera(client) -> None:
    r"""ID de 500 caractères (hors bornes `^[\w-]{1,64}$`, issue #31) :
    ignoré sans erreur — le serveur répond 200 avec un UUID valide (<= 64)."""
    response = await client.get(
        "/api/v1/health", headers={"X-Request-ID": "x" * 500}
    )
    assert response.status_code == 200
    returned = response.headers["x-request-id"]
    assert returned != "x" * 500
    assert len(returned) <= 64
    uuid.UUID(returned)  # bien un UUID v4 généré par le serveur


@pytest.mark.asyncio
async def test_request_id_caracteres_hors_pattern_ignores(client) -> None:
    r"""Valeurs ASCII hors pattern `^[\w-]{1,64}$` : ignorées, UUID généré.
    (Les valeurs non-ASCII ne sont pas testables : httpx n'accepte que des
    valeurs d'en-tête ASCII — limitation du client, pas du serveur.)"""
    for incoming in ("abc 123", "abc;drop", "ok=1", "abc/123", "abc.def", "a" * 65):
        response = await client.get(
            "/api/v1/health", headers={"X-Request-ID": incoming}
        )
        assert response.status_code == 200
        assert response.headers["x-request-id"] != incoming
        assert len(response.headers["x-request-id"]) <= 64


# --- Contraintes de base (comportement défini : 409 unicité, 400 CHECK) ------
def test_cvss_above_10_rejected_by_database(db, context) -> None:
    finding = Finding(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        title="Constat test",
        description="description fictive",
        impact="impact fictif",
        recommendation="recommandation fictive",
        severity=FindingSeverity.LOW,
        cvss=Decimal("11.0"),
        created_by=context.user.id,
    )
    db.add(finding)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (400, ErrorCode.VALIDATION)


def test_criticality_out_of_range_rejected_by_database(db, context) -> None:
    asset = Asset(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        name="Actif test",
        type=AssetType.WEB,
        criticality=6,
    )
    db.add(asset)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (400, ErrorCode.VALIDATION)


def test_duplicate_email_rejected(db, context) -> None:
    twin = User(
        email=context.user.email.upper(), password_hash="argon2id$exemplif"
    )
    db.add(twin)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (409, ErrorCode.CONFLICT)


def test_duplicate_membership_rejected(db, context) -> None:
    db.add(
        TenantMembership(
            user_id=context.user.id,
            tenant_id=context.tenant.id,
            role=TenantMembershipRole.PENTESTER,
        )
    )
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (409, ErrorCode.CONFLICT)


# --- Isolation tenant et unicités (QA écart 5 : inserts ORM directs) --------
def test_asset_cross_tenant_rejected_by_composite_fk(db) -> None:
    """Un actif dont l'engagement appartient à UN AUTRE tenant que
    `asset.tenant_id` est rejeté par la FK composite
    (tenant_id, engagement_id) => engagements(tenant_id, id) : 23503,
    comportement défini 400 VALIDATION (spec §5 : pas de référence
    cross-tenant, même au niveau base)."""
    ctx_a = _build_context(db, uuid.uuid4().hex[:10])
    ctx_b = _build_context(db, uuid.uuid4().hex[:10])
    rogue = Asset(
        tenant_id=ctx_a.tenant.id,
        engagement_id=ctx_b.engagement.id,  # engagement du tenant B
        name="Actif illégitime",
        type=AssetType.OTHER,
    )
    db.add(rogue)
    with pytest.raises(IntegrityError) as exc_info:
        db.commit()
    db.rollback()
    assert getattr(exc_info.value.orig, "pgcode", None) == "23503"
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (400, ErrorCode.VALIDATION)


def test_attack_edge_duplicate_rejected(db, context) -> None:
    """Unicité (source, target, finding) : la même relation exacte ne peut
    exister qu'une fois => IntegrityError 23505, comportement défini 409."""
    from app.models import AttackEdge

    suffix = uuid.uuid4().hex[:10]
    source = Asset(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        name=f"Actif source {suffix}",
        type=AssetType.WEB,
    )
    target = Asset(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        name=f"Actif cible {suffix}",
        type=AssetType.DATABASE,
    )
    db.add_all([source, target])
    db.flush()
    finding = Finding(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        title=f"Constat edges {suffix}",
        description="d",
        impact="i",
        recommendation="r",
        severity=FindingSeverity.LOW,
        cvss=Decimal("5.0"),
        created_by=context.user.id,
    )
    db.add(finding)
    db.flush()
    db.add(
        AttackEdge(
            tenant_id=context.tenant.id,
            engagement_id=context.engagement.id,
            source_asset_id=source.id,
            target_asset_id=target.id,
            finding_id=finding.id,
        )
    )
    db.commit()
    with pytest.raises(IntegrityError) as exc_info:
        db.add(
            AttackEdge(
                tenant_id=context.tenant.id,
                engagement_id=context.engagement.id,
                source_asset_id=source.id,
                target_asset_id=target.id,
                finding_id=finding.id,
            )
        )
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (409, ErrorCode.CONFLICT)


def test_evidence_storage_key_duplicate_rejected(db, context) -> None:
    """Unicité `evidences.storage_key` : doublon => IntegrityError 23505,
    comportement défini 409 (le stockage_key est généré par le serveur,
    D-09 ; le test vérifie la contrainte de base)."""
    from app.models import Evidence

    suffix = uuid.uuid4().hex[:10]
    finding = Finding(
        tenant_id=context.tenant.id,
        engagement_id=context.engagement.id,
        title=f"Constat evidence {suffix}",
        description="d",
        impact="i",
        recommendation="r",
        severity=FindingSeverity.MEDIUM,
        cvss=Decimal("5.0"),
        created_by=context.user.id,
    )
    db.add(finding)
    db.flush()
    storage_key = f"tenant-{context.tenant.id}/{uuid.uuid4()}.png"

    def _make_evidence() -> Evidence:
        return Evidence(
            tenant_id=context.tenant.id,
            engagement_id=context.engagement.id,
            finding_id=finding.id,
            storage_key=storage_key,
            sha256="a" * 64,
            mime="image/png",
            size_bytes=1024,
            created_by=context.user.id,
        )

    db.add(_make_evidence())
    db.commit()
    with pytest.raises(IntegrityError) as exc_info:
        db.add(_make_evidence())
        db.commit()
    db.rollback()
    status, code, _message = classify_integrity_error(exc_info.value)
    assert (status, code) == (409, ErrorCode.CONFLICT)
# --- Migration (à exécuter en dernier : destructive) ------------------------
def test_migration_re_runnable(migrated_db) -> None:
    """Downgrade complet puis 2× `alembic upgrade head` sans erreur (idempotent),
    et vérifie que les 15 tables de la spec §5 existent."""
    from alembic import command
    from alembic.config import Config

    from app.db import engine

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")

    with engine.connect() as conn:
        names = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables"
                " WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                " AND table_name <> 'alembic_version'"
                " ORDER BY table_name"
            )
        ).scalars().all()
    assert names == sorted(
        [
            "users",
            "platform_admins",
            "tenants",
            "tenant_memberships",
            "client_orgs",
            "client_memberships",
            "engagements",
            "assets",
            "findings",
            "attack_edges",
            "evidences",
            "sessions",
            "invitations",
            "password_reset_tokens",
            "audit_events",
        ]
    )
