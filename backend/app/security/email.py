"""Transport e-mail (D-12, spec §3 flux 4).

Deux transports, mutuellement exclusifs, pilotés par ``Settings`` :

1. **SMTP** si ``SMTP_HOST`` est défini (Mailpit dans le compose de dev,
   ou tout SMTP chiffré en production) : ``smtplib``, expéditeur
   ``no-reply@chainscope.local``, sujet court en français ;
2. **Log** sinon — ligne ``DEV-EMAIL to=… subject=… token=…`` —
   **uniquement si ``ENV=dev``** (D-12 : exception documentée unique au
   principe « pas de secrets dans les logs »). Si ``ENV=production`` et
   ``SMTP_HOST`` vide : ``EmailTransportConfigurationError`` (erreur de
   configuration, le flux n'est alors pas expédiable).

Les liens des e-mails sont construits sur ``PUBLIC_BASE_URL`` (Settings,
défaut ``http://localhost:8080``, documenté dans ``.env.example``) : le
corps porte le **lien complet** (ex. ``…/reset?token=…``), jamais un
fragment relatif.

Règle F18/T-47 : le token brut n'apparaît que dans le corps de l'e-mail
(canal dédié) — jamais dans l'audit ni dans d'autres logs.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.config import Environment, get_settings

logger = logging.getLogger("chainscope.email")

#: Expéditeur des e-mails transactionnels (D-12) — domaine fictif interne.
EMAIL_FROM = "no-reply@chainscope.local"
#: Port SMTP du Mailpit de dev si ``SMTP_PORT`` n'est pas défini (D-12/D-16).
_SMTP_FALLBACK_PORT = 1025
_SMTP_TIMEOUT_SECONDS = 10


class EmailTransportConfigurationError(RuntimeError):
    """Configuration e-mail invalide (D-12) : production sans ``SMTP_HOST``.

    Levée avant tout envoi ; le gestionnaire d'erreurs global renvoie
    500 normalisé (message générique, sans détail de configuration).
    """


def build_reset_link(token: str) -> str:
    """Lien complet de réinitialisation (``PUBLIC_BASE_URL`` + route
    frontend ``/reset``, DESIGN P1) — paramètre d'ouverture D-19 : la base
    URL est configurable par ``PUBLIC_BASE_URL``."""
    return f"{get_settings().PUBLIC_BASE_URL}/reset?token={token}"


def send_email(to: str, subject: str, body: str, token: str | None = None) -> None:
    """Expédie un e-mail (SMTP ou log de dev selon la configuration).

    ``token`` (facultatif) sert uniquement à la ligne ``DEV-EMAIL`` de dev
    (D-12) ; il n'est jamais loggé hors de ce mode.
    """
    settings = get_settings()
    if settings.SMTP_HOST:
        _send_smtp(settings.SMTP_HOST, settings.SMTP_PORT, to, subject, body)
        logger.info("E-mail SMTP expédié to=%s subject=%r", to, subject)
        return
    if settings.ENV is not Environment.DEV:
        raise EmailTransportConfigurationError(
            "ENV sans SMTP_HOST : le transport log DEV-EMAIL est interdit hors dev (D-12)."
        )
    token_part = f" token={token}" if token else ""
    logger.warning("DEV-EMAIL to=%s subject=%s%s", to, subject, token_part)


def _send_smtp(host: str, port: int | None, to: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = EMAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    settings = get_settings()
    smtp_port = port or _SMTP_FALLBACK_PORT
    with smtplib.SMTP(host, smtp_port, timeout=_SMTP_TIMEOUT_SECONDS) as client:
        if settings.SMTP_USER:
            client.login(settings.SMTP_USER, settings.SMTP_PASSWORD or "")
        client.send_message(message)


__all__ = [
    "EMAIL_FROM",
    "EmailTransportConfigurationError",
    "build_reset_link",
    "send_email",
]
