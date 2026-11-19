"""Base déclarative SQLAlchemy 2.0 (cible de `target_metadata` d'Alembic)."""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
