"""CLI opérationnelle (D-14, issue #5) : exécuter depuis ``backend/`` :

    python -m app.cli create-platform-admin --email <e> --password <p>

Fallback par variables d'environnement ``PLATFORM_ADMIN_EMAIL`` /
``PLATFORM_ADMIN_PASSWORD`` (Settings, D-14) quand les arguments sont
omis. **Jamais de mot de passe administrateur fixé dans les sources**
(spec §3 flux 1, D-14) : sans email/mot de passe résolvable, la commande
échoue (code 1) avec un message clair.

Idempotence : si le compte est déjà administrateur plateforme, aucune
modification n'est appliquée (message clair + audit
``platform_admin.existing``) ; le code de sortie reste 0. Les créations
sont journalisées (audit ``platform_admin.created``, tenant null).
``DATABASE_URL`` doit être défini (comme pour tout le backend).
"""
from __future__ import annotations

import argparse
import logging
import sys

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import PlatformAdmin, User
from app.security.passwords import hash_password, validate_password_policy
from app.services import auth_service
from app.services.audit import (
    A_PLATFORM_ADMIN_CREATED,
    A_PLATFORM_ADMIN_EXISTING,
    AuditContext,
    ENTITY_PLATFORM_ADMIN,
    record,
)

logger = logging.getLogger("chainscope.cli")


def _lookup_user_by_email(db, email_normalized: str) -> User | None:
    stmt = select(User).where(func.lower(User.email) == email_normalized)
    return db.execute(stmt).scalar_one_or_none()


def _validate_email(raw: str) -> str:
    """Même règle que l'API (email-validator, spec §6) : un e-mail invalide
    créerait un compte injoignable via l'API (422 login/forgot). Renvoie la
    forme normalisée ; lève ``EmailNotValidError`` sinon."""
    return validate_email(raw, check_deliverability=False).email


def cmd_create_platform_admin(cli_email: str | None, cli_password: str | None) -> int:
    settings = get_settings()
    email = cli_email or settings.PLATFORM_ADMIN_EMAIL
    password = cli_password or settings.PLATFORM_ADMIN_PASSWORD
    if not email or not password:
        print(
            "ERREUR : email/mot de passe absents. Fournir --email/--password "
            "ou définir PLATFORM_ADMIN_EMAIL / PLATFORM_ADMIN_PASSWORD (D-14).",
            file=sys.stderr,
        )
        return 1

    policy_error = validate_password_policy(password)
    if policy_error is not None:
        print(f"ERREUR : {policy_error}", file=sys.stderr)
        return 1

    try:
        email_norm = _validate_email(email)
    except EmailNotValidError as exc:
        print(f"ERREUR : e-mail invalide (rejeté par email-validator, comme l'API) : {exc}", file=sys.stderr)
        return 1
    email_norm = auth_service.normalize_email(email_norm)
    db = SessionLocal()
    try:
        user = _lookup_user_by_email(db, email_norm)
        already_admin = False
        if user is not None:
            already_admin = (
                db.query(PlatformAdmin).filter(PlatformAdmin.user_id == user.id).first()
                is not None
            )

        context = AuditContext(db=db, actor_id=user.id if user else None)
        if user is None:
            user = User(email=email_norm, password_hash=hash_password(password))
            db.add(user)
            db.flush()
            db.add(PlatformAdmin(user_id=user.id))
            context.actor_id = user.id
            record(
                context,
                action=A_PLATFORM_ADMIN_CREATED,
                entity_type=ENTITY_PLATFORM_ADMIN,
                entity_id=user.id,
                metadata={"email_normalise": email_norm},
            )
            db.commit()
            print(f"OK : administrateur plateforme créé pour {email_norm}.")
        elif already_admin:
            record(
                context,
                action=A_PLATFORM_ADMIN_EXISTING,
                entity_type=ENTITY_PLATFORM_ADMIN,
                entity_id=user.id,
                metadata={"email_normalise": email_norm},
            )
            db.commit()
            print(f"OK : {email_norm} est déjà administrateur plateforme (aucune modification).")
        else:
            db.add(PlatformAdmin(user_id=user.id))
            context.actor_id = user.id
            record(
                context,
                action=A_PLATFORM_ADMIN_CREATED,
                entity_type=ENTITY_PLATFORM_ADMIN,
                entity_id=user.id,
                metadata={"email_normalise": email_norm},
            )
            db.commit()
            print(f"OK : {email_norm} est maintenant administrateur plateforme.")
        return 0
    except Exception as exc:  # noqa: BLE001 — bordure CLI : message, pas de traceback
        db.rollback()
        logger.exception("create-platform-admin : échec (code %s)", type(exc).__name__)
        print(f"ERREUR : {type(exc).__name__} (voir logs).", file=sys.stderr)
        return 1
    finally:
        db.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    p_admin = subparsers.add_parser(
        "create-platform-admin",
        help="Crée (ou confirme) le superadministrateur plateforme (D-14).",
    )
    p_admin.add_argument("--email", help="E-mail de l'administrateur (fallback : PLATFORM_ADMIN_EMAIL).")
    p_admin.add_argument(
        "--password",
        help="Mot de passe (fallback : PLATFORM_ADMIN_PASSWORD). Jamais durci dans les sources.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "create-platform-admin":
        return cmd_create_platform_admin(args.email, args.password)
    raise SystemExit(f"Commande inconnue : {args.command}")


if __name__ == "__main__":
    sys.exit(main())
