"""Moteur et sessions SQLAlchemy 2.x (synchrone, spec §2).

Le schème `postgresql://` est normalisé vers `postgresql+psycopg2://` :
SQLAlchemy 2.1 pointe `postgresql://` par défaut sur psycopg v3, qui n'est
pas dans `requirements.txt` (driver installé : `psycopg2-binary`, D-02).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()


def resolve_database_url(raw_url: str) -> URL:
    """Force le driver psycopg2 pour tout schème Postgres générique."""
    url = make_url(raw_url)
    if url.drivername in ("postgresql", "postgres"):
        url = url.set(drivername="postgresql+psycopg2")
    return url


engine: Engine = create_engine(
    resolve_database_url(_settings.DATABASE_URL), pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : une session par requête, fermée en fin de traitement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["SessionLocal", "engine", "get_db", "resolve_database_url"]
