"""Schémas Pydantic de l'API (spec §6)."""
from app.schemas.auth import (
    AuthMe,
    ClientMembershipOut,
    CsrfResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TenantMembershipOut,
)
from app.schemas.common import ErrorDetail, ErrorResponse, Page
from app.schemas.platform import (
    TenantCreateRequest,
    TenantOut,
    TenantPatchRequest,
    TenantSummary,
)

__all__ = [
    "AuthMe",
    "ClientMembershipOut",
    "CsrfResponse",
    "ErrorDetail",
    "ErrorResponse",
    "ForgotPasswordRequest",
    "LoginRequest",
    "Page",
    "ResetPasswordRequest",
    "TenantCreateRequest",
    "TenantMembershipOut",
    "TenantOut",
    "TenantPatchRequest",
    "TenantSummary",
]
