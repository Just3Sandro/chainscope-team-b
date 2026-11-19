# ChainScope V2 — Threat Model (Équipe B)

**Rôle auteur :** Expert Cyber · **Statut :** v1.0 — gelé pour le développement, à mettre à jour à chaque PR sensible
**Références normatives :** `01_SPECIFICATIONS_ET_ARCHITECTURE.md` (§1, §4, §5, §6, §8), `02_PLAN_DE_TEST_ET_SECURITE.md` (F01–F20, §3), `03_ROLES_ET_HANDOFFS.md`, issue #3.
**Règles de lecture :** aucune affirmation de conformité sans preuve (colonne « preuve de test prévue » définit la preuve attendue) ; données 100 % fictives ; pas de scan offensif externe ; ce document ne contient aucun secret.

---

## 1. Périmètre et architecture de confiance

### 1.1 Périmètre

- SaaS multi-tenant : cabinets (tenants) → clients (ClientOrg) → missions (engagements) → actifs, constats, preuves, graphe.
- Stack imposée : React SPA (Vite/TS/Tailwind/React Flow/TanStack Query) · FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic · PostgreSQL 16 · volume local privé pour les preuves · Mailpit (dev uniquement) · Docker Compose.
- Hors périmètre : MFA/SSO, WAF, stockage objet cloud, moteur de scan actif, billing (bonus non requis). Ces absences sont documentées en §4.

### 1.2 Frontières de confiance

```
                        ZONE NON CONFIANTE
 ┌──────────────────────────────────────────────────────────────────────────────┐
 │  Navigateur attaquant/curieux          Navigateur utilisateur légitime       │
 │  (aucune donnée sensible au JS ;       ┌──────────────────────────────────┐  │
 │   rendu React auto-échappé)            │ SPA React (pas de logique d'auth)│  │
 │                                        └───────────────┬──────────────────┘  │
 │   Cookie `session` (HttpOnly, SameSite=Lax, Secure en prod)
 │   Header `X-CSRF-Token` (mutations uniquement)          │                     │
 │   Body JSON (schémas Pydantic) · Multipart (uploads)    │ HTTPS (prod)        │
 │   URL paths (UUID) · Query params (limit/offset/filtres)│                     │
 │                                                        ▼                     │
 │        Frontière F1 : origine unique (reverse proxy ou proxy Vite)           │
 │        — CORS explicite (pas de wildcard) · CSP restrictive · HSTS ·         │
 │          terminaison TLS · headers de réponse appliqués                       │
 │                                                        ▼                     │
 │        ┌─────────────────────────────────────────────────────────────┐       │
 │        │ FastAPI /api/v1  (zone de confiance applicative)            │       │
 │        │  • session → user → memberships (source UNIQUE des rôles)  │       │
 │        │  • autorisation par ressource, à chaque endpoint           │       │
 │        │  • ORM paramétré · rate limiting · erreurs normalisées     │       │
 │        │  • audit append-only (request_id, acteur de session)       │       │
 │        └──────────────┬──────────────────────────────┬───────────────┘       │
 └───────────────────────┼──────────────────────────────┼───────────────────────┘
                         ▼                              ▼
  ZONE DE STOCKAGE (Frontière F2 : accès exclusif via l'API)
 ┌─────────────────────────────┐   ┌─────────────────────────────────┐
 │ PostgreSQL 16               │   │ Volume preuves (privé)          │
 │  users, sessions (hachées), │   │  • hors webroot, aucun montage  │
 │  invitations, reset tokens  │   │    statique                     │
 │  (hachés), audit_events,    │   │  • noms internes UUID            │
 │  données métier tenantisées │   │  • lecture/écriture uniquement  │
 └─────────────────────────────┘   │    par les routes autorisées     │
                                   └─────────────────────────────────┘
  DEV UNIQUEMENT — Mailpit (SMTP local, non chiffré, UI 8025) :
  reçoit e-mails invitation/reset depuis le backend ; risque résiduel §4.2.
```

**Principe directeur :** la seule source de vérité des droits est la session (token opaque haché en base → user → `tenant_memberships` / `client_memberships` / `platform_admins`). Tout champ envoyé par le navigateur (body, URL, header, cookie) est une *clé de recherche*, jamais un droit. `PLATFORM_ADMIN` n'accède pas par défaut aux données métier (spec §1).

### 1.3 Canaux d'entrée inventoriés

| Canal | Exemple | Traitement obligatoire |
|---|---|---|
| Cookie session | `session=<256 bits opaques>` | Lookup `sessions.token_hash` ; expiration `expires_at` ; révocation `revoked_at` ; attributs HttpOnly/SameSite=Lax/Secure(prod)/Path=/api |
| Header CSRF | `X-CSRF-Token` sur chaque mutation cookie | Comparaison hashée au `csrf_token_hash` de la session ; rejet 403 sinon |
| Body JSON | constats, actifs, filtres | Pydantic v2 : champs explicites, `extra` interdit (ou ignoré), bornes (CVSS 0–10, criticality 1–5) ; `tenant_id`/`role`/`published_at`/`client_visible` **jamais acceptés** |
| Multipart upload | `POST .../findings/{id}/evidences` | Taille ≤ 10 Mio (413), MIME whitelist PDF/PNG/JPEG/TXT **et** signature (magic bytes), nom interne généré par le serveur, stockage hors webroot |
| URL (path params) | `/engagements/{uuid}/findings/{uuid}` | UUIDs server-side only ; la ressource est résolue puis contrôlée (tenant, engagement, rôle, visibilité) — pas de confiance au path seul |
| Query params | `?limit=20&offset=0`, filtres | Coercion entières, `limit ≤ 100` ; filtres contraints par le tenant de la session ; pas de filtre par `tenant_id` client-fourni |

### 1.4 Modèle d'autorisation (par rôle)

| Rôle | Portail | Droits clés | Interdits clés |
|---|---|---|---|
| `PLATFORM_ADMIN` | `/platform` | Créer/suspendre tenants, stats d'exploitation | **Lecture des preuves et contenus d'audit** (spec §1) |
| `TENANT_ADMIN` | cabinet | Clients, membres, invitations, missions, constats et preuves du tenant | Données d'autres tenants ; actions plateforme |
| `PENTESTER` | cabinet | Actifs, constats, preuves, graphe, publication (règle §4 : membre autorisé) | Gestion plateforme, invitations admin, statuts de mission fermés |
| `CLIENT_VIEWER` | `/client` | Lecture des missions de ses client_orgs, findings **publiés**, preuves **publiées ET `client_visible`** | Toute mutation (routes client read-only) ; notes internes ; non publié |

