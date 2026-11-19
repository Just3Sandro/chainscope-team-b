"""Routeur racine de l'API (`/api/v1`).

Socle (issue #4) : `/health` ; authentification (issue #5) : `/auth/*`.
Les routeurs métier (plateforme, cabinet, engagements, portail client —
spec §6) s'ajouteront ici sans changement de préfixe.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

__all__ = ["api_router"]
