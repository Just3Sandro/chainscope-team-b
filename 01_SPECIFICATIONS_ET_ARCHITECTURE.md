# ChainScope — Spécifications et architecture V2

**Statut : référence commune V2 — gelée pour le benchmark, amendements uniquement via `08_JOURNAL_INTERVENTIONS.md`.**

## 1. Vision et objectif

ChainScope est un SaaS B2B de gestion de campagnes de pentest. Des cabinets de cybersécurité gèrent des entreprises clientes, les missions, leurs actifs, vulnérabilités, preuves et chemins d'attaque. Les clients consultent uniquement les résultats explicitement publiés pour eux.

Le benchmark vise une implémentation fonctionnelle en **48 heures par équipe** ; aucun abonnement Stripe, moteur de scan actif, exploitation de vulnérabilité, moteur IA ou service externe payant n'est demandé.

### Définition des comptes et organisations

- **Plateforme** : instance ChainScope, administrée par un superadministrateur.
- **Tenant** : cabinet de pentest ; frontière principale d'isolation.
- **ClientOrg** : entreprise auditée, rattachée à un seul tenant.
- **Engagement** : mission de pentest, rattachée à un ClientOrg et un tenant.
- **User** : identité globale (e-mail unique) ; ses permissions viennent de memberships explicites, jamais de données envoyées par le navigateur.

### Rôles

- `PLATFORM_ADMIN` : création/suspension de tenants, statistiques d'exploitation et comptes administrateurs. N'accède pas par défaut aux preuves et aux contenus confidentiels des audits.
- `TENANT_ADMIN` : gestion des clients, invitations, membres et missions du tenant ; accès aux constats et preuves de son tenant.
- `PENTESTER` : travaux techniques et cycle de vie des constats dans les engagements de son tenant ; ne gère pas la plateforme ni les invitations administrateur.
- `CLIENT_VIEWER` : vue lecture seule de ses propres engagements et des éléments explicitement publiés ; n'accède pas aux notes internes.

Les rôles du cabinet sont stockés dans `tenant_memberships`. Le rôle client est stocké dans `client_memberships`. Un utilisateur peut appartenir à plusieurs entités, mais toutes les vérifications sont effectuées par ressource.

## 2. Stack imposée

- Frontend : **React + TypeScript + Vite + Tailwind CSS + React Router + TanStack Query**.
- Graphe interactif : **@xyflow/react (React Flow)**.
- Backend : **Python 3.12+ + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic**.
- Base : **PostgreSQL 16+**.
- Auth : sessions opaques côté serveur, stockées hachées en base ; cookies `HttpOnly`, `SameSite=Lax`, `Secure` en production ; protection CSRF pour toutes les mutations fondées sur les cookies.
- Stockage de preuves : volume local privé persistant (aucune exposition statique). Interface permettant une évolution ultérieure vers stockage objet.
- Déploiement : Docker Compose (frontend, backend, postgres, Mailpit de développement facultatif) avec healthchecks et migrations.
- Tests : pytest + HTTPX, Vitest, Playwright (parcours fonctionnels de référence).
- Aucun Redis, broker de messages, microservice ou moteur de jobs distribué requis dans le périmètre initial.

Architecture : monolithe modulaire avec couches `api / services / repositories / models / schemas / security` séparées. Le navigateur ne parle qu'au backend. Une configuration reverse proxy ou Vite proxy évite les origines multiples inutiles.

## 3. Flux utilisateur obligatoires

1. Bootstrap d'un administrateur plateforme via **commande CLI explicite** (jamais de mot de passe administrateur fixé dans les sources).
2. Le superadministrateur crée un tenant ; le tenant admin est invité.
3. L'administrateur tenant invite un pentester et un client ; les invitations ont une durée de vie et ne sont utilisables qu'une fois.
4. Un utilisateur peut se connecter, se déconnecter et réinitialiser son mot de passe via lien à usage unique ; e-mails via Mailpit en développement.
5. L'admin crée une entreprise cliente et une mission ; un pentester ajoute des actifs, des vulnérabilités et des preuves.
6. Le pentester construit un graphe : des actifs et des relations qui dépendent de vulnérabilités spécifiques.
7. Le backend calcule les chemins actifs vers les actifs critiques ; une vulnérabilité corrigée invalide les chemins correspondants.
8. L'admin ou le pentester publie explicitement un constat pour le client ; le client peut le voir mais ne peut pas le modifier.
9. Toute opération sensible est journalisée, sans secrets dans les logs.

## 4. Règles métier

### Missions

