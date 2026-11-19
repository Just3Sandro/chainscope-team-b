"""Fixtures du socle backend (issue #4).

- `migrated_db` : reset du schéma public de la base de test puis
  `alembic upgrade head` (scope session) ;
- `db` : session SQLAlchemy sur la base de test ;
- `app` / `client` : application FastAPI + client httpx ASGI (sans réseau).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
# Base de test dédiée, valeurs fictives dev-only (D-16) ; voir .env.example.
TEST_DATABASE_URL = "postgresql://chainscope:devfictional@127.0.0.1:5432/chainscope_test"

# Doit être fixé avant tout import de `app.*` (app.db crée le moteur au chargement).
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

import pytest
from sqlalchemy import create_engine, text


@pytest.fixture(scope="session")
def migrated_db() -> str:
    """Vide le schéma public (CASCADE) puis applique les migrations."""
    from app.db import resolve_database_url

    engine = create_engine(resolve_database_url(TEST_DATABASE_URL))
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")
    return TEST_DATABASE_URL


@pytest.fixture
def db(migrated_db: str):
    """Session SQLAlchemy par test, fermée en fin de test (les écritures du
    test non commitées sont annulées). Le reset du schéma est fait par
    `migrated_db`, qui COMMITTE `DROP/CREATE SCHEMA` — pas de rollback."""
    from app.db import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def app(migrated_db: str):
    from app.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    return create_app()


@pytest.fixture
async def client(app):
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
