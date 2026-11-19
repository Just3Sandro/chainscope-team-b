# DECISIONS — ChainScope V2, équipe B

Registre des décisions non prescrites (règle 03 §4). Structure : date, statut, décision, alternatives, compromis, impact. Les décisions ne modifient jamais un contrat normatif de la spec ; un doute relevé est remonté au commanditaire (`architecture-question`).

## D-01 — Layout du dépôt
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : à la racine du dépôt : `backend/` (FastAPI, couches internes `api / services / repositories / models / schemas / security`), `frontend/` (Vite + React + TypeScript + Tailwind + React Router + TanStack Query), `e2e/` (Playwright), `docker-compose.yml` à la racine, `docs/` (plans, design, threat model, QA report, captures), `skill_candidates/` (le cas échéant). Le frontend est servi par le backend (ou Vite proxy en dev) pour éviter les origines multiples (spec §2).
- **Alternatives** : un seul package Python avec la SPA incrustée ; layout `infra/` dédié ; `e2e` dans `frontend/`.
- **Compromis** : `e2e/` séparé garde le frontend léger et la suite Playwright versionnée à part ; une seule source Compose à la racine simplifie F20 (installation propre) au prix d'une racine un peu occupée.
- **Impact** : toutes les équipes (conventions de paths dans CI, compose, imports, docs).

## D-02 — Image Python du backend
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : image Docker backend `python:3.12-slim` (spec exige 3.12+ ; `slim` réduit la surface). Le développement local peut tourner sous une version plus récente (ex. 3.14) via le venv partagé ; l'environnement livré (compose, CI) reste 3.12.
- **Alternatives** : gel complet sur 3.12 y compris en dev ; image `python:3.12` non slim.
- **Compromis** : écart éventuel dev/livré documenté ici ; `slim` au lieu de l'image complète pour un poids et une surface d'attaque moindres.
- **Impact** : Dockerfile backend, CI (job tests), README (note dev).

## D-03 — Génération des identifiants (UUID)
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : tous les `id` (UUID) sont générés **côté serveur** (Python) ; le type de colonne SQLAlchemy `Uuid` portable est utilisé pour toutes les clés et FK. Les UUID fournis par le client sont rejetés pour la création ; les références en lecture ne sont jamais validées sur un `tenant_id` reçu du frontend (spec §5).
- **Alternatives** : génération côté base (`uuid_generate_v4`) ; génération côté frontend.
- **Compromis** : le `Uuid` portable au lieu du type `UUID` Postgres natif facilite la reproductibilité (D-16) au prix d'une abstraction fine en migration.
- **Impact** : modèle de données, migrations, services (anti mass-assignment, F17).

## D-04 — Cookie de session
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : cookie nommé `cs_session`, `HttpOnly`, `SameSite=Lax`, `Secure` lorsque `ENV=production` ; jamais accessible au JavaScript, logs, URL ou HTML (spec §8).
- **Alternatives** : JWT porteur (non révocable sans état) ; nom `session_id` ; `SameSite=Strict`.
- **Compromis** : `Lax` (et non `Strict`) pour rester utilisable depuis une navigation classique tout en conservant la session côté serveur hachée et révocable (exigence spec : révocation à la déconnexion et au changement de mot de passe) ; le nom explicite `cs_session` évite la collision avec d'autres apps.
- **Impact** : middleware auth, tests sessions (F01), démo.

## D-05 — Protection CSRF
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : token CSRF **opaque par session** : exposé en clair uniquement via `GET /auth/csrf`, son **hash est stocké** dans `sessions.csrf_token_hash` ; tout `POST/PATCH/PUT/DELETE` cookie-based exige le header `X-CSRF-Token` correct (sinon 403).
- **Alternatives** : double-submit cookie ; vérification d'Origin/Referer seule ; exclusion des GET.
- **Compromis** : le header (et non le body) évite la fuite dans les journaux ; le pattern token/hash rend la fuite du token sans le hash inoffensive ; `SameSite=Lax` ne remplace pas ce contrôle (exigence spec §8) mais le complète.
- **Impact** : toutes les mutations (F16), frontend (lecture du token avant mutation), docs de sécurité.

