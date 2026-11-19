"""Schémas Pydantic partagés (contrat API, spec §6)."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Détail normalisé d'une erreur (spec §6 : `{code, message, request_id}`).

    `request_id` est celui du middleware X-Request-ID (D-06) — il permet au
    client de tracer le problème sans que l'erreur ne contienne de secret.
    """

    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    """Corps de toute réponse d'erreur de l'API : `{"error": {...}}`."""

    error: ErrorDetail


class Page(BaseModel, Generic[T]):
    """Enveloppe de pagination (D-11 : `?limit=20&offset=0`, limit <= 100)."""

    items: list[T]
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int | None = Field(default=None, description="Nombre total si connu.")


__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "Page",
    "T",
]
