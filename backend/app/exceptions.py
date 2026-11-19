"""Erreurs normalisées de l'API (spec §6, D-06).

Toute réponse d'erreur a la forme `{"error": {code, message, request_id}}`.
Codes : 400 validation métier ; 401 non connecté ; 403 permission ;
404 inexistante / hors périmètre ; 409 conflit ; 413 taille ; 422 schéma ;
429 limitation ; 500 interne (jamais de stack trace dans la réponse).
"""
from __future__ import annotations

import logging
import uuid
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.schemas.common import ErrorDetail

logger = logging.getLogger("chainscope.api")

# --- code de base Postgres (pgerror code 23505 = unique_violation) ---------
_PG_UNIQUE_VIOLATION = "23505"


class ErrorCode(str, Enum):
    VALIDATION = "VALIDATION"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    RATE_LIMITED = "RATE_LIMITED"
    GRAPH_TOO_COMPLEX = "GRAPH_TOO_COMPLEX"
    INTERNAL = "INTERNAL"
    # --- issue #5 (authentification) ---------------------------------------
    UNAUTHENTICATED = "UNAUTHENTICATED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    CSRF_INVALID = "CSRF_INVALID"
    INVALID_TOKEN = "INVALID_TOKEN"


class ApiError(Exception):
    """Exception métier levée par les services/routes.

    ``headers`` porte des en-têtes supplémentaires de la réponse
    normalisée (ex. ``Retry-After`` sur 429, D-07) — jamais de corps
    non conforme au contrat ``{"error": {code, message, request_id}}``.
    """

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        super().__init__(message)

    @classmethod
    def validation(cls, message: str) -> "ApiError":
        return cls(400, ErrorCode.VALIDATION, message)

    @classmethod
    def unauthorized(cls, message: str = "Non connecté") -> "ApiError":
        return cls(401, ErrorCode.UNAUTHORIZED, message)

    @classmethod
    def forbidden(cls, message: str = "Permission insuffisante") -> "ApiError":
        return cls(403, ErrorCode.FORBIDDEN, message)

    @classmethod
    def not_found(cls, message: str = "Ressource introuvable ou hors périmètre") -> "ApiError":
        return cls(404, ErrorCode.NOT_FOUND, message)

    @classmethod
    def conflict(cls, message: str) -> "ApiError":
        return cls(409, ErrorCode.CONFLICT, message)

    @classmethod
    def payload_too_large(cls, message: str) -> "ApiError":
        return cls(413, ErrorCode.PAYLOAD_TOO_LARGE, message)

    @classmethod
    def rate_limited(
        cls, message: str = "Trop de requêtes", retry_after: int | None = None
    ) -> "ApiError":
        """429 normalisé + en-tête ``Retry-After`` (D-07) quand le délai
        de réessai est connu (limiteur fenêtre glissante)."""
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
        return cls(429, ErrorCode.RATE_LIMITED, message, headers=headers)

    @classmethod
    def graph_too_complex(cls, message: str) -> "ApiError":
        """D-10 : budget d'exploration dépassé — message stable, pas de résultat partiel."""
        return cls(422, ErrorCode.GRAPH_TOO_COMPLEX, message)


_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    422: ErrorCode.VALIDATION,
    429: ErrorCode.RATE_LIMITED,
}


def classify_integrity_error(exc: IntegrityError) -> tuple[int, ErrorCode, str]:
    """Comportement défini pour les violations de contraintes de base.

    - violation d'unicité (23505) => 409 CONFLICT (e-mail dupliqué, membership,
      token, clé unique d'actif/edge...) ;
    - toute autre violation de contrainte (CHECK CVSS/criticité, FK, NOT NULL)
      => 400 VALIDATION.
    """
    pgcode = getattr(exc.orig, "pgcode", None)
    if pgcode == _PG_UNIQUE_VIOLATION:
        return (
            409,
            ErrorCode.CONFLICT,
            "Ressource déjà existante (conflit de valeur unique)",
        )
    return (
        400,
        ErrorCode.VALIDATION,
        "Données invalides (contrainte de la base de données)",
    )


def _request_id(request: Request) -> str:
    """ID injecté par le middleware RequestIDMiddleware (D-06)."""
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) and rid else str(uuid.uuid4())


def _error_response(
    request: Request,
    status_code: int,
    code: ErrorCode,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    detail = ErrorDetail(code=code.value, message=message, request_id=_request_id(request))
    return JSONResponse(
        status_code=status_code, content={"error": detail.model_dump()}, headers=headers
    )


# --- gestionnaires (enregistrés dans create_app) ----------------------------
async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _error_response(
        request, exc.status_code, exc.code, exc.message, headers=exc.headers
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    status_code, code, message = classify_integrity_error(exc)
    logger.warning(
        "Violation de contrainte (%s) request_id=%s: %s",
        getattr(exc.orig, "pgcode", "?"),
        _request_id(request),
        message,
    )
    return _error_response(request, status_code, code, message)


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error_response(request, 422, ErrorCode.VALIDATION, "Schéma de requête invalide")


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) and exc.detail else "Requête non valide"
    code = _STATUS_TO_CODE.get(exc.status_code)
    if code is None:
        code = ErrorCode.INTERNAL if exc.status_code >= 500 else ErrorCode.VALIDATION
    return _error_response(request, exc.status_code, code, message)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 générique : stack trace en logs uniquement, jamais dans la réponse (spec §8)."""
    logger.exception("Erreur non gérée: request_id=%s", _request_id(request))
    return _error_response(
        request, 500, ErrorCode.INTERNAL, "Une erreur interne est survenue"
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "ApiError",
    "ErrorCode",
    "classify_integrity_error",
    "register_exception_handlers",
]