Statuts `DRAFT`, `IN_PROGRESS`, `CLOSED`. `CLOSED` interdit les mutations techniques, sauf réouverture par `TENANT_ADMIN`. Un client ne peut pas changer ce statut.

### Constats (`Finding`)

Champs obligatoires : titre, description, impact, recommandation, sévérité (`LOW/MEDIUM/HIGH/CRITICAL`), CVSS numérique **entre 0 et 10**, statut `OPEN/IN_PROGRESS/REMEDIATED/ACCEPTED_RISK`, dates et auteur.

- `published_at = NULL` : invisible au client, même si le client devine l'ID.
- Publication = action explicite d'un membre autorisé ; rétractation possible et journalisée.
- `REMEDIATED` désactive les relations de graphe supportées par ce constat.
- `ACCEPTED_RISK` reste exploitable dans le calcul de chemin : acceptation du risque ne signifie pas correction.
- État et date de publication sont indépendants.

### Actifs

`Asset` : nom, type (`WEB`, `SERVER`, `DATABASE`, `WORKSTATION`, `OTHER`), description, `is_entry_point`, `is_crown_jewel`, `criticality` entier 1–5, position visuelle x/y.

### Relations du graphe

`AttackEdge` : `source_asset_id`, `target_asset_id`, `finding_id` obligatoires, orientée de source vers cible. Les trois objets doivent appartenir **au même engagement et au même tenant**. Source et cible sont distinctes. Un constat peut servir à plusieurs relations.

**Chemin actif** : parcours dirigé d'un `is_entry_point=true` vers un `is_crown_jewel=true` dont chaque edge référence un constat dans l'état `OPEN`, `IN_PROGRESS` ou `ACCEPTED_RISK`. Les chemins contenant un constat `REMEDIATED` sont exclus.

**Algorithme contractuel :**
- Énumérer les **chemins simples** (sans répéter un actif), de longueur **1 à 6 relations**.
- Limite : **20 résultats maximum** ; classer par score décroissant, puis longueur croissante, puis liste ordonnée d'identifiants d'edges (ordre lexicographique) pour stabilité.
- Score pédagogique (pas une méthode officielle de scoring cyber) : `round(2 * criticality_of_target * min(cvss_of_edges), 1)` ; borné entre 0 et 100.
- Si aucune relation active ou aucun chemin, renvoyer un tableau vide et non un chemin fictif.
- Pour limiter les abus : plafond de 150 actifs et 300 edges par engagement ; contraintes de longueur, pagination et délai raisonnable sur la recherche.
- Le **backend** calcule les chemins : le frontend se contente de représenter les résultats.

### Preuves

`Evidence` : rattachement à un finding, chemin interne généré par le serveur, SHA-256, MIME identifié, taille, auteur, date, visibilité client `client_visible=false` par défaut. Upload limité à **10 Mio**, types autorisés `PDF`, `PNG`, `JPEG`, `TXT`. Les téléchargements passent **exclusivement** par une route autorisée, avec `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` et aucun accès direct au stockage. Une preuve n'est visible au client que si `client_visible=true` **et** si le constat associé est publié.

### Historique

`AuditEvent` append-only applicatif : acteur, tenant, type de ressource, action, ID de ressource, horodatage, request ID, métadonnées non sensibles. Journaliser logins (succès/échec), invitations, publications, changements de rôles, corrections, changements de statut, accès/téléchargements des preuves.

## 5. Modèle de données minimal

Tous les identifiants sont des UUID générés côté serveur.