---

## 2. Actifs et classification

| # | Actif | Contenu sensible | Criticité (C / I / A) | Justification |
|---|---|---|---|---|
| A1 | Données métier multi-tenant | engagements, actifs, findings (titre/description/impact/reco, CVSS, statuts), edges | **Critique / Élevée / Moyenne** | Fuite cross-tenant = critère bloquant (02 §6) ; données de pentest réelles en production |
| A2 | Preuves (fichiers + métadonnées) | fichiers PDF/PNG/JPEG/TXT, SHA-256, storage_key, `client_visible` | **Critique / Critique / Moyenne** | Une preuve falsifiée ou lue par un tiers est trompeuse/compromettante ; aucun accès hors route autorisée |
| A3 | Sessions | token opaque + `token_hash`, `csrf_token_hash`, `expires_at`, `revoked_at` | **Élevée / Élevée / Moyenne** | Compromission = usurpation de compte (02 §6 : bloquant si escalade) |
| A4 | Tokens invitation / reset | `token_hash`, cible (tenant/client_org + rôle ou user), expiration, `consumed_at` | **Élevée / Élevée / Faible** | Réutilisation = création de compte / prise de contrôle de mot de passe |
| A5 | Mots de passe | `password_hash` (Argon2id) | **Critique / Élevée / Faible** | Fuite de hash = risque de cracking offline (coût Argon2id est le contrôle) |
| A6 | Audit log | `AuditEvent` (acteur, action, entité, horodatage, request_id, métadonnées) | **Moyenne / Critique / Moyenne** | Preuve de non-répudiation ; doit être complet, non falsifiable, sans secrets |
| A7 | Secret d'application & credentials | secret de session, identifiants DB, config Compose | **Critique / Critique / Moyenne** | `.env` jamais commité ; seed sans mot de passe ; bootstrap par CLI |
| A8 | Disponibilité du service | uptime API/DB, volume preuves | Moyenne / Moyenne / **Élevée** | F19 (persistance après redémarrage Compose) ; DoS applicatif via graphe (T-42) |
| A9 | Données de démonstration | seed fictif (Aegis/Boreal/Acme…) | Faible / Moyenne / Faible | Obligation : **aucune donnée réelle** dans le dépôt (02 §1) |

---

## 3. Catalogue des menaces

