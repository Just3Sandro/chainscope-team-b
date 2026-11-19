"""Routeur racine de l'API (`/api/v1`).

Le socle (issue #4) ne contient que `/health` ; les routeurs métier
(auth, plateforme, cabinet, engagements, portail client — spec §6)
s'ajouteront ici sans changement de préfixe.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import health

api_router = APIRouter()
api_router.include_router(health.router)

__all__ = ["api_router"]
