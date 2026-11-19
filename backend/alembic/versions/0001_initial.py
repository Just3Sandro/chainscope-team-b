"""Socle initial : les 15 tables de la spec §5.

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.constants import CRITICALITY_MAX, CRITICALITY_MIN, CRITICALITY_DEFAULT, CVSS_MAX, CVSS_MIN

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) users (+ e-mail unique insensible à la casse)
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_users_email_lower", "users", [sa.func.lower(sa.column("email"))], unique=True
    )

    # 2) platform_admins
    op.create_table(
        "platform_admins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_platform_admins_user_id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_platform_admins_user", ondelete="CASCADE"
        ),
    )

    # 3) tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    # 4) tenant_memberships
    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("TENANT_ADMIN", "PENTESTER", name="tenant_membership_role"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tenant_id", name="uq_tenant_memberships_user_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_tenant_memberships_user"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_tenant_memberships_tenant"
        ),
    )
    op.create_index(
        "ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"], unique=False
    )
    op.create_index(
        "ix_tenant_memberships_tenant_id",
        "tenant_memberships",
        ["tenant_id"],
        unique=False,
    )

    # 5) client_orgs
    op.create_table(
        "client_orgs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_client_orgs_tenant_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_client_orgs_tenant"
        ),
    )
    op.create_index(
        "ix_client_orgs_tenant_id", "client_orgs", ["tenant_id"], unique=False
    )

    # 6) client_memberships
    op.create_table(
        "client_memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("client_org_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.Enum("CLIENT_VIEWER", name="client_membership_role"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "client_org_id", name="uq_client_memberships_user_org"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_client_memberships_user"
        ),
        sa.ForeignKeyConstraint(
            ["client_org_id"],
            ["client_orgs.id"],
            name="fk_client_memberships_client_org",
        ),
    )
    op.create_index(
        "ix_client_memberships_user_id", "client_memberships", ["user_id"], unique=False
    )
    op.create_index(
        "ix_client_memberships_client_org_id",
        "client_memberships",
        ["client_org_id"],
        unique=False,
    )

    # 7) engagements
    op.create_table(
        "engagements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("client_org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("DRAFT", "IN_PROGRESS", "CLOSED", name="engagement_status"),
            server_default="DRAFT",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_engagements_tenant_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_engagements_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "client_org_id"],
            ["client_orgs.tenant_id", "client_orgs.id"],
            name="fk_engagements_tenant_client_org",
        ),
    )
    op.create_index(
        "ix_engagements_tenant_id", "engagements", ["tenant_id"], unique=False
    )

    # 8) assets
    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("engagement_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.Enum("WEB", "SERVER", "DATABASE", "WORKSTATION", "OTHER", name="asset_type"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_entry_point", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_crown_jewel", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "criticality",
            sa.Integer(),
            server_default=sa.text(str(CRITICALITY_DEFAULT)),
            nullable=False,
        ),
        sa.Column("x", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("y", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "id", name="uq_assets_tenant_id"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_assets_tenant_engagement",
        ),
        sa.CheckConstraint(
            f"criticality >= {CRITICALITY_MIN} AND criticality <= {CRITICALITY_MAX}",
            name="ck_assets_criticality_range",
        ),
    )
    op.create_index("ix_assets_tenant_id", "assets", ["tenant_id"], unique=False)
    op.create_index(
        "ix_assets_engagement_id", "assets", ["engagement_id"], unique=False
    )

    # 9) findings
    op.create_table(
        "findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("engagement_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column(
            "severity",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="finding_severity"),
            nullable=False,
        ),
        sa.Column("cvss", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column(
            "status",
            sa.Enum("OPEN", "IN_PROGRESS", "REMEDIATED", "ACCEPTED_RISK", name="finding_status"),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "engagement_id", "id", name="uq_findings_tenant_engagement_id"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_findings_tenant_engagement",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_findings_created_by"
        ),
        sa.CheckConstraint(
            f"cvss >= {CVSS_MIN} AND cvss <= {CVSS_MAX}", name="ck_findings_cvss_range"
        ),
    )
    op.create_index("ix_findings_tenant_id", "findings", ["tenant_id"], unique=False)
    op.create_index(
        "ix_findings_engagement_id", "findings", ["engagement_id"], unique=False
    )
    op.create_index(
        "ix_findings_engagement_status", "findings", ["engagement_id", "status"], unique=False
    )

    # 10) attack_edges
    op.create_table(
        "attack_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("engagement_id", sa.Uuid(), nullable=False),
        sa.Column("source_asset_id", sa.Uuid(), nullable=False),
        sa.Column("target_asset_id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "finding_id",
            name="uq_attack_edges_source_target_finding",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_attack_edges_tenant_engagement",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_asset_id"],
            ["assets.tenant_id", "assets.id"],
            name="fk_attack_edges_source_asset",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "target_asset_id"],
            ["assets.tenant_id", "assets.id"],
            name="fk_attack_edges_target_asset",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id", "finding_id"],
            ["findings.tenant_id", "findings.engagement_id", "findings.id"],
            name="fk_attack_edges_finding",
        ),
        sa.CheckConstraint(
            "source_asset_id <> target_asset_id",
            name="ck_attack_edges_source_target_distinct",
        ),
    )
    op.create_index(
        "ix_attack_edges_tenant_id", "attack_edges", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_attack_edges_engagement_id", "attack_edges", ["engagement_id"], unique=False
    )

    # 11) evidences
    op.create_table(
        "evidences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("engagement_id", sa.Uuid(), nullable=False),
        sa.Column("finding_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "client_visible", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_evidences_storage_key"),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id"],
            ["engagements.tenant_id", "engagements.id"],
            name="fk_evidences_tenant_engagement",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "engagement_id", "finding_id"],
            ["findings.tenant_id", "findings.engagement_id", "findings.id"],
            name="fk_evidences_finding",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_evidences_created_by"
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_evidences_size_non_negative"),
    )
    op.create_index(
        "ix_evidences_tenant_id", "evidences", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_evidences_engagement_id", "evidences", ["engagement_id"], unique=False
    )

    # 12) sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_sessions_user"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)

    # 13) invitations
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("client_org_id", sa.Uuid(), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "TENANT_ADMIN", "PENTESTER", "CLIENT_VIEWER", name="invitation_role"
            ),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_invitations_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["client_org_id"], ["client_orgs.id"], name="fk_invitations_client_org"
        ),
    )
    op.create_index(
        "ix_invitations_tenant_id", "invitations", ["tenant_id"], unique=False
    )

    # 14) password_reset_tokens
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_password_reset_tokens_user"
        ),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )

    # 15) audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_audit_events_tenant"
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_events_actor"
        ),
    )
    op.create_index(
        "ix_audit_events_tenant_id", "audit_events", ["tenant_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_tenant_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_invitations_tenant_id", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_evidences_engagement_id", table_name="evidences")
    op.drop_index("ix_evidences_tenant_id", table_name="evidences")
    op.drop_table("evidences")
    op.drop_index("ix_attack_edges_engagement_id", table_name="attack_edges")
    op.drop_index("ix_attack_edges_tenant_id", table_name="attack_edges")
    op.drop_table("attack_edges")
    op.drop_index("ix_findings_engagement_status", table_name="findings")
    op.drop_index("ix_findings_engagement_id", table_name="findings")
    op.drop_index("ix_findings_tenant_id", table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_assets_engagement_id", table_name="assets")
    op.drop_index("ix_assets_tenant_id", table_name="assets")
    op.drop_table("assets")
    op.drop_index("ix_engagements_tenant_id", table_name="engagements")
    op.drop_table("engagements")
    op.drop_index("ix_client_memberships_client_org_id", table_name="client_memberships")
    op.drop_index("ix_client_memberships_user_id", table_name="client_memberships")
    op.drop_table("client_memberships")
    op.drop_index("ix_client_orgs_tenant_id", table_name="client_orgs")
    op.drop_table("client_orgs")
    op.drop_index("ix_tenant_memberships_tenant_id", table_name="tenant_memberships")
    op.drop_index("ix_tenant_memberships_user_id", table_name="tenant_memberships")
    op.drop_table("tenant_memberships")
    op.drop_table("tenants")
    op.drop_table("platform_admins")
    op.drop_index("ix_users_email_lower", table_name="users")
    op.drop_table("users")

    # Les types ENUM Postgres ne sont pas détruits avec les tables :
    # les supprimer explicitement (après les tables) rend l'upgrade re-executable.
    for enum_name in (
        "tenant_membership_role",
        "client_membership_role",
        "invitation_role",
        "engagement_status",
        "asset_type",
        "finding_severity",
        "finding_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