## D-06 — X-Request-ID
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : le middleware **génère un `X-Request-ID` (UUID) si absent**, le propage au contexte applicatif, le persiste dans `audit_events.request_id` et le renvoie dans toute réponse d'erreur normalisée `{error:{code,message,request_id}}`.
- **Alternatives** : confiance au `X-Request-ID` client ; pas de request ID ; request ID seulement en production.
- **Compromis** : la génération côté serveur garantit la présence et l'intégrité (un ID client ne fait pas autorité) ; l'ID renvoyé dans les erreurs aide la traçabilité sans exposer de secret.
- **Impact** : middleware global, schéma d'erreur, audit (F18).

## D-07 — Rate limiting
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : limitation en mémoire par **fenêtre glissante** sur `POST /auth/login`, `forgot-password`, `reset-password` et `accept-invitation` ; réponse et délai de calcul identiques qu'un compte existe ou non (anti-enumeration, spec §8). **Limitation documentée** : état non partagé entre instances/processus — acceptable pour l'installation livrée (une instance), hors périmètre spec §2 (pas de Redis requis).
- **Alternatives** : Redis (hors périmètre et outillage supplémentaire) ; pas de limitation.
- **Compromis** : simple et suffisant pour le SaaS mono-instance livré ; l'écart multi-instances est consigné ici et dans README/QA_REPORT (pas de revendication de conformité, spec §8).
- **Impact** : routes auth, docs limites, revue Cyber.

## D-08 — Validation des uploads de preuves
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : validation triple : extension autorisée parmi `{.pdf, .png, .jpg, .jpeg, .txt}`, taille ≤ **10 Mio** (sinon 413, rien stocké durablement), et **signature binaire vérifiée via `puremagic`** (PDF/PNG/JPEG/TXT) ; le MIME déclaré doit être cohérent avec la signature détectée. Codes d'erreur harmonisés : `400` = contenu invalide (signature/extension incohérente, type interdit), `413` = taille > 10 Mio, `422` = schéma multipart invalide. Le nom de fichier fourni est ignoré (D-09).
- **Alternatives** : extension seule ; MIME déclaré seul ; décodage par bibliothèques d'images (Pillow) pour les PNG/JPEG.
- **Compromis** : `puremagic` (sniffing de magic bytes) est léger et sans dépendance d'imagerie au prix d'une heuristique documentée pour les TXT (contenu texte simple vérifié) ; la cohérence signature/extension empêche les faux MIME (plan de test §3).
- **Impact** : route upload preuves (F12, F14), tests de contenu.

