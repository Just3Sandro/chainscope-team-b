"""audit_events.actor_id nullable (issue #5, authentification).

Un échec de login sur e-mail **inconnu** ne dispose d'aucun acteur
identifié (pas de ligne `users`) : la colonne `actor_id` devient
nullable. La métadonnée porte alors `email_normalise` — jamais de mot
de passe ni de token (F18, T-47).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )


def downgrade() -> None:
    # Le downgrade exige qu'aucune ligne d'audit sans acteur n'existe
    # (données de démo / test) : sinon la contrainte NOT NULL échoue —
    # comportement assumé (l'audit est append-only, spec §4).
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
