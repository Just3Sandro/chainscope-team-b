"""Routes plateforme (issue #7, spec §6) : ``/platform/tenants``.

``PLATFORM_ADMIN`` UNIQUEMENT (dépendance ``require_platform_admin``) :
toute autre session authentifiée => 403 ``FORBIDDEN`` ; sans session =>
401 ``UNAUTHENTICATED`` (``get_current_user``).

- ``GET   /platform/tenants``          -> ``Page[TenantSummary]`` paginée
  (D-11) : fiche tenant + **compteurs agrégés lecture seule** — jamais de
  données métier (spec §1, THREAT_MODEL T-05) ;
- ``POST  /platform/tenants``          -> 201 + invitation ``TENANT_ADMIN``
  (flux 2 spec §3, e-mail via D-12) ;
- ``PATCH /platform/tenants/{id}``     -> 200 : suspension / réactivation.

Les mutations (POST/PATCH) exigent le CSRF du middleware global (D-05) :
aucune exemption sur ce routeur. Les agrégats avancés de l'écran
d'administration plateforme sont suivis par l'issue #27 (P2).
"""
from __future__ import annotations

import uuid

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi import status as http_status

from app.api.deps import DbSession, PlatformAdminUser, get_request_id
from app.config import get_settings
from app.exceptions import ApiError, ErrorCode
from app.schemas.common import Page
from app.schemas.platform import (
    TenantCreateRequest,
    TenantOut,
    TenantPatchRequest,
    TenantSummary,
)
from app.services import platform_service
from app.services.audit import AuditContext

router = APIRouter(prefix="/platform", tags=["platform"])


def _tenant_out(tenant) -> TenantOut:
    return TenantOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
    )


@router.get("/tenants", response_model=Page[TenantSummary])
def list_tenants(
    user: PlatformAdminUser,
    db: DbSession,
    limit: Annotated[
        int | None,
        Query(ge=1, description="Page max. bornée à `PAGINATION_MAX_LIMIT` (D-11)."),
    ] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TenantSummary]:
    """Liste paginée des tenants (D-11) : compteurs agrégés uniquement,
    aucune donnée métier (spec §1)."""
    settings = get_settings()
    page_limit = (
        limit if limit is not None else settings.PAGINATION_DEFAULT_LIMIT
    )
    if page_limit > settings.PAGINATION_MAX_LIMIT:
        raise ApiError(
            422,
            ErrorCode.VALIDATION,
            f"limit doit être inférieur ou égal à {settings.PAGINATION_MAX_LIMIT} (D-11).",
        )
    items, total = platform_service.list_tenants(
        db, limit=page_limit, offset=offset
    )
    return Page(
        items=items, limit=page_limit, offset=offset, total=total
    )


@router.post("/tenants", status_code=http_status.HTTP_201_CREATED, response_model=TenantOut)
def create_tenant(
    payload: TenantCreateRequest,
    request: Request,
    user: PlatformAdminUser,
    db: DbSession,
) -> TenantOut:
    """Crée un tenant (``is_active=true``) + invitation ``TENANT_ADMIN``
    pour ``admin_email`` (flux 2 spec §3). 409 ``CONFLICT`` si le slug
    existe déjà ; CSRF exigé (D-05, pas d'exemption)."""
    tenant = platform_service.create_tenant(
        db,
        AuditContext(
            db=db,
            request_id=get_request_id(request),
            actor_id=user.id,
        ),
        name=payload.name,
        slug=payload.slug,
        admin_email=payload.admin_email,
    )
    return _tenant_out(tenant)


@router.patch("/tenants/{tenant_id}", response_model=TenantOut)
def patch_tenant(
    tenant_id: uuid.UUID,
    payload: TenantPatchRequest,
    request: Request,
    user: PlatformAdminUser,
    db: DbSession,
) -> TenantOut:
    """Suspension (``is_active=false``) ou réactivation d'un tenant.

    Body sans ``is_active`` => 422 ; tenant inconnu => 404 ``NOT_FOUND`` ;
    audit ``platform.tenant.suspended`` / ``platform.tenant.reactivated``
    (uniquement si l'état change)."""
    tenant = platform_service.set_tenant_active(
        db,
        AuditContext(
            db=db,
            request_id=get_request_id(request),
            actor_id=user.id,
        ),
        tenant_id=tenant_id,
        is_active=payload.is_active,
    )
    return _tenant_out(tenant)


__all__ = ["router"]