| Table | Champs clés / relations |
|---|---|
| `users` | `id`, `email` unique, `password_hash`, `is_active`, `created_at` |
| `platform_admins` | `user_id` unique |
| `tenants` | `id`, `name`, `slug` unique, `is_active` |
| `tenant_memberships` | `user_id`, `tenant_id`, `role` (`TENANT_ADMIN`, `PENTESTER`) |
| `client_orgs` | `id`, `tenant_id`, `name` |
| `client_memberships` | `user_id`, `client_org_id`, `role` (`CLIENT_VIEWER`) |
| `engagements` | `id`, `tenant_id`, `client_org_id`, `name`, `scope`, `status`, `created_at`, `updated_at` |
| `assets` | `id`, `tenant_id`, `engagement_id`, `name`, `type`, `criticality`, `is_entry_point`, `is_crown_jewel`, `x`, `y` |
| `findings` | `id`, `tenant_id`, `engagement_id`, `title`, `description`, `impact`, `recommendation`, `severity`, `cvss`, `status`, `published_at`, `created_by` |
| `attack_edges` | `id`, `tenant_id`, `engagement_id`, `source_asset_id`, `target_asset_id`, `finding_id` |
| `evidences` | `id`, `tenant_id`, `engagement_id`, `finding_id`, `storage_key`, `sha256`, `mime`, `size_bytes`, `client_visible`, `created_by` |
| `sessions` | `id`, `user_id`, `token_hash`, `csrf_token_hash`, `expires_at`, `revoked_at` |
| `invitations` | `id`, `email`, `token_hash`, `tenant_id` nullable, `client_org_id` nullable, `role`, `expires_at`, `consumed_at` |
| `password_reset_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `consumed_at` |
| `audit_events` | `id`, `tenant_id` nullable, `actor_id`, `action`, `entity_type`, `entity_id`, `metadata_json`, `created_at`, `request_id` |

Exigences base : clés étrangères, index tenant et engagement, contraintes de domaine et unicité appropriées, migrations reproductibles. Les références cross-tenant et cross-engagement doivent être interdites en service et, lorsque praticable, par clés étrangères composites. Ne jamais faire confiance à un `tenant_id` reçu du frontend.

## 6. Contrats API minimaux

Toutes les routes ci-dessous sont sous `/api/v1`. JSON, sauf uploads/downloads. Réponses d'erreur normalisées : `{ "error": { "code": "FORBIDDEN", "message": "...", "request_id": "..." } }`. Codes HTTP : 200/201/204 succès ; 400 validation métier ; 401 non connecté ; 403 permission insuffisante ; 404 ressource inexistante ou hors périmètre ; 409 conflit ; 413 taille upload ; 422 schéma invalide ; 429 limitation.

### Authentification / plateforme

- `POST /auth/login` : `{email,password}` → cookie session + résultat utilisateur.
- `GET /auth/me`, `GET /auth/csrf`, `POST /auth/logout`.
- `POST /auth/forgot-password`, `POST /auth/reset-password` (tokens à usage unique ; réponse de demande non révélatrice de compte).
- `POST /auth/accept-invitation` : token et nouveau mot de passe.
- `GET /platform/tenants`, `POST /platform/tenants`, `PATCH /platform/tenants/{tenant_id}` : plateforme seulement.

### Gestion cabinet/client

- `GET/POST /tenants/{tenant_id}/clients` ; `GET/PATCH /tenants/{tenant_id}/clients/{client_id}`.
- `GET/POST /tenants/{tenant_id}/members` (POST = invitation) ; `GET/POST /tenants/{tenant_id}/clients/{client_id}/invitations`.
- `GET/POST /tenants/{tenant_id}/engagements` ; `GET/PATCH /tenants/{tenant_id}/engagements/{engagement_id}`.

### Exécution d'un pentest

- `GET/POST /engagements/{engagement_id}/assets`; `PATCH/DELETE /engagements/{engagement_id}/assets/{asset_id}`.
- `GET/POST /engagements/{engagement_id}/findings`; `GET/PATCH /engagements/{engagement_id}/findings/{finding_id}`.
- `POST /engagements/{engagement_id}/findings/{finding_id}/publish` et `POST .../unpublish`.
- `POST /engagements/{engagement_id}/findings/{finding_id}/evidences` : multipart upload.
- `GET /engagements/{engagement_id}/evidences/{evidence_id}/download` : pièce jointe sécurisée.
- `PATCH /engagements/{engagement_id}/evidences/{evidence_id}` : visibilité client.
- `GET/POST /engagements/{engagement_id}/graph/edges` ; `DELETE /engagements/{engagement_id}/graph/edges/{edge_id}`.
- `GET /engagements/{engagement_id}/graph/paths` : liste ordonnée de `{edge_ids, asset_ids, score, target_asset_id}`.
- `GET /tenants/{tenant_id}/audit-events` : admin seulement, paginé.

### Portail client

- `GET /client/engagements` : missions du ou des client_orgs autorisés.
- `GET /client/engagements/{engagement_id}/findings` : **uniquement publiées**.
- `GET /client/engagements/{engagement_id}/findings/{finding_id}` : publiée uniquement.
- `GET /client/evidences/{evidence_id}/download` : publiée ET `client_visible` uniquement.

Pagination : `?limit=20&offset=0`, `limit <= 100`. Filtres serveur sur recherches/lists. Les routes client sont en lecture seule. Pas d'endpoint public présentant une liste globale de tenants ou clients.

## 7. Pages et UX attendues

1. Connexion / déconnexion / acceptation d'invitation / mot de passe oublié.
2. Tableau de bord cabinet : missions en cours, constats par gravité, activité récente, filtres.
3. Espace clients du cabinet : liste, création, détail et invitations.
4. Espace missions : création, statut, liste des actifs et constats.
5. Détail d'un constat : CVSS, impact, recommandations, statut, publication, preuves.
6. Graphe interactif : React Flow, nœuds/relations, chemin actif sélectionnable, repositionnement persistant, calcul côté serveur.
7. Portail client séparé : missions et constats publiés, éventuellement preuves explicitement visibles.
8. Administration plateforme : tenants et état des comptes ; pas de lecture des données métiers.
9. Journal d'audit cabinet (admin).

UX : véritable navigation, responsive desktop/tablette, chargement/erreur/vide, confirmations avant suppression et publication, notifications non intrusives, accessibilité minimale clavier/labels/contraste. Pas de pages factices ni données statiques imitant un backend.

## 8. Contraintes de sécurité obligatoires

- Mots de passe hachés avec Argon2id ; invitations et réinitialisations tokenisées à expiration courte et usage unique.
- Sessions opaques aléatoires (256 bits) ; secrets et jetons stockés hachés en base, révocation à la déconnexion et au changement de mot de passe.
- Cookies `HttpOnly`, `SameSite=Lax`, `Secure` en production ; jeton CSRF lié à la session envoyé dans en-tête pour opérations mutantes ; pas de secrets en `localStorage`.
- Limitation des connexions et réinitialisations, sans fuite sur existence d'un utilisateur.
- Autorisation côté serveur sur **chaque ressource**. Aucune permission déduite uniquement d'un identifiant dans l'URL ou d'un rôle fourni par le client.
- SQL parameterized via ORM ; jamais d'exécution de code ou shell à partir de texte utilisateur.
- Rendu HTML échappé ; pas de HTML brut pour les descriptions, commentaires ou preuves.
- Upload MIME/extension et signature vérifiés, limitation de taille, stockage hors webroot, noms internes imprévisibles, téléchargements autorisés.
- En production : HTTPS, config des cookies, CSP restrictive et CORS explicite ; pas de debug ni erreurs contenant secrets.
- Audit log des mutations et opérations sensibles ; données personnelles minimisées ; données de test entièrement fictives.

La conformité à OWASP ASVS n'est **pas revendiquée** : les contrôles présents seront testés, et les écarts documentés.

## 9. Périmètre 48 heures

### Obligatoire (évalué)

Auth réelle et rôles, multi-tenant, client et cabinet, missions, actifs, constats, publication client, preuves privées, graphe dirigé + paths, UI utilisable, tests significatifs, migrations, Docker Compose, seed de démonstration fictive, documentation d'installation.

### Bonus (non requis pour réussir)

Exports PDF, PDF brandé, SSO/OIDC, MFA, billing Stripe, notifications temps réel, workers asynchrones, import CVE/CVSS automatisé, IA de rédaction, collaboration simultanée avancée, système de scans. Les bonus ne peuvent compenser un défaut de sécurité fondamental.

## 10. Livrables obligatoires

Repo prêt à cloner ; README ; `.env.example` sans secret ; migrations ; scripts seed idempotents ; commandes lint/build/test ; frontend et backend lancés via Docker Compose ; minimum de tests automatisés ; description des limites, choix d'architecture et dette technique restante.


## 11. Addendum V2 : gouvernance du développement

Ce document est la source normative des exigences fonctionnelles et de sécurité. Les autres documents V2 définissent la méthode de travail, sans assouplir ces règles.

- Cinq rôles obligatoires : **Tech Lead/PM**, **UX/UI Designer**, **Développeur**, **Expert Cyber**, **QA/Reviewer**. Les rôles peuvent employer le même modèle sous des contextes distincts et doivent produire des artefacts vérifiables.
- Git, issues, branches `feature/`/`fix/`/`security/`, pull requests, revue par un rôle distinct et CI sont obligatoires. Le merge doit intervenir après la validation pertinente.
- Design : liberté sur la marque, la disposition des écrans, la navigation, les composants, les détails visuels et les interactions. Pas de maquette imposée. Les règles métier, la sécurité, les parcours et les technologies de base restent obligatoires.
- Innovation : bonus uniquement après le socle ; un bonus ne compense pas une faille critique ni une fonctionnalité manquante.
- Apprentissage : les agents peuvent proposer des **candidats skills** versionnés. Ils ne deviennent pas automatiquement actifs pendant ce benchmark et ne modifient pas les poids du modèle.
- Intervention du commanditaire : consultations libres, aucun score intermédiaire. Les changements normatifs doivent être envoyés de manière identique aux deux équipes, via un amendement daté.
- Les preuves de tests exécutés, les captures et les journaux de décision font partie des livrables obligatoires.
