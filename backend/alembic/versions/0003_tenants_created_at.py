"""tenants.created_at (issue #7, plateforme).

Le contrat de lecture/création de l'issue #7 (``GET/POST
/platform/tenants``) renvoie ``created_at`` pour chaque tenant, or la
spéc §5 ne prescrit que ``id, name, slug, is_active`` pour la table
``tenants``. La colonne est ajoutée avec ``server_default now()`` :

- les lignes existantes reçoivent la date d'application de la migration
  (comportement acceptable, documenté — aucune donnée de production au
  stade du benchmark) ;
- aucun modèle ni API existante n'est affecté (colonne additive,
  nullable=False + défaut serveur).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "created_at")
