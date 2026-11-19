"""Configuration applicative (pydantic-settings).

Toutes les valeurs opérationnelles (limites, chemins, identifiants d'hôtes)
passent par `Settings` : le code applicatif ne contient pas de valeur magic
(règle globale équipe B, spec §4/§6/§8, décisions D-04 à D-16).

Les variables sont fournies par l'environnement (compose, CI, `.env` local) ;
voir `.env.example` à la racine du dépôt (valeurs fictives, aucun secret réel).
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Environnements autorisés (spec : `dev` | `production`)."""

    DEV = "dev"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    # --- Environnement -------------------------------------------------
    ENV: Environment = Environment.DEV
    DATABASE_URL: str
    """URL Postgres 16 (ex. `postgresql://user:pass@hote:5432/chainscope`)."""

    # --- Stockage des preuves (D-09) ------------------------------------
    EVIDENCE_DIR: str = "data/evidence"
    """Volume local privé ; chemin interne généré par le serveur."""

    # --- SMTP (optionnel, D-12) ------------------------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None

    # --- Cookie de session (D-04) ----------------------------------------
    SESSION_COOKIE_NAME: str = "cs_session"
    SESSION_LIFETIME_HOURS: int = 12
    SESSION_COOKIE_SECURE: bool | None = None
    """`None` => dérivé de `ENV` (True si production), surcharge explicite possible."""

    # --- Bootstrap administrateur plateforme (D-14) ----------------------
    PLATFORM_ADMIN_EMAIL: str | None = None
    PLATFORM_ADMIN_PASSWORD: str | None = None

    # --- Limites opérationnelles -----------------------------------------
    # Rate limiting, fenêtre glissante (D-07) sur login/forgot/reset/invitation.
    RATE_LIMIT_MAX_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    # Upload de preuves : 10 Mio maximum (D-08, spec §4).
    UPLOAD_MAX_BYTES: int = 10 * 1024 * 1024
    # Densité du graphe par engagement (spec §4, D-10).
    MAX_ASSETS_PER_ENGAGEMENT: int = 150
    MAX_EDGES_PER_ENGAGEMENT: int = 300
    # Budget d'exploration DFS (D-10 ; au-delà : 422 GRAPH_TOO_COMPLEX).
    GRAPH_EXPANSION_BUDGET: int = 50_000
    # Pagination (D-11, spec §6 : ?limit=20&offset=0, limit <= 100).
    PAGINATION_DEFAULT_LIMIT: int = 20
    PAGINATION_MAX_LIMIT: int = 100

    # --- Validité des jetons (spec §8 : usage unique, expiration courte) --
    INVITATION_LIFETIME_HOURS: int = 24
    PASSWORD_RESET_LIFETIME_MINUTES: int = 30

    @property
    def is_production(self) -> bool:
        return self.ENV is Environment.PRODUCTION

    @property
    def session_cookie_secure(self) -> bool:
        """D-04 : `Secure` lorsque ENV=production, sauf surcharge explicite."""
        if self.SESSION_COOKIE_SECURE is not None:
            return self.SESSION_COOKIE_SECURE
        return self.is_production


@lru_cache
def get_settings() -> Settings:
    return Settings()