## D-09 — Stockage des preuves
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : volume local privé `data/evidence/<tenant_id>/<uuid><ext>` ; le chemin interne est **généré par le serveur** (imprévisible, jamais dérivé du nom utilisateur) ; **aucun accès direct/statique** au stockage : téléchargement exclusivement via la route autorisée (`Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, autorisation complète : cabinet ou client publié+`client_visible`). L'interface de stockage est abstraite (évolution objet ultérieure, spec §2).
- **Alternatives** : BLOB en base ; répertoire statique public ; stockage à la racine des données applicatives.
- **Compromis** : le volume local (au lieu du BLOB) conserve la base légère et correspond à l'exigence de « volume local privé persistant » ; l'isolement par sous-répertoire tenant renforce la séparation au niveau fichier.
- **Impact** : F12–F13, sécurité (D-08), compose (volume persistant, F19).

## D-10 — Plafond de complexité du graphe
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : l'algorithme contractuel (chemins simples, 1 à 6 relations, max 20 résultats, score `round(2 * criticality_cible * min(cvss_edges), 1)` borné 0–100, tri score décroissant → longueur croissante → liste ordonnée des `edge_ids`) est implémenté **sans modification** ; pour limiter les abus, l'exploration DFS est plafonnée à **50 000 expansions** : au-delà, réponse **422 code `GRAPH_TOO_COMPLEX`** avec message stable, sans renvoyer de résultat partiel. Les limites denses (≤150 actifs, ≤300 edges par engagement, spec §4) sont appliquées à la création avec 422/400 explicite.
- **Alternatives** : timeout de calcul ; troncature partielle des résultats ; pas de plafond d'exploration.
- **Compromis** : le plafond est une **limite de densité documentée** (et testée), pas une triche sur l'algorithme : tant que le budget n'est pas atteint, les résultats sont complets, stables et conformes au contrat ; un rejet 422 explicite est préférable à un calcul non borné (DoS, spec §4).
- **Impact** : F08–F11, tests de densité, docs limites (QA_REPORT).

## D-11 — Pagination
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : toutes les listes paginent avec `?limit=20&offset=0` ; `limit` borné à **100** (422 au-delà), filtres applicables côté serveur sur les recherches/lists (spec §6).
- **Alternatives** : pagination par curseur ; pages fixes ; pas de bornage.
- **Compromis** : `limit/offset` respecte le contrat spec §6 au prix d'une lecture positionnelle (suffisante aux volumes du périmètre, F19).
- **Impact** : toutes les GET lists (cabinet, portail, audit), API schema partagée.

## D-12 — E-mails en développement
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : si `SMTP_HOST` est défini (Mailpit dans le compose), les e-mails (invitation, mot de passe oublié) sont envoyés par SMTP classique ; à défaut (dev minimal), un transport **log** écrit la ligne `DEV-EMAIL to=<email> subject=<s> token=<token>` dans la console — **dev uniquement**, et la variable `ENV=production` interdit ce transport (erreur de configuration). Les tokens restants hachés en base ne sont jamais loggés autrement.
- **Alternatives** : SMTP seul (obligation de Mailpit en dev) ; transport mémoire non observable ; e-mails réels.
- **Compromis** : le log de dev facilite la démo des flux invitation/reset sans service SMTP, en restant explicite (préfixe `DEV-EMAIL`) et interdit en production ; les données sont 100 % fictives (contrainte benchmark).
- **Note sécurité** : (a) le transport log est strictement interdit si `ENV=production` (erreur de configuration, déjà le cas) ; (b) c'est l'**exception documentée unique** au principe « pas de secrets dans les logs » (spec §3.9) — elle est bornée au dev sans SMTP et suivie dans `QA_REPORT.md`, en cohérence avec le THREAT_MODEL ; (c) les `audit_events` ne portent **jamais** de token ni de mot de passe (garanti par le test F18) ; (d) dans le compose de livraison (Mailpit SMTP actif), les tokens passent par l'e-mail et non par les logs — le log `DEV-EMAIL` n'est alors plus utilisé.
- **Impact** : routes invitations/reset, compose (Mailpit), `.env.example`.

## D-13 — Seed de démonstration
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : seed **idempotent** exécutable par CLI `python -m app.cli seed`, matérialisant le **jeu de référence du plan de test §1** (fictif) : tenants `Aegis Red Team` / `Boreal Security`, clients `Acme Santé` / `Boreal Finance`, engagements (`Audit Web 2026`, `Audit AD 2026`, `Audit Externe 2026`), les 6 utilisateurs de référence, et pour `Audit Web 2026` les actifs `Web` (entry point), `API`, `DB` (crown jewel, criticality 5), findings `F1` (CVSS 8.8, OPEN) et `F2` (CVSS 7.5, OPEN), edges `Web→API (F1)`, `API→DB (F2)` (score attendu du chemin : 75.0). Idempotence : upsert par clés naturelles (slugs tenants/clients, emails, noms d'actifs/constats) — réexécution sans duplication.
- **Alternatives** : seed par appels API (dépend d'admin + invitations + mot de passe) ; seed aléatoire ; fixture par test uniquement.
- **Compromis** : la CLI insère directement (transaction unique) ce qui est simple et reproductible pour F03–F11 et F20, au prix d'un chemin de test qui n'exerce pas les API d'écriture (les API restent couvertes par les tests d'intégration).
- **Impact** : E2E, démo, F08 (score 75.0), F20.

## D-14 — Bootstrap administrateur plateforme
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : création du superadministrateur par **commande CLI explicite** `python -m app.cli create-platform-admin --email <e> --password <p>`, ou par variables d'environnement (`PLATFORM_ADMIN_EMAIL` / `PLATFORM_ADMIN_PASSWORD`) au premier démarrage si aucune ligne `platform_admins` n'existe ; **jamais de mot de passe administrateur fixé dans les sources** (spec §3.1). L'opération est journalisée (audit event, tenant null).
- **Alternatives** : auto-création avec mot de passe aléatoire non récupérable ; création uniquement par un autre admin (boucle de bootstrapping) ; seed inclus.
- **Compromis** : l'env var au premier boot facilite la démo (F20) tandis que la CLI explicite reste la référence traçable ; le risque d'oubli des variables est documenté dans README/.env.example.
- **Impact** : J1, F20, sécurité (secrets jamais commités).

## D-15 — Modèle de collaboration agentique
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : les 5 rôles obligatoires (Tech Lead/PM, UX/UI Designer, Développeur, Expert Cyber, QA/Reviewer) sont portés par **sous-agents Qwen distincts** (contextes et prompts séparés, mandat 03/07 et AGENTS.md) ; le **Tech Lead orchestre les merges** après revue QA (+ Cyber si sensible, cf. `docs/PLAN.md` §4 « Politique qualité ») ; **aucune notation interne** pendant le benchmark ; toute assistance non Qwen devrait être déclarée comme assistance externe (aucune prévue).
- **Alternatives** : agent unique multi-rôles ; modèle de secours différent ; revue humaine.
- **Compromis** : l'indépendance des revues est structurelle (rôle distinct) mais limitée par l'usage d'un même modèle — cette limite est consignée dans `QA_REPORT.md` (règle 03 §3 : revue non considérée aussi indépendante qu'humaine).
- **Impact** : processus Git (PR, reviews), preuves de collaboration (issues, docs, verdicts).

## D-16 — Environnement local de développement
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : Postgres **16 en Docker** pour tout le monde (dev, CI, démo) ; **venv Python partagé** pour le backend (dev hors Docker possible) ; `docker compose up --build` est la **référence d'installation** (F20) : conteneurs postgres 16, backend (python:3.12-slim, Alembic), frontend (build + service), mailpit (dev), volumes persistants (`db`, `data/evidence`), healthchecks et migrations automatiques au démarrage du backend. Toutes les variables sont documentées dans `.env.example` (sans secret : `ENV`, `DATABASE_URL`, `SMTP_HOST`, bootstrap admin, limites de dev).
- **Alternatives** : SQLite pour la dev (écarts de comportement Postgres) ; virtualenv par service ; dev entièrement Dockerisé.
- **Compromis** : Postgres 16 partout garantit la parité avec le livrable (F19/F20, index et FK composites) ; le venv partagé simplifie l'itération backend, au prix d'un dev qui dépend de Docker pour Postgres — documenté dans le README.
- **Impact** : J1 (infrastructure), CI, README, `.env.example`, tests d'intégration.

## D-17 — Contrat de l'endpoint `GET /auth/me`
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : fige le contrat de `GET /api/v1/auth/me`, authentifié par le cookie `cs_session` (D-04). `401` si non connecté. Réponse JSON (200) :
  ```json
  {
    "id": "<uuid user>",
    "email": "…",
    "is_active": true,
    "platform_admin": false,
    "tenant_memberships": [
      {"tenant_id": "…", "tenant_name": "…", "slug": "…", "role": "TENANT_ADMIN"}
    ],
    "client_memberships": [
      {"client_org_id": "…", "client_org_name": "…", "tenant_id": "…"}
    ]
  }
  ```
  Règles : `platform_admin` = présence dans `platform_admins` (la table ne porte pas de champ `role` — booléen, spec §5) ; les arrays sont vides `[]` et non `null` ; `is_active=false` ⇒ `401` (compte suspendu traité comme non connecté, aucune fuite d'existence) ; le tenant d'un PENTESTER apparaît dans `tenant_memberships` avec son `role` ; aucun secret ni hash dans la réponse ; la décision du « tenant courant » est côté **client** par défaut (`tenant_memberships[0]`) avec possibilité de sélection — le serveur exige toujours le tenant via l'URL pour les routes cabinet (spec §6).
- **Alternatives** : payload d'identité dupliqué par route ; endpoint `/auth/profile` dédié ; rôle global unique dans la réponse. Rejetées pour le périmètre : un seul endpoint canonique couvre la navigation par rôle des 5 pages de J2 sans doublon de contrat.
- **Compromis** : le contrat figé découple le frontend (#18, déjà en cours) du backend (#5, non implémenté) pendant le jalon 2, aligné avec D-01 (layout) et D-04 (cookie session) ; la « sélection » de tenant reste un état purement client, le serveur ne s'en fie jamais (spec §5 : aucune permission déduite du client) ; extension ultérieure possible par ajout de champs (compatibilité ascendante), sans modification de ceux-ci.
- **Impact** : issue #5 (implémentation backend conforme à ce contrat, revue Cyber), issue #18 (client + navigation par rôle du socle frontend), issue #19 (dashboard consomme `tenant_memberships[0]` comme tenant courant).

## D-19 — Politique CSRF et exemptions (auth)
- **Date** : 2026-11-19 — **Statut** : adoptée
- **Décision** : précision opérationnelle de D-05, portée par la PR #32 (issue #5). Le middleware CSRF (ASGI, global) s'applique à toute mutation `POST/PATCH/PUT/DELETE` sous `/api/v1` :
  - **Exemptions contexte sans session — toujours exemptes, même avec un cookie de session valide** : `POST /auth/login`, `POST /auth/reset-password`, `POST /auth/accept-invitation`. Justification : le bootstrap de session est impossible sans l'exemption du login ; le reset et l'acceptation d'invitation reposent sur des **tokens à usage unique** et des **rate limits** (THREAT_MODEL T-21/T-24 : clés e-mail+IP ou IP).
  - **Exemption conditionnelle** : `POST /auth/forgot-password` est exempt **uniquement sans session active** (cookie absent, inconnu, expiré ou révoqué) ; avec une session valide, le header `X-CSRF-Token` est exigé — sinon un attaquant avec une page tierce pourrait inciter la victime connectée à déclencher des resets et casser ses tokens.
  - **Toute autre mutation** `POST/PATCH/PUT/DELETE` sous `/api/v1` avec session valide exige `X-CSRF-Token` valide, sinon **403, code `CSRF_INVALID`** (corps d'erreur normalisé avec `request_id`, D-06).
  - **Sans session valide**, le middleware laisse passer la requête et la dépendance d'authentification répond 401 : états « non connecté » et « CSRF invalide » indiscernables (THREAT_MODEL T-12/T-13).
  - Le token reste **stable par session** (D-05 demeure la référence) : la rotation à chaque émission via `GET /auth/csrf` proposée dans la PR #32 est **en arbitrage Cyber sur cette PR** et n'est pas consignée ici pour l'instant.
- **Alternatives** : aucune exemption (impossible — le bootstrap de session serait mort-né) ; exemption de tout `/auth/*` (rejetée — le forgot-password avec session et le logout doivent rester protégés) ; double-submit cookie (incompatible avec le pattern token/hash de D-05).
- **Compromis** : confiance dans `SameSite=Lax` + token de session (D-04/D-05) pour le reste de la surface ; l'exemption `POST /auth/accept-invitation` n'est testée qu'**à partir de l'issue #6** (route non routée dans #5).
- **Impact** : middleware `backend/app/security/csrf.py` (issue #5), tests F16 et T-12/T-13, frontend #18 (le token doit être envoyé sur toute mutation non exemptée), issue #6 (accept-invitation), revue Cyber de la PR #32 (arbitrage rotation).