Conventions : STRIDE = **S**poofing, **T**ampering, **R**epudiation, **I**nfo Disclosure, **D**enial of Service, **E**levation of Privilege. « Mitigation prévue » cite le contrôle + l'endpoint/mécanisme ; « Preuve » cite le scénario Fxx (02 §2), l'item §3 (02) et le fichier de test **prévu** (chemins backend/frontend à confirmer à l'implémentation). Statut global de ce catalogue : **prévu — aucune mesure non testée**.

### 3.1 Isolation multi-tenant et autorisation par ressource (A1, A2)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-01 | A1, A2 | I | Lecture cross-tenant ou hors périmètre par UUID deviné/connu (finding, asset, evidence, engagement) | Compte légitime dans un autre tenant, ou client du mauvais engagement | **Bloquant** (02 §6) : fuite de données d'audit | Résolution de la ressource **puis** contrôle `tenant_id` session + engagement + visibilité (finding publié, `client_visible`) ; réponses 404/403 sans révéler l'existence ; index tenant+engagement | F05, F13 ; 02 §3 « modifier tenant_id/finding_id… ; listes ne renvoient pas le voisin » · `backend/tests/api/test_isolation_cross_tenant.py` | Prévu |
| T-02 | A1 | T, E | Écriture/suppression cross-tenant (PATCH/DELETE d'un asset, finding, edge, evidence d'autrui) | Compte d'un autre tenant + UUID cible | Altération de données d'audit ; critère bloquant | Mêmes contrôles de résolution que T-01 pour chaque mutation ; `tenant_id`/`engagement_id` dérivés de la ressource mère, jamais du body ; transaction atomique (rollback si échec) | 02 §3 « tenter lectures, écritures, téléchargements cross-tenant » · `backend/tests/api/test_isolation_cross_tenant.py` | Prévu |
| T-03 | A1 | I | Fuite par agrégation : listes, dashboards, filtres, pagination renvoyant des enregistrements du voisin | Compte légitime, connaissance partielle des identifiants | Fuite indirecte même si l'accès direct est verrouillé | Toutes les requêtes de liste scopingées `WHERE tenant_id = (session)` (ou engagement pour les vues métier) ; `limit ≤ 100` ; aucun champ interne (hash, storage_key brut) dans les schémas de sortie ; test systématique « liste A vs liste B » | F03, F04, F06 ; 02 §3 « listes ne renvoient pas de données du voisin » · `backend/tests/api/test_isolation_cross_tenant.py` | Prévu |
| T-04 | A1 | E | `tenant_id` / `engagement_id` / `client_org_id` injectés dans le body JSON ou les filtres pour contourner le périmètre | Compte légitime + body falsifié | Escalade de périmètre (bloquant) | Schémas Pydantic sans ces champs (rejet `extra`) ; le tenant d'écriture est celui de la session ; le path paramètre n'est qu'une clé résolue puis contrôlée | F17 (partiel) ; 02 §3 « dans URL, JSON ou filtres » · `backend/tests/api/test_mass_assignment.py` + `test_isolation_cross_tenant.py` | Prévu |
| T-05 | A1, A2 | I | `PLATFORM_ADMIN` lit des preuves ou contenus d'audit via endpoints plateforme ou devinés | Compte plateforme admin | Violation de la séparation spec §1 ; exposition de données confidentielles | Routes `/platform/*` limitées à stats/tenants/membres ; aucun endpoint de lecture métier accessible au rôle plateforme ; le contrôleur « lecture preuve » exige un membership tenant | 02 §3 « élévation de privilèges » · `backend/tests/api/test_roles_platform.py` | Prévu |
| T-06 | A1 | E | `PENTESTER` opère hors de son tenant (engagement d'un autre cabinet, membership absent) | Compte pentester + UUID d'engagement tiers | Fuite/altération cross-tenant | Contrôle de membership à chaque ressource ; pas de dérivation par rôle seul (vérification **par ressource**, spec §1) | 02 §3 isolation · `backend/tests/api/test_roles_platform.py` | Prévu |
| T-07 | A1 | E, T | `CLIENT_VIEWER` modifie un finding/asset/engagement (PUT/PATCH/DELETE, publication) | Compte client + UUID connu | Mutation non autorisée (F07 bloquant en pratique) | Routes client strictement read-only (`/client/*`) ; routes cabinet exigeant membership tenant ; 403/404 | F07 ; 02 §3 « publier/rétracter en tant que client » · `backend/tests/api/test_client_readonly.py` + e2e `frontend/e2e/isolation.spec.ts` | Prévu |
| T-08 | A1 | E | Client publie/rétracte un constat (endpoints `publish`/`unpublish`) | Compte client | Fausse visibilité, tromperie client | `POST .../findings/{id}/publish|unpublish` : membership `TENANT_ADMIN` ou `PENTESTER` du tenant du finding ; événement d'audit | 02 §3 « publier/rétracter en tant que client » · `backend/tests/api/test_client_readonly.py` | Prévu |
| T-09 | A1 | I | Fuite cross-engagement **au sein d'un même tenant** (actif/finding/edge de l'engagement B lu via l'engagement A) | Membership du tenant, deux engagements | Mélange de contextes d'audit ; intégrité métier dégradée | Contrôle `engagement_id` sur chaque ressource enfant ; les listes sont paramétrées par l'engagement du path | 02 §3 « état de base inchangé » (F11) · `backend/tests/api/test_isolation_cross_tenant.py` | Prévu |

### 3.2 Sessions et usurpation (A3)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-10 | A3 | S | Replay de session après logout (cookie réutilisé) | Session révoquée conservée côté attaquant | Usurpation de compte (bloquant) | `POST /auth/logout` pose `revoked_at` ; chaque requête vérifie `revoked_at IS NULL` et l'expiration avant autorisation ; cookie effacé | F01 · `backend/tests/api/test_sessions.py` | Prévu |
| T-11 | A3 | S | Replay de session après changement de mot de passe (reset ou invitation) | Ancien cookie valide avant le reset | Prise de contrôle persistante | Reset/acceptation d'invitation → révocation de **toutes** les sessions de l'utilisateur (`sessions.revoked_at` par `user_id`) | 02 §3 « changement de mot de passe et sessions anciennes » · `backend/tests/api/test_sessions.py` | Prévu |
| T-12 | A3 | S, T | Cookie session altéré/falsifié (truncation, modification de base64, fixation) | Accès au cookie (XSS, réseau, vol de session) | Requête non authentifiée ou falsifiée | Token opaque 256 bits, **stocké haché** : toute altération ne correspond à aucun `token_hash` → 401 identique ; pas de state signé dans le cookie (pas de JWT à valider localement) | 02 §3 « cookie expiré, révoqué ou altéré » · `backend/tests/api/test_sessions.py` | Prévu |
| T-13 | A3 | S | Session expirée non rejetée (ou durée sans bornes) | Temps | Accès résiduel au-delà de la durée prévue | `expires_at` vérifié à chaque requête ; durée absolue + renouveaux bornés ; 401 cohérent avec l'état « non connecté » | 02 §3 sessions · `backend/tests/api/test_sessions.py` | Prévu |
| T-14 | A3 | I | Attributs cookie faibles : `HttpOnly` absent (lisible en JS), `SameSite` absent, `Secure` absent en prod, `Path` trop large | Lecture des réponses | Vol de cookie par XSS / CSRF / leakage | `set_cookie` : `httponly=True, samesite='lax', secure=<prod>, path='/api', max_age borné` ; contrôle par test d'inspection des headers de réponse | 02 §3 « absence de cookie de session dans JavaScript, logs, URL ou HTML » · `backend/tests/api/test_sessions.py` (sous-tests headers) | Prévu |
| T-15 | A3 | S, T | CSRF sur mutation cookie-based : POST de page tierce exécuté avec le cookie (login, publish, upload, PATCH) | Victime connectée qui visite un site malveillant | Action non intentionnelle (critère 02 §3) | Jeton CSRF lié à la session, haché en base (`csrf_token_hash`), servi par `GET /auth/csrf` ; header `X-CSRF-Token` **obligatoire sur toutes les mutations** ; rejet 403 si absent/erroné ; double protection `SameSite=Lax` | F16 · `backend/tests/api/test_csrf.py` | Prévu |
| T-16 | A3 | S | Contournement CSRF quand `SameSite=Lax` n'est pas respecté (anciens navigateurs, modes dégradés) | Navigateur non conforme | Idem T-15 | Le jeton CSRF est le contrôle primaire (T-15), `SameSite` est une défense en profondeur et non la garantie ; pas d'exception pour les mutations | 02 §3 « validation du CSRF pour mutations cookie-based et contrôles d'origines » · `backend/tests/api/test_csrf.py` | Prévu |
| T-17 | A3 | S | Vol de session par interception réseau (HTTP non chiffré) | Réseau non sécurisé | Usurpation complète | Cookies `Secure` (prod) + TLS terminé par le reverse proxy ; en dev, documenté comme non représentatif de prod (§4.4) | Revue manuelle CI/deployment (02 §4 « check sécurité des headers ») · `backend/tests/api/test_security_headers.py` | Prévu |

### 3.3 Tokens invitation / reset (A4)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-18 | A4 | S | Réutilisation d'un token invitation ou reset déjà consommé | Token valide capturé avant consommation | Double création de compte / reset arbitraire | `consumed_at` + mise à jour **atomique** (`UPDATE … WHERE consumed_at IS NULL`) : 2e tentative → 409/400 ; token jamais réémette sans nouvelle demande | F02 · `backend/tests/api/test_tokens.py` | Prévu |
| T-19 | A4 | S | Token invitation/reset expiré (durée de vie) | Temps au-delà de `expires_at` | Compte créé / mot de passe reset après expiration | Expiration courte (invitation : heures/jours ; reset : heures) vérifiée **avant** toute consommation ; 400/401 non distinguables à l'attaquant (§T-21) | 02 §3 « jeton d'invitation expiré » · `backend/tests/api/test_tokens.py` | Prévu |
| T-20 | A4 | I | Énumération des tokens (longueur/entropie insuffisantes) | Accès réseau (bruteforce) | Prise de compte ou création de membres arbitraire | Tokens aléatoires ≥ 256 bits (`secrets`), encodage url-safe, **stockés hachés** (SHA-256) → le brut ne circule que dans l'e-mail ; unité d'entropie vérifiée par test | 02 §3 sessions/usurpation (items tokens) · `backend/tests/unit/test_token_entropy.py` | Prévu |
| T-21 | A4 | I | Réponses révélatrices de l'existence d'un compte (login, forgot-password, reset) | E-mail d'essai | Énumération d'utilisateurs, ciblage | Réponse **identique** (même code HTTP, même message, durée équivalente) que l'e-mail existe ou non ; `forgot-password` renvoie toujours 200 générique ; échecs de login journalisés en audit **sans** indiquer l'existence | 01 §8 « sans fuite sur existence d'un utilisateur » · `backend/tests/api/test_account_existence.py` | Prévu |
| T-22 | A4 | E | Acceptation d'invitation par un e-mail différent de la cible, ou token « transvasé » vers un autre tenant/organisme | Token valid capturé (fuite d'e-mail) | Compte créé dans le mauvais tenant / mauvais rôle | Token lié à `(email, tenant_id ou client_org_id, role)` ; `accept-invitation` exige la coïncidence de l'e-mail du nouvel utilisateur avec l'e-mail du token ; le rôle final est celui du token, non du body | 02 §3 (usurpation) + F02 · `backend/tests/api/test_tokens.py` | Prévu |
| T-23 | A4 | I | Token présent dans les logs applicatifs, l'audit, l'URL de redirection ou les e-mails ré-émis | Vol de logs / inspection Mailpit | Consommation à distance du token | Logs sans token brut (seule l'action est journalisée) ; pas de token dans `metadata_json` de l'audit ; lien dans l'e-mail une seule fois (canal dev Mailpit §4.2) | F18 · `backend/tests/api/test_audit.py` (assertion « pas de token dans les logs ») | Prévu |

### 3.4 Rate limiting (A3, A4)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-24 | A3 | D, S | Brute force / credential stuffing sur `POST /auth/login` | Volume de requêtes | Comptes compromis, déni de service local | Rate limit applicatif (fenêtre glissante par **e-mail + IP**) sur login ; réponse 429 normalisée ; échecs journalés en audit (type `login_failed`) ; coût Argon2id comme frein offline | 01 §8 « limitation des connexions » · `backend/tests/api/test_rate_limit.py` | Prévu |
| T-25 | A4 | D | Flood `POST /auth/forgot-password` (spam e-mail, déni Mailpit, sondage d'existence par timing) | Volume de requêtes | Nuisance, indice de timing, épuisement de tokens | Rate limit par e-mail + IP (fenêtre courte, quota modeste), réponse non révélatrice (T-21), ré-émission qui **révoque** les tokens reset non consommés (pas d'accumulation) | 01 §8 « limitation des réinitialisations » · `backend/tests/api/test_rate_limit.py` | Prévu |
| T-26 | A3 | D | Contournement du rate limiting : réinitialisation de l'état (restart), IP partagée (NAT/proxy), rotation d'IP | Contrôle de l'infra ou réseau mobile | Brute force non borné dans le temps | **Limite assumée** (§4.1) : état en mémoire par instance, pas de lockout persistant ; compensations : audit des échecs, quota par e-mail (pas seulement par IP), 429 ; résiduel documenté | 02 §3 (sessions) + revue · `backend/tests/api/test_rate_limit.py` (comportement 429) | Prévu |

### 3.5 Upload et stockage des preuves (A2)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-27 | A2 | I, T | Faux MIME : extension/content-type déclarés incohérents avec le contenu (`.pdf` contenant du HTML/JS) | Upload malveillant | Contenu exécutable stocké comme « preuve » | Détection par **signature (magic bytes)** : `%PDF`, `\x89PNG`, `\xFF\xD8`, texte pour TXT ; le MIME stocké est celui **déterminé par le serveur**, pas le déclarant ; incohérence → 422 | F12, F14 ; 02 §3 « faux MIME » · `backend/tests/api/test_evidence_upload.py` | Prévu |
| T-28 | A2 | T | Double extension / contenu exécutable déguisé (`shell.php.png`, SVG avec `<script>`, HTM) | Upload malveillant | Exécution de code côté client lors de l'ouverture / confusion de type | Whitelist stricte PDF/PNG/JPEG/TXT sur signature **et** extension normalisée ; SVG/HTML/JS/EXE/ZIP rejetés 422 ; téléchargement forcé `attachment` + `nosniff` (T-33) réduit l'exposition | F14 ; 02 §3 « content-type dangereux » · `backend/tests/api/test_evidence_upload.py` | Prévu |
| T-29 | A2 | D | Dépassement de la taille limite 10 Mio (buffering en mémoire, épuisement disque) | Fichier volumineux | DoS applicatif, stockage saturé | Lecture bornée (streaming, abandon au 10 Mio + marge) → 413 **avant** tout écriture durable ; taille mesurée après upload (fichiers valides), 413 aussi si `size_bytes` incohérent | F14 ; 02 §3 « PDF volumineux » · `backend/tests/api/test_evidence_upload.py` | Prévu |
| T-30 | A2 | T | Traversal / caractères de contrôle dans le nom de fichier (`../../etc/passwd`, `\0`, backslash) | Upload avec nom hostilité | Écriture hors volume, corruption du chemin | Le **nom de fichier client est ignoré** pour le stockage : chemin interne `engagement/{uuid}/{uuid}.{ext}` généré par le serveur ; validation stricte de l'extension ; aucun `os.path.join` sur l'entrée brute | 02 §3 « nom de fichier avec séparateurs » · `backend/tests/api/test_evidence_upload.py` | Prévu |
| T-31 | A2 | T, D | Objet non autorisé stocké durablement malgré le rejet (fichier orphelin sur le volume) | Upload rejeté tardif (validation après écriture) | Données indésirables persistantes, surface d'accroche | Validation **complète avant** le commit au volume (buffer temp, nettoyage au rejet) ; test affirmant l'absence de fichier persistant après un upload refusé | F14 « sans stockage durable d'objet non autorisé » · `backend/tests/api/test_evidence_upload.py` | Prévu |
| T-32 | A2 | I | Accès direct au stockage (URL statique, path guess, montage webroot) | Connaissance/énumération du chemin | Lecture de preuve sans autorisation (bloquant 02 §6) | Volume **hors webroot**, aucun service ne l'expose statiquement ; seule `GET .../evidences/{id}/download` (cab) et `GET /client/evidences/{id}/download` (client, double condition) servent les octets ; contrôle d'autorisation préalable | F12, F13 ; revue « aucun accès direct au stockage » (02 §4) · `backend/tests/api/test_evidence_download.py` + vérification manuelle du montage Compose | Prévu |
| T-33 | A2 | T | Headers de téléchargement manquants/incorrects : inline sans `nosniff`, `Content-Type` exécutable, `Content-Disposition` absente | Preuve légitime téléchargée | Rendu exécuté par le navigateur (pivot XSS) | La route de download émet : `Content-Disposition: attachment; filename="<nom sûr>"`, `X-Content-Type-Options: nosniff`, `Content-Type` = MIME vérifié (fallback `application/octet-stream`), `Content-Length` | 02 §3 « vérifier téléchargement avec attachment + nosniff » · `backend/tests/api/test_evidence_download.py` | Prévu |
| T-34 | A2 | I | Client non autorisé télécharge une preuve `client_visible=false` ou d'un finding non publié | UUID deviné, ou membership client dans un autre client_org | Fuite de preuve (bloquant 02 §6) | Double condition : finding `published_at IS NOT NULL` **et** evidence `client_visible=true` **et** membership client sur le `client_org_id` de l'engagement ; sinon 404/403 | F13, F05, F06 · `backend/tests/api/test_evidence_download.py` + e2e `frontend/e2e/isolation.spec.ts` | Prévu |

### 3.6 Injections — XSS, SQLi, exécution (A1, A2, A3, A6)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-35 | A1 | T, S | XSS persistant via titre/description/impact/recommandation d'un finding, rendu **cabinet ET portail client** | Pentester malveillant ou client collé dans une description | Vol de session (cookie), action à distance, critère bloquant 02 §6 | React : échappement automatique, **interdiction de `dangerouslySetInnerHTML`** ; aucune réponse API ne contient de HTML brut ; pas de parsing de markdown riche non échappé ; CSP sans `unsafe-inline` (T-49) | F15 ; 02 §3 « payloads inoffensifs HTML/JS » · `frontend/e2e/xss.spec.ts` + `backend/tests/api/test_injection.py` (payload présent en clair échappé dans le JSON) | Prévu |
| T-36 | A1 | T | XSS via noms d'actifs, engagements, clients, membres (listes et détails) | Création d'entité nommée `<script>` | Idem T-35 | Idem T-35 : tous les noms rendus en tant que texte ; vérification sur chaque écran de liste/détail (cabinet + client) | F15 ; 02 §3 · `frontend/e2e/xss.spec.ts` | Prévu |
| T-37 | A1, A2 | T | Injection dans les exports (HTML/PDF brandé — bonus éventuel) : le contenu utilisateur est assemblé dans un template | Export déclenché avec payload | Exécution au rendu de l'export | Échappement systématique des variables de template (f-string/`jinja2 autoescape` ou équivalent) ; pas de balise interpolée depuis l'utilisateur ; test d'export avec payload | F15 « lors du rendu **ou export HTML** » · `backend/tests/api/test_injection.py` (si export implémenté) | Prévu |
| T-38 | A1 | T | SQL injection via filtres, tri, recherche (noms, CVSS, statuts) | Champs texte ou query params hostiles | Lecture/altération DB, contournement d'isolation | ORM SQLAlchemy 2 paramétré **uniquement** (pas de f-string SQL) ; recherche/`LIKE` échappées ; revue statique (checklist §6) + test de payloads dans filtres (`' OR 1=1--`, `UNION SELECT`) | 01 §8 ; 02 §3 · `backend/tests/api/test_injection.py` | Prévu |
| T-39 | A1 | T, E | Injection de shell / exécution de code à partir de texte utilisateur (`subprocess`, `eval`, `exec`, `yaml.load`, `pickle`) | Champ ou filename traité par du code | Compromission serveur complète | Interdit par architecture (01 §8 « jamais d'exécution de code ou shell à partir de texte utilisateur ») ; aucune dépendance de sérialisation non sûre sur données utilisateur ; vérification par revue + grep de patterns dans la CI (candidat skill, non actif) | 01 §8 · revue checklist §6 point 9 (sans test dédié si l'architecture l'exclut ; à consigner en `DECISIONS.md`) | Prévu |
| T-40 | A6 | T | Log injection (CR/LF) via champs utilisateur : falsification des logs et de l'audit | Titre/finding contenant `\r\n` | Piste d'audit falsifiée, parsing corrompu | Journalisation structurée (JSON ou format borné), `\r\n` normalisés/échappés dans `metadata_json` et logs applicatifs ; test de champ avec CRLF | 01 §4 (audit), F18 · `backend/tests/api/test_audit.py` | Prévu |
| T-41 | A3 | T, S | XSS **reflété** via query params ou état d'URL (messages d'erreur, filtres) rendus sans échappement | Lien hostilité avec paramètre | Vol de session | Toute valeur passée à l'UI est rendue en tant que texte ; pas de `innerHTML` sur les messages ; test avec paramètre contenant payload | 02 §3 « payloads inoffensifs » · `frontend/e2e/xss.spec.ts` | Prévu |

### 3.7 Graphe d'attaque (A1, A8)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-42 | A1, A8 | D | DoS par complexité explosive : graphe dense → énumération de chemins hors budget (CPU/mémoire, latence) | Engagement légitime avec ~150 actifs / ~300 edges | Indisponibilité du service (F19 au sens large), coût de calcul | Bornes contractuelles : **150 actifs, 300 edges** par engagement (rejet 400 au-delà), chemins simples longueur **1–6**, **20 résultats max**, délais raisonnables sur la recherche (timeout applicatif documenté) ; calcul 100 % serveur | 02 §3 « graphes cycliques… plus de six sauts » · `backend/tests/api/test_graph.py` (performance sur graphe maximal, assertion de délai) | Prévu |
| T-43 | A1 | T, I | Edge cross-engagement / cross-tenant (source, cible ou finding appartenant à un autre contexte) | UUID d'engagement voisin | Graphe falsifié, fuite indirecte par chemin | Les 3 objets doivent appartenir **au même engagement et même tenant** (spec §4) : vérification service + contraintes de clés étrangères composites (`engagement_id`, `tenant_id`) ; rejet atomique (état de base inchangé) | F11 · `backend/tests/api/test_graph.py` | Prévu |
| T-44 | A1 | T | Cycles, self-loops (`source = target`), edges en double, références à finding/actif supprimés | Graphes pathologiques | Boucles dans l'énumération, incohérence métier | `source_asset_id != target_asset_id` (400) ; les cycles sont naturellement bornés par « chemins simples » ; unicité de l'edge (même triplet → 409 ou idempotence documentée) ; suppression en cascade cohérente des enfants d'un asset/finding supprimé | 02 §3 « graphes cycliques, edges doublons, éléments supprimés » · `backend/tests/api/test_graph.py` | Prévu |

### 3.8 Mass assignment / durcissement des schémas (A1, A3, A4)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-45 | A1, A3 | E | Mass assignment : `role`, `tenant_id`, `published_at`, `client_visible`, `cvss`, `criticality`, `consumed_at`, `is_active`, `created_by` injectés dans les body de création/modification | Tout compte | Élévation de rôle, publication à distance, altération d'audit (F17 bloquant) | Schémas Pydantic v2 explicites **sans** ces champs (`model_config = ConfigDict(extra="forbid")` en écriture) ; `published_at` modifiable uniquement via `publish`/`unpublish` (membre autorisé) ; `client_visible` via `PATCH .../evidences/{id}` (membre tenant) ; `role` uniquement via le flux d'invitation ; bornes : CVSS 0–10, criticality 1–5, statut enum | F17 · `backend/tests/api/test_mass_assignment.py` | Prévu |

### 3.9 Logs, erreurs et audit (A6, A7)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-46 | A6 | I | Stack traces / détails d'implémentation dans les réponses d'erreur (500 brut, messages ORM, chemins de fichiers) | Erreurs déclenchées | Reconnaissance, exposition de la structure, possible fuite de données | Réponses normalisées `{error:{code,message,request_id}}` (01 §6) ; gestionnaire global d'exceptions ; `debug=False` hors dev ; messages publics génériques ; `request_id` traceable côté serveur uniquement | 01 §6, §8 · `backend/tests/api/test_errors.py` (aucun `Traceback` dans le body des erreurs) | Prévu |
| T-47 | A6, A7 | I | Secrets dans les logs ou la métadonnée d'audit : token brut, mot de passe, `X-CSRF-Token`, payload d'upload | Journalisation d'une action sensible | Fuite via accès aux logs (dev ou prod), audit infalsifiable dégradé | Politique de métadonnée : champs autorisés seulement (IDs, statuts, tailles) ; aucun token/mot de passe/payload ; logs applicatifs filtrés (pas de body complet par défaut) | F18 « sans jeton ni mot de passe » ; 02 §3 · `backend/tests/api/test_audit.py` | Prévu |
| T-48 | A6 | R, T | Audit log incomplet ou falsifiable : acteur pris du body, événements manquants (échec de login, accès preuve), suppression/modification possible | Compte admin du tenant | Non-répudiation perdue, traçabilité inopérante | `AuditEvent` append-only **au niveau applicatif** : aucune route DELETE/PATCH sur l'audit ; `actor_id` dérivé de la session (jamais du body) ; couverture des événements normatifs (logins succès/échec, invitations, publications, rôles, corrections, statuts, accès/téléchargement de preuves) ; `request_id` joint | F18, 01 §4 Historique · `backend/tests/api/test_audit.py` | Prévu |

### 3.10 Transport, headers de réponse et dépôt (A7)

| ID | Actif | STRIDE | Menace | Préconditions | Impact | Mitigation prévue | Preuve de test prévue | Statut |
|---|---|---|---|---|---|---|---|---|
| T-49 | — | T, S | Headers de sécurité manquants : CSP permissive, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` absents (clickjacking, XSS amorti) | Lecture des réponses | Pivot XSS / embedding d'iframe malveillante | Middleware global : `Content-Security-Policy: default-src 'self'; script-src 'self'; …` (pas de `unsafe-inline`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` ; CORS explicite (origine frontend exacte uniquement, pas de wildcard avec credentials) | 01 §8, 02 §4 « check sécurité des headers » · `backend/tests/api/test_security_headers.py` | Prévu |
| T-50 | A7 | I | Secrets commités dans le dépôt : `.env` réel, mots de passe de seed, token d'invitation en fixture, captures avec cookie | Installation depuis le clone (F20) | Compromission immédiate de l'instance ; non-conformité 02 §6 | `.env.example` **sans** valeur de production ; bootstrap par `CLI create-platform-admin` ; seed sans mot de passe durci (documenté, fictif) ; contrôle CI optionnel (candidat skill gitleaks, non actif) ; revue checklist point 14 | F20 · revue CI + checklist §6 point 14 | Prévu |

---

## 4. Risques résiduels et limites documentées

Honnêteté d'usage : les points ci-dessous subsisteront **même après mise en œuvre des contrôles prévus**. Ils sont assumés pour le périmètre 48 h et doivent figurer dans `QA_REPORT.md` / `DECISIONS.md`.

1. **Rate limiting en mémoire (mono-instance)** — T-26 : l'état des fenêtres glissantes est perdu au redémarrage et non partagé si plusieurs réplicas sont placés derrière un load balancer. Contournement par IP possible (NAT, proxy mobile). Compensations : quota par e-mail, audit des échecs, réponse 429. Résiduel : un attaquant patient multi-IP peut dépasser le quota. *Hors périmètre : Redis.*
2. **Mailpit de développement non chiffré et exposé sur le réseau Compose** — T-23 : les liens reset/invitation transitent en clair et sont lisibles dans l'UI Mailpit (port 8025). Acceptable uniquement en dev local ; en production, un SMTP chiffré serait requis. Résiduel : sur l'instance de démo, un observateur du réseau de dev peut lire un lien de reset.
3. **Absence de WAF** — la défense est 100 % applicative (échappement, ORM paramétré, CSRF, autorisation). Un régress de code non couvert par les tests pourrait exposer l'application à des vecteurs que le WAF aurait filtrés (XSS exotique, certains DoS volumétriques).
4. **Cookies `Secure` conditionnels à la terminaison TLS du reverse proxy** — T-17 : le backend n'impose pas lui-même le TLS ; si le déploiement produit est mal configuré (HTTP direct sur le port FastAPI), les cookies ne sont pas protégés. La documentation d'installation doit exiger le proxy TLS ; test de vérification prévu par revue d'infra, pas par code applicatif.
5. **Pas de MFA ni de SSO (hors périmètre, bonus)** — la seule preuve d'identité est le mot de passe (Argon2id) ; un mot de passe volé (brute force borné mais non nul, phishing) conduit à la prise de compte sans facteur supplémentaire.
6. **Benchmarks de test non représentatifs de production** — aucune charge réelle, aucun trafic internet, données 100 % fictives ; les tests de performance du graphe (T-42) mesurent un budget, pas une garantie de durée sous production. Les résultats de sécurité sont validés en revue manuelle sur instance locale isolée (02 §7).
7. **Intégrité du stockage des preuves** — le SHA-256 est calculé à l'écriture et stocké ; la re-vérification à la lecture n'est pas contractuelle. Un tamperage du volume (accès hôte Docker) ne serait pas détecté en lecture. Acceptable : le volume est isolé, non monté statiquement (T-32).
8. **Audit applicatif, pas système** — les accès à Postgres et au volume ne sont pas journalisés ; seule la couche applicative produit des `AuditEvent`. Une compromission au niveau hôte contournerait l'audit.
9. **Aucun scan offensif externe** (règle du benchmark) — le threat model est une revue défensive par la preuve ; il ne remplace pas un test d'intrusion indépendant.

---

## 5. Matrice de couverture des tests

Lecture : pour chaque menace, la preuve **prévue** (fichier de test à créer par les rôles Développeur/QA). Chemins backend (`backend/tests/…`) et frontend/e2e (`frontend/e2e/…`) sont des conventions attendues, à confirmer dans la PR d'implémentation correspondante. À la clôture, QA coche cette matrice dans `QA_REPORT.md` (règle 02 §4 : ne pas déclarer « testé » sans commande et journal).

| ID | Menace (rappel) | Preuve pytest prévue (fichier) | Preuve E2E Playwright prévue | Scénarios de référence |
|---|---|---|---|---|
| T-01 | Lecture hors périmètre / UUID deviné | `backend/tests/api/test_isolation_cross_tenant.py` | `frontend/e2e/isolation.spec.ts` (vue client) | F05, F13 · 02 §3 |
| T-02 | Écriture cross-tenant | `backend/tests/api/test_isolation_cross_tenant.py` | — | 02 §3 |
| T-03 | Fuite par liste/agrégation | `backend/tests/api/test_isolation_cross_tenant.py` | — | F03, F04, F06 · 02 §3 |
| T-04 | `tenant_id`/`engagement_id` dans body/filtres | `backend/tests/api/test_mass_assignment.py`, `test_isolation_cross_tenant.py` | — | F17 · 02 §3 |
| T-05 | Plateforme admin lit des preuves | `backend/tests/api/test_roles_platform.py` | — | 02 §3 |
| T-06 | Pentester hors tenant | `backend/tests/api/test_roles_platform.py` | — | 02 §3 |
| T-07 | Client modifie | `backend/tests/api/test_client_readonly.py` | `frontend/e2e/isolation.spec.ts` | F07 |
| T-08 | Client publie/rétracte | `backend/tests/api/test_client_readonly.py` | — | 02 §3 |
| T-09 | Cross-engagement (même tenant) | `backend/tests/api/test_isolation_cross_tenant.py` | — | F11 |
| T-10 | Replay post-logout | `backend/tests/api/test_sessions.py` | — | F01 |
| T-11 | Replay post-changement de mdp | `backend/tests/api/test_sessions.py` | — | 02 §3 |
| T-12 | Cookie altéré | `backend/tests/api/test_sessions.py` | — | 02 §3 |
| T-13 | Session expirée | `backend/tests/api/test_sessions.py` | — | 02 §3 |
| T-14 | Attributs cookie | `backend/tests/api/test_sessions.py` | — | 02 §3 |
| T-15 | CSRF manquant sur mutation | `backend/tests/api/test_csrf.py` | — | F16 |
| T-16 | SameSite non respecté | `backend/tests/api/test_csrf.py` | — | 02 §3 |
| T-17 | Vol réseau (HTTP) | `backend/tests/api/test_security_headers.py` (cookie Secure) | — | Revue 02 §4 |
| T-18 | Réutilisation invitation/reset | `backend/tests/api/test_tokens.py` | — | F02 |
| T-19 | Token expiré | `backend/tests/api/test_tokens.py` | — | 02 §3 |
| T-20 | Entropie/énumération | `backend/tests/unit/test_token_entropy.py` | — | 02 §3 |
| T-21 | Réponse révélatrice | `backend/tests/api/test_account_existence.py` | — | 01 §8 |
| T-22 | Cible/falsification d'invitation | `backend/tests/api/test_tokens.py` | — | F02, 02 §3 |
| T-23 | Token dans logs | `backend/tests/api/test_audit.py` | — | F18 |
| T-24 | Brute force login | `backend/tests/api/test_rate_limit.py` | — | 01 §8 |
| T-25 | Flood reset | `backend/tests/api/test_rate_limit.py` | — | 01 §8 |
| T-26 | Contournement rate limit | `backend/tests/api/test_rate_limit.py` (429) | — | 02 §3 |
| T-27 | Faux MIME | `backend/tests/api/test_evidence_upload.py` | `frontend/e2e/upload.spec.ts` | F12, F14 · 02 §3 |
| T-28 | Double extension / SVG/HTML | `backend/tests/api/test_evidence_upload.py` | `frontend/e2e/upload.spec.ts` | F14 · 02 §3 |
| T-29 | > 10 Mio | `backend/tests/api/test_evidence_upload.py` | — | F14 |
| T-30 | Traversal nom fichier | `backend/tests/api/test_evidence_upload.py` | — | 02 §3 |
| T-31 | Stockage orphelin | `backend/tests/api/test_evidence_upload.py` (assertion disque) | — | F14 |
| T-32 | Accès direct au volume | `backend/tests/api/test_evidence_download.py` + revue Compose | — | F13 · 02 §4 |
| T-33 | Headers de download | `backend/tests/api/test_evidence_download.py` | — | 02 §3 |
| T-34 | Client non autorisé (download) | `backend/tests/api/test_evidence_download.py` | `frontend/e2e/isolation.spec.ts` | F05, F13 |
| T-35 | XSS finding (cabinet + client) | `backend/tests/api/test_injection.py` | `frontend/e2e/xss.spec.ts` | F15 |
| T-36 | XSS noms d'entités | `backend/tests/api/test_injection.py` | `frontend/e2e/xss.spec.ts` | F15 |
| T-37 | Injection export HTML/PDF | `backend/tests/api/test_injection.py` (si bonus) | — | F15 |
| T-38 | SQLi | `backend/tests/api/test_injection.py` | — | 01 §8 |
| T-39 | Shell / code execution | Revue statique (checklist §6 pt 9), aucun pattern interdit en CI | — | 01 §8 |
| T-40 | Log injection CRLF | `backend/tests/api/test_audit.py` | — | F18 |
| T-41 | XSS reflété | — | `frontend/e2e/xss.spec.ts` | 02 §3 |
| T-42 | DoS graphe dense | `backend/tests/api/test_graph.py` (budget temps) | — | 02 §3 |
| T-43 | Edge cross-engagement | `backend/tests/api/test_graph.py` | — | F11 |
| T-44 | Cycle/self-loop/doublons | `backend/tests/api/test_graph.py` | — | 02 §3 |
| T-45 | Mass assignment | `backend/tests/api/test_mass_assignment.py` | — | F17 |
| T-46 | Stack trace dans erreurs | `backend/tests/api/test_errors.py` | — | 01 §6 |
| T-47 | Secrets dans logs/audit | `backend/tests/api/test_audit.py` | — | F18 |
| T-48 | Audit incomplet/falsifiable | `backend/tests/api/test_audit.py` | — | F18, 01 §4 |
| T-49 | Headers de réponse / CORS | `backend/tests/api/test_security_headers.py` | — | 02 §4 |
| T-50 | Secrets commités | Revue CI + checklist §6 pt 14 | — | F20 |

Scénarios F non couverts par une menace (F08, F09, F10, F12 positif, F19, F20) : couvertures fonctionnelles du Développeur/QA (graphe, upload valide, persistance, installation) — ils restent obligatoires en E2E mais ne sont pas des menaces.

---

## 6. Checklist de revue des PR sensibles (rôle Cyber)

À appliquer systématiquement sur toute PR touchant auth, multi-tenant, upload, preuves, graphe, audit ou schémas :

1. Chaque route modifiée contrôle-t-elle l'autorisation **par ressource** (tenant + engagement + rôle + visibilité), et non par rôle seul ?
2. Aucun champ client-fourni (`tenant_id`, `engagement_id`, `role`, `client_org_id`) n'est utilisé comme source de vérité ?
3. Les listes/filtres sont-ils scopingés au tenant de la session, avec `limit ≤ 100` et bornes de tri ?
4. Les schémas Pydantic refusent-ils les champs sensibles (`extra="forbid"` en écriture) : `published_at`, `client_visible`, `role`, `consumed_at`, `is_active`, `created_by`, `token*` ?
5. Les mutations cookie-based exigent-elles `X-CSRF-Token` ? (pas d'exception « interne »)
6. Le cookie de session : HttpOnly, SameSite=Lax, Secure en prod, Path borné ?
7. Toute révocation de session est-elle traitée (logout, changement de mdp, ré-émission de token) ?
8. Upload : whitelist MIME **et** signature, 10 Mio **avant** écriture durable, nom interne serveur, nettoyage au rejet ?
9. SQL uniquement paramétré via l'ORM ; aucun `subprocess`/`eval`/`exec`/`yaml.load`/`pickle` sur donnée utilisateur ?
10. Rendu des contenus utilisateur : échappé partout, aucun `dangerouslySetInnerHTML`, aucun HTML brut côté API ?
11. Les réponses d'erreur sont-elles normalisées (`code/message/request_id`), sans stack trace ni détail interne ?
12. L'audit enregistre-t-il l'événement sensible avec acteur **de session**, request_id, et métadonnée sans secret ?
13. Les tokens (invitation/reset/session/CSRF) : entropie ≥ 256 bits, hachés en base, usage unique, expiration courte ?
14. Aucun secret, `.env` réel, mot de passe de seed ou capture avec cookie dans le diff ?
15. Tests de sécurité correspondants du §5 présents et exécutés (CI verte : pytest + vitest + build) ; sinon issue de suivi ouverte ?

Rappel gouvernance (02 §7, 04) : une faille bloquante (fuite cross-tenant, preuve non autorisée, escalade, XSS en chaîne de rendu) est signalée **séparément** de la note, avec impact, préconditions et preuve reproductible non destructive, et bloque le merge.

---

## 7. Processus de mise à jour de ce document

- Toute menace découverte en cours de benchmark (revue de PR, test, incident) → issue `security/<ticket>-slug` → contrôle ou test ajouté → **ligne T-xx ajoutée ici** dans la même PR (ou PR dédiée).
- Les changements de spécification normatifs ne sont jamais improvisés : ils passent par amendement daté du commanditaire (01 §11, 07) et sont ensuite répercutés ici.
- Statuts possibles : `Prévu` → `Implémenté (PR #n)` → `Vérifié (QA_REPORT, journal du n/2026)`.
