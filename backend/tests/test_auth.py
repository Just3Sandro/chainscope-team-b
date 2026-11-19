"""Tests de l'authentification (issue #5) — Postgres réel, httpx ASGI.

Scénarios couverts :

- **F01** : login (cookie + attributs D-04), /me, logout (204), /me 401,
  re-login (nouvelle session) ;
- sessions expirée / révoquée / altérée (T-10…T-14) ;
- **F16 / D-19** : CSRF manquant/faux/correct, exempt login, forgot-password
  exempt sans session mais exigé avec session ;
- **D-17** : shape exacte de /auth/me (clés, arrays vides, platform_admin,
  memberships) avec user double (tenant + client) ;
- forgot/reset : réponse neutre identique (T-21), e-mail capturé (D-12 mock),
  reset usage unique (T-18), expiration (T-19), révocation des sessions
  (T-11), politique mot de passe (DESIGN P1, message unique anti-oracle),
  confirmation divergente (422) ;
- **rate limit D-07** : 6ᵉ login < 60 s => 429 + Retry-After ; reset clippé
  par IP => 429 ;
- **F18** : audit complet sans aucun mot de passe / token dans
  ``metadata_json`` (assertion sur toutes les lignes) ;
- comptes suspendus (is_active=false) => 401 login et /me ;
- e-mail en majuscules au login (normalisation lower+trim).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.models import (
    ClientMembership,
    ClientMembershipRole,
    ClientOrg,
    PlatformAdmin,
    Tenant,
    TenantMembership,
    TenantMembershipRole,
    User,
)
from app.security import email as email_security
from app.security.passwords import PASSWORD_POLICY_MESSAGE, hash_password
from app.services import auth_service

API = "/api/v1"
DEV_PASSWORD = "Chainscope123"  # données de test fictives, conforme politique
NEW_PASSWORD = "Nouveau456789"
BASE_URL = "http://localhost:8080"  # défaut Settings.PUBLIC_BASE_URL (D-12)


# --- fixtures ---------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """État du limiteur (mémoire, D-07) purgé avant chaque test."""
    from app.security.rate_limit import get_rate_limiter

    get_rate_limiter().reset()
    yield


@pytest.fixture(autouse=True)
def _clean_auth_data(db):
    """Purge les données COMMITTÉES par la suite d'auth (les services
    committent : login, reset, audit) en fin de test — garantit que la
    base de test reste propre pour les tests suivants (dont le test
    migration destructif du socle, `test_migration_re_runnable`).
    TRUNCATE ... CASCADE : les tables dépendantes (sessions, memberships,
    platform_admins, password_reset_tokens) sont purgées avec."""
    yield
    db.execute(text("TRUNCATE TABLE audit_events, users, tenants CASCADE"))
    db.commit()


@pytest.fixture
def emails(monkeypatch) -> list[dict]:
    """Mock du transport e-mail (D-12) : capture les envois, pas de SMTP."""
    captured: list[dict] = []

    def fake_send_email(to: str, subject: str, body: str, token: str | None = None) -> None:
        captured.append({"to": to, "subject": subject, "body": body, "token": token})

    monkeypatch.setattr(email_security, "send_email", fake_send_email)
    return captured


def suffix() -> str:
    return uuid.uuid4().hex[:10]


def make_user(
    db,
    *,
    email: str | None = None,
    password: str = DEV_PASSWORD,
    active: bool = True,
    platform_admin: bool = False,
) -> User:
    user = User(
        email=email or f"user.{suffix()}@exemplif.fr",
        password_hash=hash_password(password),
        is_active=active,
    )
    db.add(user)
    db.flush()
    if platform_admin:
        db.add(PlatformAdmin(user_id=user.id))
    db.commit()
    return user


def make_double_membership(db, user: User) -> tuple[Tenant, ClientOrg]:
    """User double (D-17) : membership tenant (TENANT_ADMIN) + membership
    client (CLIENT_VIEWER) sur le même tenant."""
    s = suffix()
    tenant = Tenant(name=f"Tenant {s}", slug=f"tenant-{s}")
    db.add(tenant)
    db.flush()
    db.add(
        TenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantMembershipRole.TENANT_ADMIN
        )
    )
    org = ClientOrg(tenant_id=tenant.id, name=f"Org {s}")
    db.add(org)
    db.flush()
    db.add(
        ClientMembership(
            user_id=user.id, client_org_id=org.id, role=ClientMembershipRole.CLIENT_VIEWER
        )
    )
    db.commit()
    return tenant, org


async def login(client, email: str, password: str = DEV_PASSWORD):
    return await client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )


async def get_csrf(client) -> str:
    r = await client.get(f"{API}/auth/csrf")
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def session_cookie_of(response) -> str:
    value = response.cookies.get("cs_session")
    if value is None:
        raise AssertionError("cookie cs_session absent de la réponse")
    return value


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- F01 : cycle de vie de session -------------------------------------------
async def test_f01_login_me_logout_relogin(client, db) -> None:
    user = make_user(db)
    r1 = await login(client, user.email)
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["id"] == str(user.id)
    # Cookie posé avec attributs D-04 (T-14) — valeurs insensibles à la
    # casse (RFC 6265bis) ; starlette rend `SameSite=lax` en minuscule.
    # Path=/api (arbitrage Cyber T-14, PR #32 : le backend ne sert que
    # /api/v1 => portée du cookie strictement plus étroite que /).
    set_cookie = r1.headers["set-cookie"].lower()
    assert "cs_session=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api" in set_cookie
    token1 = session_cookie_of(r1)

    # /me OK
    rme = await client.get(f"{API}/auth/me")
    assert rme.status_code == 200
    assert rme.json()["email"] == user.email

    # logout : 204 avec CSRF correct (F16), cookie supprimé (Max-Age=0)
    csrf = await get_csrf(client)
    rlog = await client.post(
        f"{API}/auth/logout", headers={"X-CSRF-Token": csrf}
    )
    assert rlog.status_code == 204, rlog.text
    deleted = rlog.headers.get_list("set-cookie")
    assert any("cs_session" in c and "max-age=0" in c.lower() for c in deleted)

    # ancienne session refusée (T-10)
    rme2 = await client.get(f"{API}/auth/me")
    assert rme2.status_code == 401
    assert rme2.json()["error"]["code"] == "UNAUTHENTICATED"

    # re-login : nouvelle session valide (T-19 du cookie, pas du token)
    r2 = await login(client, user.email)
    assert r2.status_code == 200
    assert session_cookie_of(r2) != token1
    rme3 = await client.get(f"{API}/auth/me")
    assert rme3.status_code == 200


async def test_session_expired_rejected(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    db.execute(
        text("UPDATE sessions SET expires_at = :p WHERE user_id = :u"),
        {"p": utcnow() - timedelta(hours=1), "u": user.id},
    )
    db.commit()
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_session_revoked_rejected(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    db.execute(
        text("UPDATE sessions SET revoked_at = :p WHERE user_id = :u"),
        {"p": utcnow(), "u": user.id},
    )
    db.commit()
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401


async def test_session_altered_cookie_rejected(client, db) -> None:
    """Cookie falsifié (T-12) : le hash ne correspond à aucune session."""
    user = make_user(db)
    r = await client.get(
        f"{API}/auth/me",
        headers={"cookie": "cs_session=falsifie-" + "0" * 56},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    # (le compte existe bel et bien ; seul le cookie est invallide)
    assert user.id is not None


# --- F16 / D-19 : CSRF ---------------------------------------------------------
async def test_csrf_logout_missing_token_403(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    r = await client.post(f"{API}/auth/logout")
    assert r.status_code == 403
    error = r.json()["error"]
    assert error["code"] == "CSRF_INVALID"
    assert error["request_id"]
    # La session n'est PAS révoquée (refus avant traitement)
    rme = await client.get(f"{API}/auth/me")
    assert rme.status_code == 200


async def test_csrf_logout_wrong_token_403(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    r = await client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": "token-faux"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CSRF_INVALID"


async def test_csrf_logout_correct_token_204(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    csrf = await get_csrf(client)
    r = await client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 204
    # Rejouer le même jeton : la session est révoquée => plus de 403 CSRF,
    # mais 401 (états indiscernables, T-10/T-12).
    r2 = await client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r2.status_code == 401


async def test_csrf_login_exempt_without_token(client, db) -> None:
    """Exempt D-19 : POST /auth/login passe sans X-CSRF-Token (anonyme)."""
    user = make_user(db)
    r = await login(client, user.email)
    assert r.status_code == 200


async def test_csrf_forgot_exempt_without_session(client) -> None:
    r = await client.post(
        f"{API}/auth/forgot-password", json={"email": "inexistant@exemplif.fr"}
    )
    assert r.status_code == 200
    assert r.json()["code"] == "OK"


async def test_csrf_forgot_required_with_session(client, db, emails) -> None:
    """Exemption conditionnelle D-19 : avec une session active, le CSRF est
    exigé même sur forgot-password."""
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    r = await client.post(
        f"{API}/auth/forgot-password", json={"email": user.email}
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CSRF_INVALID"
    assert emails == []  # aucun e-mail envoyé (refusé avant le service)


async def test_csrf_rotation_invalidates_previous_token(client, db) -> None:
    user = make_user(db)
    assert (await login(client, user.email)).status_code == 200
    old = await get_csrf(client)
    new = await get_csrf(client)
    assert old != new
    r = await client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": old})
    assert r.status_code == 403
    r2 = await client.post(f"{API}/auth/logout", headers={"X-CSRF-Token": new})
    assert r2.status_code == 204


async def test_csrf_endpoint_unauthenticated_401(client) -> None:
    r = await client.get(f"{API}/auth/csrf")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"


# --- D-17 : contrat exact de /auth/me ------------------------------------------
async def test_d17_me_shape_user_double_tenant_client(client, db) -> None:
    user = make_user(db)
    tenant, org = make_double_membership(db, user)
    r = await login(client, user.email)
    assert r.status_code == 200
    body = r.json()
    # Clés exactes (D-17)
    assert set(body) == {
        "id",
        "email",
        "is_active",
        "platform_admin",
        "tenant_memberships",
        "client_memberships",
    }
    assert body["id"] == str(user.id)
    assert body["email"] == user.email
    assert body["is_active"] is True
    assert body["platform_admin"] is False
    # Membership tenant (nom/slug/rôle joints, D-17)
    assert len(body["tenant_memberships"]) == 1
    tm = body["tenant_memberships"][0]
    assert set(tm) == {"tenant_id", "tenant_name", "slug", "role"}
    assert tm["tenant_id"] == str(tenant.id)
    assert tm["tenant_name"] == tenant.name
    assert tm["slug"] == tenant.slug
    assert tm["role"] == "TENANT_ADMIN"
    # Membership client (client_org_name/tenant_id joints, D-17)
    assert len(body["client_memberships"]) == 1
    cm = body["client_memberships"][0]
    assert set(cm) == {"client_org_id", "client_org_name", "tenant_id"}
    assert cm["client_org_id"] == str(org.id)
    assert cm["client_org_name"] == org.name
    assert cm["tenant_id"] == str(tenant.id)
    # Même forme via /auth/me (contrat identique)
    rme = await client.get(f"{API}/auth/me")
    assert rme.status_code == 200
    assert rme.json() == body


async def test_d17_me_empty_arrays_and_platform_admin(client, db) -> None:
    """Arrays vides => [] (jamais null) ; platform_admin booléen vrai."""
    user = make_user(db, platform_admin=True)
    r = await login(client, user.email)
    assert r.status_code == 200
    body = r.json()
    assert body["platform_admin"] is True
    assert body["tenant_memberships"] == []
    assert body["client_memberships"] == []
    # Un simple user (non admin plateforme) : platform_admin false
    plain = make_user(db)
    r2 = await client.post(
        f"{API}/auth/login", json={"email": plain.email, "password": DEV_PASSWORD}
    )
    assert r2.json()["platform_admin"] is False


# --- forgot / reset -------------------------------------------------------------
async def test_forgot_unknown_email_neutral_no_email_no_audit(client, db, emails) -> None:
    db.execute(text("DELETE FROM audit_events"))
    db.commit()
    r = await client.post(
        f"{API}/auth/forgot-password", json={"email": "fantome@exemplif.fr"}
    )
    assert r.status_code == 200
    assert r.json()["code"] == "OK"
    assert "si un compte existe" in r.json()["message"].lower()
    assert emails == []  # pas d'e-mail
    rows = db.execute(text("SELECT action FROM audit_events")).all()
    assert rows == []  # pas d'audit (T-21)


async def test_forgot_known_email_identical_response_and_link(
    client, db, emails
) -> None:
    """T-21 : réponse IDENTIQUE connu/inconnu + e-mail avec lien complet."""
    db.execute(text("DELETE FROM audit_events"))
    db.commit()
    user = make_user(db)
    r_unknown = await client.post(
        f"{API}/auth/forgot-password", json={"email": "fantome@exemplif.fr"}
    )
    r_known = await client.post(
        f"{API}/auth/forgot-password", json={"email": user.email}
    )
    assert r_unknown.status_code == r_known.status_code == 200
    assert r_unknown.json() == r_known.json()  # corps strictement identiques
    assert len(emails) == 1
    sent = emails[0]
    assert sent["to"] == user.email
    token = sent["token"]
    assert len(token) >= 32  # entropie >= 256 bits (T-20)
    assert f"{BASE_URL}/reset?token={token}" in sent["body"]  # lien complet (D-12)
    # audit password.reset_requested présent, sans secret (F18)
    rows = db.execute(
        text("SELECT action, metadata_json FROM audit_events")
    ).all()
    assert [a for a, _ in rows] == ["password.reset_requested"]
    dump = json.dumps(rows, ensure_ascii=False, default=str)
    assert token not in dump and DEV_PASSWORD not in dump


async def test_reset_password_success_revokes_sessions(client, db, emails) -> None:
    """T-11/T-18 : reset OK => anciennes sessions révoquées, nouveau mot
    de passe actif, token consommé."""
    user = make_user(db)
    r_login = await login(client, user.email)
    assert r_login.status_code == 200
    old_cookie = session_cookie_of(r_login)

    # Session active => forgot-password exige le CSRF (D-19)
    csrf = await get_csrf(client)
    r_forgot = await client.post(
        f"{API}/auth/forgot-password",
        json={"email": user.email},
        headers={"X-CSRF-Token": csrf},
    )
    assert r_forgot.status_code == 200
    token = emails[0]["token"]

    r_reset = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
    )
    assert r_reset.status_code == 200, r_reset.text
    assert r_reset.json()["code"] == "OK"

    # Ancienne session révoquée (T-11)
    r_me = await client.get(f"{API}/auth/me")
    assert r_me.status_code == 401
    assert old_cookie  # rappel : le cookie est mort côté serveur

    # Vieux mot de passe rejeté, nouveau accepté
    r_old = await client.post(
        f"{API}/auth/login", json={"email": user.email, "password": DEV_PASSWORD}
    )
    assert r_old.status_code == 401
    r_new = await client.post(
        f"{API}/auth/login", json={"email": user.email, "password": NEW_PASSWORD}
    )
    assert r_new.status_code == 200
    # Token consommé : rejoué => 400 générique (T-18)
    r_replay = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "password": "Rejouer98765", "password_confirmation": "Rejouer98765"},
    )
    assert r_replay.status_code == 400
    assert r_replay.json()["error"]["code"] == "INVALID_TOKEN"


async def test_reset_token_expired_rejected(client, db, emails) -> None:
    user = make_user(db)
    r = await client.post(
        f"{API}/auth/forgot-password", json={"email": user.email}
    )
    assert r.status_code == 200
    token = emails[0]["token"]
    db.execute(
        text("UPDATE password_reset_tokens SET expires_at = :p WHERE user_id = :u"),
        {"p": utcnow() - timedelta(minutes=1), "u": user.id},
    )
    db.commit()
    r2 = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
    )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "INVALID_TOKEN"
    assert r2.json()["error"]["message"] == auth_service.MSG_INVALID_RESET_LINK
    # Mot de passe inchangé
    assert (await login(client, user.email)).status_code == 200


async def test_reset_unknown_token_rejected(client, db) -> None:
    r = await client.post(
        f"{API}/auth/reset-password",
        json={
            "token": "inexistant-" + "a" * 40,
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


async def test_reset_policy_rejected_422_single_message(client, db, emails) -> None:
    """DESIGN P1 (contrat figé) : 422 avec le MÊME message unique, quelle
    que soit la règle en défaut (anti-oracle)."""
    user = make_user(db)
    await client.post(f"{API}/auth/forgot-password", json={"email": user.email})
    token = emails[0]["token"]
    weak = ["Abcdefg1234"[:9], "abcde12345", "ABCDE12345"]  # court / pas maj / pas min
    messages = set()
    for password in weak:
        r = await client.post(
            f"{API}/auth/reset-password",
            json={"token": token, "password": password, "password_confirmation": password},
        )
        assert r.status_code == 422, r.text
        assert r.json()["error"]["message"] == PASSWORD_POLICY_MESSAGE
        messages.add(r.json()["error"]["message"])
    assert messages == {PASSWORD_POLICY_MESSAGE}
    # Le token reste utilisable (le reset a échoué avant consommation)
    r_ok = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
    )
    assert r_ok.status_code == 200


async def test_reset_confirmation_mismatch_422(client, db, emails) -> None:
    user = make_user(db)
    await client.post(f"{API}/auth/forgot-password", json={"email": user.email})
    token = emails[0]["token"]
    r = await client.post(
        f"{API}/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD, "password_confirmation": "Diverge98765"},
    )
    assert r.status_code == 422
    # Schéma invalide => corps normalisé (code VALIDATION, 422)
    assert "error" in r.json()


# --- rate limiting (D-07, T-24/T-25) ---------------------------------------------
async def test_rate_limit_login_sixth_request_429(client, db) -> None:
    user = make_user(db)
    for i in range(5):
        r = await login(client, user.email)
        assert r.status_code == 200, f"login {i} : {r.text}"
    r6 = await login(client, user.email)
    assert r6.status_code == 429
    error = r6.json()["error"]
    assert error["code"] == "RATE_LIMITED"
    retry_after = r6.headers.get("Retry-After")
    assert retry_after is not None and int(retry_after) >= 1
    # Autre e-mail, même IP : non affecté (clé e-mail+IP, D-07)
    other = make_user(db)
    r_other = await login(client, other.email)
    assert r_other.status_code == 200


async def test_rate_limit_reset_password_ip_clamped(client, db, emails) -> None:
    """Clé par IP (reset) : 5 essais + 6ᵉ => 429, indépendamment du token."""
    user = make_user(db)
    await client.post(f"{API}/auth/forgot-password", json={"email": user.email})
    fake = "fictif-" + "b" * 40
    for i in range(5):
        r = await client.post(
            f"{API}/auth/reset-password",
            json={"token": fake, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
        )
        assert r.status_code == 400, f"essai {i} : {r.text}"
    r6 = await client.post(
        f"{API}/auth/reset-password",
        json={"token": fake, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
    )
    assert r6.status_code == 429
    assert r6.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r6.headers["Retry-After"]) >= 1


# --- F18 : audit sans secrets -------------------------------------------------------
async def test_f18_audit_actions_without_secrets(client, db, emails) -> None:
    """Après login+failure+reset : actions présentes, et AUCUN mot de passe
    ni token dans metadata_json (assertion sur toutes les lignes)."""
    db.execute(text("DELETE FROM audit_events"))
    db.commit()
    user = make_user(db)

    r1 = await login(client, user.email)
    assert r1.status_code == 200
    session_cookie = session_cookie_of(r1)
    r_fail = await client.post(
        f"{API}/auth/login", json={"email": user.email, "password": "Mauvais98765"}
    )
    assert r_fail.status_code == 401
    csrf = await get_csrf(client)
    r_forgot = await client.post(
        f"{API}/auth/forgot-password",
        json={"email": user.email},
        headers={"X-CSRF-Token": csrf},
    )
    assert r_forgot.status_code == 200
    reset_token = emails[0]["token"]
    r_reset = await client.post(
        f"{API}/auth/reset-password",
        json={"token": reset_token, "password": NEW_PASSWORD, "password_confirmation": NEW_PASSWORD},
    )
    assert r_reset.status_code == 200

    rows = db.execute(
        text(
            "SELECT action, actor_id, metadata_json FROM audit_events ORDER BY created_at, action"
        )
    ).all()
    actions = [r.action for r in rows]
    for expected in (
        "login.success",
        "login.failure",
        "password.reset_requested",
        "password.reset",
    ):
        assert expected in actions, f"{expected} absent de {actions}"
    # Ni mot de passe, ni token, ni cookie de session dans AUCUNE ligne (F18)
    secrets = [DEV_PASSWORD, NEW_PASSWORD, "Mauvais98765", reset_token, session_cookie]
    for row in rows:
        dump = json.dumps(row.metadata_json, ensure_ascii=False, default=str)
        for secret in secrets:
            assert secret not in dump, f"secret dans audit ({row.action})"
    # L'échec de login porte l'acteur connu (e-mail du compte existant)
    failure = [r for r in rows if r.action == "login.failure"]
    assert len(failure) == 1
    assert failure[0].actor_id == user.id


async def test_login_unknown_email_failure_actor_null(client, db) -> None:
    """E-mail inconnu : 401 générique + audit login.failure SANS acteur
    (migration 0002) et métadonnée email_normalise — jamais de mot de
    passe (F18)."""
    db.execute(text("DELETE FROM audit_events"))
    db.commit()
    r = await client.post(
        f"{API}/auth/login",
        json={"email": "fantome@exemplif.fr", "password": "Mystere12345"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    rows = db.execute(
        text("SELECT actor_id, metadata_json FROM audit_events WHERE action = 'login.failure'")
    ).all()
    assert len(rows) == 1
    assert rows[0].actor_id is None
    assert rows[0].metadata_json == {"email_normalise": "fantome@exemplif.fr"}
    dump = json.dumps(rows[0].metadata_json, ensure_ascii=False)
    assert "Mystere12345" not in dump


# --- comptes suspendus / normalisation e-mail ---------------------------------------
async def test_inactive_user_login_and_me_401(client, db) -> None:
    """D-17 : compte suspendu = non connecté (login 401, /me 401, aucune
    fuite d'existence)."""
    user = make_user(db, active=False)
    r = await login(client, user.email)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"
    # Session créée en direct en base (contournement du login) : /me 401
    from app.config import get_settings
    from app.security import sessions as session_security

    session_row, token = session_security.create_session(db, user.id, get_settings())
    db.commit()
    r_me = await client.get(f"{API}/auth/me", headers={"cookie": f"cs_session={token}"})
    assert r_me.status_code == 401
    assert session_row.user_id == user.id


async def test_login_email_uppercase_normalized(client, db) -> None:
    """Normalisation lower+trim (issue #5) : ' BOB.CASE@Exemplif.FR ' accepté."""
    user = make_user(db, email="Bob.Case@ExempliF.fr")
    assert user.email == "bob.case@exemplif.fr"  # invariant du modèle
    r = await login(client, "  BOB.CASE@EXEMPLIF.FR  ")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "bob.case@exemplif.fr"
    assert r.json()["email"] == "bob.case@exemplif.fr"


async def test_login_invalid_email_body_422(client, db) -> None:
    r = await client.post(
        f"{API}/auth/login", json={"email": "pas-un-email", "password": DEV_PASSWORD}
    )
    assert r.status_code == 422
    assert "error" in r.json()


async def test_login_extra_field_rejected_422(client, db) -> None:
    """T-45 (mass assignment) : les schémas d'écriture ignorent/refusent
    les champs inattendus (extra=forbid)."""
    user = make_user(db)
    r = await client.post(
        f"{API}/auth/login",
        json={"email": user.email, "password": DEV_PASSWORD, "role": "PLATFORM_ADMIN"},
    )
    assert r.status_code == 422
