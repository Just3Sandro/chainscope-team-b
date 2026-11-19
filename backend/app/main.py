"""Point d'entrée de l'API ChainScope (factory, spec §2/§6, D-01).

Lancement en dev : `uvicorn app.main:app --port 8011` (DATABASE_URL défini).
En production (compose) : `python:3.12-slim`, entrée via `entrypoint.sh`
(migrations puis uvicorn).
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.config import get_settings
from app.exceptions import register_exception_handlers
from app.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.security.csrf import CsrfProtectionMiddleware

APP_TITLE = "ChainScope API"
APP_VERSION = "0.1.0"
API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    # Spec §8 : pas de debug, ni docs ouvertes en production.
    expose_docs = not settings.is_production
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        debug=False,
        docs_url="/docs" if expose_docs else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if expose_docs else None,
    )
    # Middlewares ASGI : le dernier ajouté est le plus externe.
    # - RequestIDMiddleware (D-06) : le plus externe, pose
    #   `request.state.request_id` visible de tout l'arbre ;
    # - SecurityHeadersMiddleware : en-têtes de sécurité sur toute réponse ;
    # - CsrfProtectionMiddleware (D-05, issue #5) : le plus interne, après
    #   RequestID (lit `request.state.request_id` dans le 403 normalisé).
    app.add_middleware(CsrfProtectionMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


# Instance module-level pour `uvicorn app.main:app`.
app = create_app()
