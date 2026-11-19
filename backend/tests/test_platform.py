"""Tests de la plateforme — tenants (issue #7) : Postgres réel, httpx ASGI.

Scénarios couverts :

- **GET /platform/tenants** : 200 + compteurs agrégés lecture seule
  (``member_count`` minimal, issue #27 pour le reste), pagination D-11
  (limit=1, bornes), **aucune donnée métier** (absence findings/assets/
  client_names), 403 pour TENANT_ADMIN/PENTESTER/CLIENT_VIEWER,
  401 sans session ;
- **POST /platform/tenants** : 201 + invitation ``TENANT_ADMIN`` créée
  (1 ligne, ``tenant_id``/``role`` corrects, token 256 bits haché,
  expiration ``INVITATION_LIFETIME_HOURS``) + e-mail capturé (mock D-12,
  lien ``/invite`` complet) ; 422 slug invalide / e-mail invalide / nom
  vide / champs inattendus (mass assignment, THREAT_MODEL T-45) ;
  409 slug dupliqué ; 403 non-plateforme ; 403 CSRF manquant (D-05) ;
- **PATCH /platform/tenants/{id}** : suspension 200 + audit
  ``platform.tenant.suspended``, réactivation + audit
  ``platform.tenant.reactivated``, idempotence (pas d'audit si état
  inchangé), 422 body vide, 404 inconnu, 403 PENTESTER ;
- **F18** : audit plateforme sans token d'invitation ni mot de passe.

Setup par test : 1 platform admin, 2 tenants (données fictives).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.config import get_settings
from app.models import (
    ClientMembership,
    ClientMembershipRole,
    ClientOrg,
    Engagement,
    PlatformAdmin,
    Tenant,
    TenantMembership,
    TenantMembershipRole,
    User,
)
from app.security import email as email_security
from app.security.passwords import hash_password

API = "/api/v1"
DEV_PASSWORD = "Chainscope123"  # données de test fictives, conforme politique
BASE_URL = "http://localhost:8080"  # défaut Settings.PUBLIC_BASE_URL (D-12)

#: Champs interdits dans la liste plateforme (spec §1 : pas de lecture
#: métier) — assertion sur le corps JSON complet.
FORBIDDEN_BUSINESS_KEYS = ("findings", "assets", "client_names")
EXPECTED_ITEM_KEYS = {
    "id",
    "name",
    "slug",
    "is_active",
    "created_at",
    "member_count",
    "client_org_count",
    "engagement_count",
}


# --- fixtures ---------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """État du limiteur (mémoire, D-07) purgé avant chaque test
    (les logins de fixture compteraient sinon)."""
    from app.security.rate_limit import get_rate_limiter

    get_rate_limiter().reset()
    yield


@pytest.fixture(autouse=True)
def _clean_platform_data(db):
    """Purge les données COMMITTÉES par la suite (les services committent :
    création/suspension de tenant, invitations, audit) — garantit que la
    base de test reste propre pour les tests suivants."""
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
    platform_admin: bool = False,
) -> User:
    user = User(
        email=email or f"user.{suffix()}@exemplif.fr",
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    if platform_admin:
        db.add(PlatformAdmin(user_id=user.id))
    db.commit()
    return user


def make_membership(db, user: User, tenant: Tenant, role: TenantMembershipRole):
    db.add(
        TenantMembership(user_id=user.id, tenant_id=tenant.id, role=role)
    )
    db.commit()


def make_client_viewer(db, user: User, tenant: Tenant) -> None:
    """Membership CLIENT_VIEWER sur le tenant (pour le test 403 rôle client)."""
    org = ClientOrg(tenant_id=tenant.id, name=f"Org {suffix()}")
    db.add(org)
    db.flush()
    db.add(
        ClientMembership(
            user_id=user.id,
            client_org_id=org.id,
            role=ClientMembershipRole.CLIENT_VIEWER,
        )
    )
    db.commit()


def build_two_tenants(db) -> tuple[Tenant, Tenant]:
    """2 tenants avec compteurs connus :
    - A : 2 memberships, 1 client_org, 1 engagement ;
    - B : 1 membership, 0 client_org, 0 engagement."""
    s = suffix()
    tenant_a = Tenant(name=f"Cabinet {s} A", slug=f"cabinet-{s}-a")
    tenant_b = Tenant(name=f"Cabinet {s} B", slug=f"cabinet-{s}-b")
    db.add_all([tenant_a, tenant_b])
    db.flush()
    user_a1 = make_user(db)
    user_a2 = make_user(db)
    make_membership(db, user_a1, tenant_a, TenantMembershipRole.TENANT_ADMIN)
    make_membership(db, user_a2, tenant_a, TenantMembershipRole.PENTESTER)
    make_membership(db, user_a1, tenant_b, TenantMembershipRole.PENTESTER)
    org_a = ClientOrg(tenant_id=tenant_a.id, name=f"Client {s}")
    db.add(org_a)
    db.flush()
    db.add(
        Engagement(
            tenant_id=tenant_a.id,
            client_org_id=org_a.id,
            name=f"Mission {s}",
            scope="périmètre fictif de test",
        )
    )
    db.commit()
    return tenant_a, tenant_b


async def login(client, email: str, password: str = DEV_PASSWORD):
    r = await client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r


async def get_csrf(client) -> str:
    r = await client.get(f"{API}/auth/csrf")
    assert r.status_code == 200, r.text
    return r.json()["csrf_token"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def audit_actions(db) -> list[str]:
    rows = db.execute(text("SELECT action FROM audit_events")).all()
    return [r[0] for r in rows]


# --- GET /platform/tenants ----------------------------------------------------
@pytest.mark.asyncio
async def test_list_tenants_200_counters_no_business_fields(client, db) -> None:
    """200 + compteurs agrégés ; AUCUN champ métier (spec §1, T-05)."""
    platform = make_user(db, platform_admin=True)
    tenant_a, tenant_b = build_two_tenants(db)
    await login(client, platform.email)

    r = await client.get(f"{API}/platform/tenants")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"items", "limit", "offset", "total"}
    assert body["total"] == 2
    assert body["limit"] == get_settings().PAGINATION_DEFAULT_LIMIT
    assert body["offset"] == 0

    items = body["items"]
    assert len(items) == 2
    by_slug = {i["slug"]: i for i in items}
    assert set(by_slug) == {tenant_a.slug, tenant_b.slug}
    item_a, item_b = by_slug[tenant_a.slug], by_slug[tenant_b.slug]
    for item in (item_a, item_b):
        assert set(item) == EXPECTED_ITEM_KEYS
    assert item_a["member_count"] == 2
    assert item_a["client_org_count"] == 1
    assert item_a["engagement_count"] == 1
    assert item_a["is_active"] is True
    assert uuid.UUID(item_a["id"]) == tenant_a.id
    assert item_b["member_count"] == 1
    assert item_b["client_org_count"] == 0
    assert item_b["engagement_count"] == 0
    # created_at présent (contrat issue #7) et cohérent
    datetime.fromisoformat(item_a["created_at"])
    # Aucune donnée métier : ni finding, ni actif, ni client par nom
    dump = json.dumps(body, ensure_ascii=False)
    for forbidden in FORBIDDEN_BUSINESS_KEYS:
        assert forbidden not in dump, f"champ métier interdit présent : {forbidden}"
    assert "Client " not in dump  # le nom du client_org ne fuite pas


@pytest.mark.asyncio
async def test_list_tenants_pagination_limit_1_and_bounds(client, db) -> None:
    """D-11 : limit=1 -> 1 item (total conservé) ; bornes 422."""
    platform = make_user(db, platform_admin=True)
    build_two_tenants(db)
    await login(client, platform.email)

    r1 = await client.get(f"{API}/platform/tenants", params={"limit": 1, "offset": 0})
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert len(body1["items"]) == 1
    assert body1["total"] == 2

    r2 = await client.get(f"{API}/platform/tenants", params={"limit": 1, "offset": 1})
    assert r2.status_code == 200
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] != body1["items"][0]["id"]

    for bad in (
        {"limit": 101},  # > PAGINATION_MAX_LIMIT (D-11)
        {"limit": 0},
        {"offset": -1},
    ):
        r = await client.get(f"{API}/platform/tenants", params=bad)
        assert r.status_code == 422, f"{bad} : {r.text}"
        assert r.json()["error"]["request_id"]


@pytest.mark.asyncio
async def test_list_tenants_403_non_platform_roles_and_401(client, db) -> None:
    """TENANT_ADMIN / PENTESTER / CLIENT_VIEWER => 403 FORBIDDEN ;
    sans session => 401 UNAUTHENTICATED (spec §1, issue #7)."""
    tenant_a, _tenant_b = build_two_tenants(db)
    admin = make_user(db)
    make_membership(db, admin, tenant_a, TenantMembershipRole.TENANT_ADMIN)
    pentester = make_user(db)
    make_membership(db, pentester, tenant_a, TenantMembershipRole.PENTESTER)
    viewer = make_user(db)
    make_client_viewer(db, viewer, tenant_a)

    # Non connecté
    r = await client.get(f"{API}/platform/tenants")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"

    for user in (admin, pentester, viewer):
        await login(client, user.email)
        r = await client.get(f"{API}/platform/tenants")
        assert r.status_code == 403, f"{user.email} : {r.text}"
        assert r.json()["error"]["code"] == "FORBIDDEN"


# --- POST /platform/tenants ----------------------------------------------------
@pytest.mark.asyncio
async def test_create_tenant_201_invitation_email_audit(client, db, emails) -> None:
    """201 + invitation TENANT_ADMIN (1 ligne, tenant correct, token 256 bits
    haché, expiration) + e-mail capturé (lien /invite) + audit F18."""
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    csrf = await get_csrf(client)

    s = suffix()
    admin_email = f"Boss.{s}@Exemplif.FR"  # normalisé en minuscules
    r = await client.post(
        f"{API}/platform/tenants",
        json={"name": f"Cabinet {s}", "slug": f"cabinet-{s}", "admin_email": admin_email},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "name", "slug", "is_active", "created_at"}
    assert body["name"] == f"Cabinet {s}"
    assert body["slug"] == f"cabinet-{s}"
    assert body["is_active"] is True
    datetime.fromisoformat(body["created_at"])
    tenant_id = uuid.UUID(body["id"])

    # Invitation : 1 ligne, tenant correct, rôle TENANT_ADMIN, e-mail normalisé
    rows = db.execute(
        text("SELECT email, role, tenant_id, token_hash, expires_at, consumed_at"
             " FROM invitations")
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.email == admin_email.lower()
    assert row.role == "TENANT_ADMIN"
    assert row.tenant_id == tenant_id
    assert row.consumed_at is None
    assert len(row.token_hash) == 64  # SHA-256
    # Expiration = now + INVITATION_LIFETIME_HOURS (±5 min)
    expected = timedelta(hours=get_settings().INVITATION_LIFETIME_HOURS)
    assert abs((row.expires_at - utcnow()) - expected) < timedelta(minutes=5)

    # E-mail capturé (mock D-12) : lien /invite complet, token 256 bits
    assert len(emails) == 1
    sent = emails[0]
    assert sent["to"] == admin_email.lower()
    token = sent["token"]
    assert token is not None and len(token) >= 32  # urlsafe de 256 bits (T-20)
    assert f"{BASE_URL}/invite?token={token}" in sent["body"]
    # Le token haché correspond à celui de l'e-mail (pas de fuite du clair)
    from app.security.sessions import hash_token

    assert row.token_hash == hash_token(token)

    # Audit : platform.tenant.created, acteur = platform admin, sans secret
    audit_rows = db.execute(
        text(
            "SELECT entity_type, entity_id, actor_id, metadata_json"
            " FROM audit_events WHERE action = 'platform.tenant.created'"
        )
    ).all()
    assert len(audit_rows) == 1
    a = audit_rows[0]
    assert a.entity_type == "tenant"
    assert a.entity_id == tenant_id
    assert a.actor_id == platform.id
    assert a.metadata_json == {"slug": f"cabinet-{s}", "admin_email": admin_email.lower()}
    assert token not in json.dumps(a.metadata_json, default=str)


@pytest.mark.asyncio
async def test_create_tenant_invalid_slug_422(client, db, emails) -> None:
    """Slug hors `^[a-z0-9-]{2,64}$` => 422, aucun effet de bord."""
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    for bad_slug in ("a", "AB-c", "mauvais slug", "x" * 65, "ok_underscore"):
        r = await client.post(
            f"{API}/platform/tenants",
            json={"name": "Cabinet X", "slug": bad_slug, "admin_email": f"admin.{suffix()}@exemplif.fr"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422, f"slug={bad_slug!r} : {r.text}"
        assert r.json()["error"]["code"] == "VALIDATION"
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 0
    assert emails == []


@pytest.mark.asyncio
async def test_create_tenant_invalid_admin_email_422(client, db, emails) -> None:
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    r = await client.post(
        f"{API}/platform/tenants",
        json={"name": "Cabinet X", "slug": f"cabinet-{suffix()}", "admin_email": "pas-un-email"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 422
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 0
    assert emails == []


@pytest.mark.asyncio
async def test_create_tenant_blank_name_422(client, db) -> None:
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    for bad_name in ("", "   "):
        r = await client.post(
            f"{API}/platform/tenants",
            json={"name": bad_name, "slug": f"cabinet-{suffix()}", "admin_email": f"admin.{suffix()}@exemplif.fr"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422, f"name={bad_name!r} : {r.text}"


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug_409(client, db, emails) -> None:
    """Slug existant => 409 CONFLICT, aucun tenant/invitation créée."""
    platform = make_user(db, platform_admin=True)
    tenant_a, _ = build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    r = await client.post(
        f"{API}/platform/tenants",
        json={"name": "Autre nom", "slug": tenant_a.slug, "admin_email": f"admin.{suffix()}@exemplif.fr"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["code"] == "CONFLICT"
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 2
    assert db.execute(text("SELECT count(*) FROM invitations")).scalar_one() == 0
    assert emails == []


@pytest.mark.asyncio
async def test_create_tenant_mass_assignment_422(client, db, emails) -> None:
    """THREAT_MODEL T-45 : `role`, `tenant_id`, `is_active`, `created_at`
    injectés dans le body => 422 (schéma `extra="forbid"`) ; rien n'est
    créé."""
    platform = make_user(db, platform_admin=True)
    s = suffix()
    await login(client, platform.email)
    csrf = await get_csrf(client)
    for extra in (
        {"role": "PLATFORM_ADMIN"},
        {"tenant_id": str(uuid.uuid4())},
        {"is_active": False},
        {"created_at": "2020-01-01T00:00:00Z"},
    ):
        payload = {
            "name": f"Cabinet {s}",
            "slug": f"cabinet-{s}",
            "admin_email": f"admin.{s}@exemplif.fr",
            **extra,
        }
        r = await client.post(
            f"{API}/platform/tenants",
            json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422, f"champ inattendu {extra} : {r.text}"
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 0
    assert emails == []


@pytest.mark.asyncio
async def test_create_tenant_403_tenant_admin_and_pentester(client, db) -> None:
    """Non-plateforme => 403 FORBIDDEN, aucun tenant créé."""
    tenant_a, _ = build_two_tenants(db)
    admin = make_user(db)
    make_membership(db, admin, tenant_a, TenantMembershipRole.TENANT_ADMIN)
    pentester = make_user(db)
    make_membership(db, pentester, tenant_a, TenantMembershipRole.PENTESTER)
    s = suffix()

    for user in (admin, pentester):
        await login(client, user.email)
        csrf = await get_csrf(client)
        r = await client.post(
            f"{API}/platform/tenants",
            json={"name": f"Cabinet {s}", "slug": f"cabinet-{s}", "admin_email": f"admin.{s}@exemplif.fr"},
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 403, f"{user.email} : {r.text}"
        assert r.json()["error"]["code"] == "FORBIDDEN"
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 2


@pytest.mark.asyncio
async def test_create_tenant_csrf_missing_403(client, db, emails) -> None:
    """Mutation plateforme non exemptée (D-05) : sans X-CSRF-Token =>
    403 CSRF_INVALID, rien n'est créé."""
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    s = suffix()
    r = await client.post(
        f"{API}/platform/tenants",
        json={"name": f"Cabinet {s}", "slug": f"cabinet-{s}", "admin_email": f"admin.{s}@exemplif.fr"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "CSRF_INVALID"
    assert db.execute(text("SELECT count(*) FROM tenants")).scalar_one() == 0
    assert emails == []


# --- PATCH /platform/tenants/{tenant_id} ---------------------------------------
@pytest.mark.asyncio
async def test_suspend_tenant_200_and_audit(client, db) -> None:
    """PATCH is_active=false => 200 + tenant suspendu + audit
    platform.tenant.suspended (acteur plateforme)."""
    platform = make_user(db, platform_admin=True)
    tenant_a, _ = build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)

    r = await client.patch(
        f"{API}/platform/tenants/{tenant_a.id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"id", "name", "slug", "is_active", "created_at"}
    assert body["is_active"] is False
    assert body["id"] == str(tenant_a.id)
    # État persisté (expire_all : la session de test ne sert pas l'objet en
    # mémoire avant le commit de la route API)
    db.expire_all()
    assert db.get(Tenant, tenant_a.id).is_active is False
    # Audit
    rows = db.execute(
        text(
            "SELECT entity_type, entity_id, actor_id, metadata_json"
            " FROM audit_events WHERE action = 'platform.tenant.suspended'"
        )
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.entity_type == "tenant"
    assert row.entity_id == tenant_a.id
    assert row.actor_id == platform.id
    assert row.metadata_json == {"slug": tenant_a.slug, "is_active": False}
    # La liste plateforme reflète l'état suspendu
    r_list = await client.get(f"{API}/platform/tenants")
    item = next(i for i in r_list.json()["items"] if i["id"] == str(tenant_a.id))
    assert item["is_active"] is False


@pytest.mark.asyncio
async def test_reactivate_tenant_200_and_audit(client, db) -> None:
    """Suspension puis réactivation => audit platform.tenant.reactivated,
    état actif restauré."""
    platform = make_user(db, platform_admin=True)
    tenant_a, _ = build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)

    r1 = await client.patch(
        f"{API}/platform/tenants/{tenant_a.id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert r1.status_code == 200
    r2 = await client.patch(
        f"{API}/platform/tenants/{tenant_a.id}",
        json={"is_active": True},
        headers={"X-CSRF-Token": await get_csrf(client)},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["is_active"] is True
    db.expire_all()
    assert db.get(Tenant, tenant_a.id).is_active is True
    actions = await audit_actions(db)
    assert "platform.tenant.suspended" in actions
    assert "platform.tenant.reactivated" in actions


@pytest.mark.asyncio
async def test_patch_same_value_noop_without_audit(client, db) -> None:
    """PATCH avec la valeur courante : 200 idempotent, AUCUN audit
    (comportement documenté — l'audit journalise un changement d'état)."""
    platform = make_user(db, platform_admin=True)
    tenant_a, _ = build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)

    r = await client.patch(
        f"{API}/platform/tenants/{tenant_a.id}",
        json={"is_active": True},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is True
    assert "platform.tenant.suspended" not in await audit_actions(db)
    assert "platform.tenant.reactivated" not in await audit_actions(db)


@pytest.mark.asyncio
async def test_patch_empty_body_422(client, db) -> None:
    """Body vide ou sans `is_active` => 422 ; tenant inchangé."""
    platform = make_user(db, platform_admin=True)
    tenant_a, _ = build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    for payload in ({}, {"autre_champ": True}):
        r = await client.patch(
            f"{API}/platform/tenants/{tenant_a.id}",
            json=payload,
            headers={"X-CSRF-Token": csrf},
        )
        assert r.status_code == 422, f"{payload} : {r.text}"
    db.expire_all()
    assert db.get(Tenant, tenant_a.id).is_active is True


@pytest.mark.asyncio
async def test_patch_unknown_tenant_404(client, db) -> None:
    platform = make_user(db, platform_admin=True)
    build_two_tenants(db)
    await login(client, platform.email)
    csrf = await get_csrf(client)
    r = await client.patch(
        f"{API}/platform/tenants/{uuid.uuid4()}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_patch_pentester_403(client, db) -> None:
    """PENTESTER => 403 FORBIDDEN, état inchangé."""
    tenant_a, _ = build_two_tenants(db)
    pentester = make_user(db)
    make_membership(db, pentester, tenant_a, TenantMembershipRole.PENTESTER)
    await login(client, pentester.email)
    csrf = await get_csrf(client)
    r = await client.patch(
        f"{API}/platform/tenants/{tenant_a.id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"
    db.expire_all()
    assert db.get(Tenant, tenant_a.id).is_active is True


# --- F18 : audit plateforme sans secret ------------------------------------------
@pytest.mark.asyncio
async def test_platform_audit_no_secrets_f18(client, db, emails) -> None:
    """Aucun token d'invitation ni mot de passe dans AUCUNE ligne d'audit
    (assertion sur toutes les métadonnées — F18/T-23/T-47)."""
    platform = make_user(db, platform_admin=True)
    await login(client, platform.email)
    csrf = await get_csrf(client)

    s = suffix()
    r = await client.post(
        f"{API}/platform/tenants",
        json={"name": f"Cabinet {s}", "slug": f"cabinet-{s}", "admin_email": f"admin.{s}@exemplif.fr"},
        headers={"X-CSRF-Token": csrf},
    )
    assert r.status_code == 201
    tenant_id = uuid.UUID(r.json()["id"])
    await client.patch(
        f"{API}/platform/tenants/{tenant_id}",
        json={"is_active": False},
        headers={"X-CSRF-Token": await get_csrf(client)},
    )
    invitation_token = emails[0]["token"]

    rows = db.execute(text("SELECT action, metadata_json FROM audit_events")).all()
    assert len(rows) >= 2
    for row in rows:
        dump = json.dumps(row.metadata_json, ensure_ascii=False, default=str)
        assert invitation_token not in dump, f"token dans l'audit ({row.action})"
        assert DEV_PASSWORD not in dump, f"mot de passe dans l'audit ({row.action})"
    actions = [r.action for r in rows]
    assert "platform.tenant.created" in actions
    assert "platform.tenant.suspended" in actions
