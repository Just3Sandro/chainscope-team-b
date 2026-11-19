"""Middlewares ASGI du socle (D-04, D-06, spec §8).

Middlewares ASGI purs (pas de BaseHTTPMiddleware) : les exceptions traversent
le middleware sans être avalées, les gestionnaires globalisés de
`app.exceptions` s'appliquent donc aussi aux réponses 500, et les en-têtes
sont ajoutés sur toutes les réponses.

Ordre d'installation (le dernier ajouté est le plus externe) :
1. SecurityHeadersMiddleware
2. RequestIDMiddleware  => `request.state.request_id` visible de tout l'arbre.
"""
from __future__ import annotations

import uuid

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"

# En-têtes de base (spec §8, D-04 ; le téléchargement des preuves renforce
# par ailleurs `Content-Disposition: attachment` au niveau de la route).
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


class SecurityHeadersMiddleware:
    """Ajoute les en-têtes de sécurité aux réponses HTTP (setdefault :
    une route peut les raffiner, jamais les retirer)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message.get("headers") or [])
                for name, value in _SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                message["headers"] = headers.raw
            await send(message)

        await self.app(scope, receive, send_with_headers)


class RequestIDMiddleware:
    """X-Request-ID (D-06) : généré si absent, propagé dans
    `request.state.request_id` et retourné dans l'en-tête de toute réponse.

    L'ID fourni par le client est conservé (trace client<->serveur) mais
    n'est pas une source d'autorisation : tout contexte applicatif se repose
    sur `request.state`, jamais sur un header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        incoming = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
        request_id = incoming or str(uuid.uuid4())
        request.state.request_id = request_id

        async def send_with_id(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message.get("headers") or [])
                headers[REQUEST_ID_HEADER] = request_id
                message["headers"] = headers.raw
            await send(message)

        await self.app(scope, receive, send_with_id)


__all__ = ["REQUEST_ID_HEADER", "RequestIDMiddleware", "SecurityHeadersMiddleware"]
