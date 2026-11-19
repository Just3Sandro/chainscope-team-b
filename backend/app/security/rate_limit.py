"""Rate limiting applicatif en mémoire, fenêtre glissante (D-07, T-24…T-26).

- Quota par Settings : ``RATE_LIMIT_MAX_REQUESTS`` (défaut 5) par
  ``RATE_LIMIT_WINDOW_SECONDS`` (défaut 60) ;
- Clés (issue #5, D-07) :
  * ``login``             -> e-mail normalisé + IP client ;
  * ``forgot-password``   -> e-mail normalisé + IP client ;
  * ``reset-password``    -> IP client ;
  * ``accept-invitation`` -> IP client ;
- Dépassement : 429 normalisé ``RATE_LIMITED`` + en-tête ``Retry-After``.

**Limite documentée (D-07, T-26)** : l'état est en mémoire par processus —
pas de partage entre instances ni de persistance au redémarrage.
Acceptable pour l'installation livrée (mono-instance, spec §2 : pas de
Redis requis) ; le contournement par rotation d'IP reste résiduel
(THREAT_MODEL §4.1). Le « verify fantôme » du login (e-mail inconnu,
``app.security.passwords.dummy_password_hash``) égalise les délais de
calcul que le compte existe ou non (T-21, D-07).
"""
from __future__ import annotations

import math
import threading
import time
from typing import Final

from app.config import get_settings

#: Préfixes de clés (stables — ne pas mélanger les flux entre eux).
KEY_LOGIN: Final[str] = "login"
KEY_FORGOT_PASSWORD: Final[str] = "forgot_password"
KEY_RESET_PASSWORD: Final[str] = "reset_password"
KEY_ACCEPT_INVITATION: Final[str] = "accept_invitation"

_NO_CLIENT_IP: Final[str] = "inconnu"


def build_key(kind: str, *parts: str) -> str:
    """Clé normalisée ``<kind>:<partie>:<partie>`` (parts vides ignorées)."""
    clean = [part for part in parts if part]
    return ":".join([kind, *clean]) if clean else kind


class SlidingWindowLimiter:
    """Fenêtre glissante en mémoire : conserve les horodatages (``monotonic``)
    des requêtes par clé ; une requête est acceptée si moins de
    ``max_requests`` horodatages datent de moins de ``window_seconds``."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Enregistre la requête si le quota est disponible ; renvoie
        ``True`` (acceptée) ou ``False`` (limitée)."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = [t for t in self._hits.get(key, ()) if t > cutoff]
            if len(hits) >= self.max_requests:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def retry_after(self, key: str) -> int:
        """Délai (secondes, >= 1) avant qu'un quota ne se libère pour ``key``."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = [t for t in self._hits.get(key, ()) if t > cutoff]
        if not hits:
            return 1
        delta = hits[0] + self.window_seconds - now
        return max(1, math.ceil(delta))

    def reset(self) -> None:
        """Purge l'état (usage tests ; jamais appelé par l'applicatif)."""
        with self._lock:
            self._hits.clear()


_limiter: SlidingWindowLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> SlidingWindowLimiter:
    """Singleton de processus, configuré par ``Settings`` (D-07)."""
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                settings = get_settings()
                _limiter = SlidingWindowLimiter(
                    settings.RATE_LIMIT_MAX_REQUESTS,
                    settings.RATE_LIMIT_WINDOW_SECONDS,
                )
    return _limiter


def client_ip(request) -> str:
    """IP client vue par l'instance (``request.client`` ASGI, starlette
    ``Request``).

    Mono-instance livrée (D-07) : pas de confiance à ``X-Forwarded-For``
    (en-tête falsifiable sans proxy de terminaison documenté) ; derrière
    le reverse proxy de production, l'IP sera celle du proxy — limite
    assumée, T-26.
    """
    client = getattr(request, "client", None)
    host = getattr(client, "host", None) if client is not None else None
    return host or _NO_CLIENT_IP


__all__ = [
    "KEY_ACCEPT_INVITATION",
    "KEY_FORGOT_PASSWORD",
    "KEY_LOGIN",
    "KEY_RESET_PASSWORD",
    "SlidingWindowLimiter",
    "build_key",
    "client_ip",
    "get_rate_limiter",
]
