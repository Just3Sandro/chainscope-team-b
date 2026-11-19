# PLAN — ChainScope V2, équipe B (48 h)

Rôle : Tech Lead / PM. Ce document opérationnalise la spec (01_*) et la méthode (03, 04, 05, 06, 07, 10). Il ne modifie aucun contrat normatif ; tout écart perçu est remonté comme `architecture-question`.

## 1. Objectif et périmètre 48 h (spec §9)

Livrer en **48 h murales** un SaaS de suivi de pentest multi-tenant **fonctionnel, sûr et reproductible**, évalué sur le produit, le processus Git, la sécurité, l'autonomie et les choix créatifs.

### Obligatoire (évalué, spec §9)

- Authentification réelle (sessions opaques hachées, Argon2id, CSRF) et rôles (`PLATFORM_ADMIN`, `TENANT_ADMIN`, `PENTESTER`, `CLIENT_VIEWER`).
- Multi-tenant strict : cabinet, client_org, memberships, aucune donnée croisée.
- Missions (engagements, statuts `DRAFT/IN_PROGRESS/CLOSED`), actifs, constats (CVSS 0–10, sévérités, statuts).
- Publication / rétractation explicite d'un constat ; portail client en lecture seule, publié uniquement.
- Preuves privées : upload validé, stockage hors webroot, téléchargement sécurisé.
- Graphe dirigé + chemins actifs **calculés côté serveur** (algorithme contractuel §4).
- UI utilisable (9 pages spec §7), sans données mockées pour une fonctionnalité métier.
- Tests significatifs (pytest + Postgres, Vitest, Playwright), migrations Alembic reproductibles, Docker Compose, seed de démonstration fictive idempotent, documentation d'installation.

### Bonus (non requis, spec §9 et §11)

Exports PDF, SSO/OIDC, MFA, billing, notifications temps réel, workers asynchrones, import CVE/CVSS, IA de rédaction, collaboration avancée, scans. **Un bonus ne peut compenser une faille de sécurité fondamental ni une fonctionnalité manquante.** Les bonus ne sont envisagés qu'après stabilisation du socle (fin J3 / J4) et doivent être documentés.

### Critères bloquants (plan de test §6)

Fuite cross-tenant, preuve non autorisée, escalation exploitable, connexion normale cassée, démarrage impossible depuis le clone, injection dans le rendu. Aucun bonus ne compense un blocage.

## 2. Épics, issues et dépendances

### Mapping ticket interne → issue GitHub (vérifié par `gh issue list`)

| Ticket | Issue | Sujet |
|---|---|---|
| CS-21 | #1 | PLAN + DECISIONS |
| CS-22 | #2 | DESIGN (marque, tokens, navigation, pages) |
| CS-23 | #3 | THREAT_MODEL |
| CS-01 | #4 | Backend socle : FastAPI, modèles, migrations, erreurs normalisées |
| CS-02 | #5 | Auth : sessions opaques hachées, Argon2id, CSRF, reset, bootstrap CLI |
| CS-03 | #6 | Invitations cabinet/client : expiration, usage unique, acceptation |
| CS-04 | #7 | Plateforme : GET/POST/PATCH `/platform/tenants` |
| CS-05 | #8 | Cabinet : clients, membres, engagements (CRUD + statuts) |
| CS-06 | #9 | Actifs + constats (CRUD + validation) |
| CS-07 | #10 | Publication / rétractation des constats |
| CS-08 | #11 | Preuves : upload validé, stockage privé, download sécurisé |
| CS-09 | #12 | Graphe : edges + chemins actifs côté serveur |
| CS-10 | #13 | Audit : AuditEvent append-only + request_id |
| CS-11 | #14 | API portail client (lecture seule, publié uniquement) |
| CS-12 | #15 | Seed de démonstration fictif idempotent |
| CS-13 | #16 | Docker Compose complet + healthchecks + migrations |
| CS-14 | #17 | CI GitHub Actions (pytest, vitest, build, Postgres) |
| CS-15 | #18 | Frontend socle : Vite/React/TS/Tailwind/Router/TanStack + pages auth |
| CS-16 | #19 | Dashboard cabinet + clients + engagements |
| CS-17 | #20 | Détail engagement : actifs, constats, preuves |
| CS-18 | #21 | Graphe interactif React Flow (vérité serveur) |
| CS-19 | #22 | Portail client + admin plateforme + journal d'audit (UI) |
| CS-20 | #23 | E2E Playwright + QA_REPORT + docs d'installation |

### Épics et ordre de réalisation

**Epic P — Planification/gouvernance (J1)** : #1 → #2 (design) et #3 (threat model) en parallèle. #3 doit précéder les endpoints sensibles (auth, upload, graphe, portail).

**Epic I — Infrastructure (dès J1, en parallèle)** : #16 (compose) puis #17 (CI). Le squelette compose (postgres 16 + mailpit + conteneurs vides avec healthchecks) est prêt avant le socle backend ; la CI couvre les tests dès le premier commit testable.

**Epic B — Backend (chaîne séquentielle, le chemin critique)** :
`#4 socle → #5 auth → #6 invitations → #7 plateforme → #8 cabinet (clients/membres/engagements) → #9 actifs+constats → #10 publication → #11 preuves → #12 graphe → #13 audit (complétion) → #14 portail client → #15 seed`.

Précisions de dépendances :
- **Audit (#13)** : la table `audit_events` et le service append-only sont créés **dans #4 (socle)** afin de journaliser dès le départ (logins, invitations…) ; #13 couvre l'intégration systématique, l'endpoint paginé admin et les tests F18.
- **#7 et #8** peuvent se recouper partiellement (même module RBAC), mais #7 (plateforme) reste en amont car la création de tenant invite l'admin cabinet.
- **#15 seed** dépend du schéma complet (#4–#14) et du jeu de référence (plan de test §1).

**Epic F — Frontend (parallèle au backend, dépend de l'API)** :
`#18 socle (app, routing, login + cookie/CSRF client) → #19 dashboard (missions, gravités, activité, filtres) → #20 détail engagement (actifs, constats, preuves) → #21 graphe React Flow (affichage de la vérité serveur uniquement) → #22 portail client + admin plateforme + journal d'audit`.
Le frontend ne commence une page que si l'API associée est mergeable ou son contrat figé ; aucune page factice avec données statiques (spec §7, 10_UX).

**Epic E — Clôture (J4)** : #23 (E2E Playwright des scénarios de référence, QA_REPORT, README/.env.example final, captures).

### Résumé visuel des dépendances

```
J1 :  #1 ─┬─ #2 (design)
          ├─ #3 (threat model)
          ├─ #16 compose ─ #17 CI
          └─ #4 socle backend (dont audit_events)
J2 :  #5 auth → #6 invitations → #7 plateforme → #8 cabinet → #9 actifs/constats   (backend)
      #18 socle FE → #19 dashboard                                                   (frontend, en parallèle)
J3 :  #10 publication → #11 preuves → #12 graphe → #13 audit API → #14 portail → #15 seed (backend)
      #20 détail engagement → #21 graphe FE                                          (frontend, en parallèle)
J4 :  #22 portail/admin/audit UI + corrections + #23 E2E/QA/docs
```

## 3. Jalons J1–J4 (48 h murales)

Horodatages indicatifs relatifs au top départ ; un jalon est validé par des **tests réellement exécutés et verts**, pas par déclarations.

### J1 — 0–6 h — Planification et socle (jalon 1 : planification)

Critères de complétion mesurables :
- Issues #1, #2, #3 fermées (PLAN + DECISIONS, DESIGN, THREAT_MODEL merges).
- #16 : `docker compose up --build` démarre Postgres 16 + Mailpit + squelettes backend/frontend avec healthchecks.
- #17 : CI GitHub Actions verte sur PR et `main` (pytest, vitest, typecheck/build, Postgres service).
- #4 : migrations Alembic reproductibles (`alembic upgrade head` sur base vide), erreurs normalisées `{error:{code,message,request_id}}`, `X-Request-ID` garanti, aucune donnée de démo en source.
- Bootstrap admin CLI opérationnel (D-14) sur la base de dev.

### J2 — 6–24 h — Vertical slice (jalon 2 : connexion réelle → mission → constat visible)

Critères mesurables (scénarios F01–F04 du plan de test, tests verts + capture) :
- **Démontré par test** : login réel (cookie `cs_session` + CSRF) → déconnexion (révocation, F01) → acceptation d'invitation à usage unique (F02) → le superadmin crée le tenant **Aegis Red Team** → l'admin Aegis crée le client **Acme Santé** et l'engagement **Audit Web 2026** (F03) → le pentester Aegis ajoute les actifs **Web / API / DB** et un constat (F04), visibles côté cabinet (API + UI dashboard).
- Issues #5, #6, #7, #8, #9 (backend) et #18, #19 (frontend) fermées ; parcours complet navigable dans le navigateur.
- Matrice RBAC de base testée (403 inter-rôles sur au moins les routes cabinet/plateforme).

### J3 — 24–40 h — Cœur métier (jalon 3 : graphe serveur, publication, preuves privées)

Critères mesurables (F05–F14, F18) :
- Publication : F05 (non publié invisible même avec l'ID deviné), F06 (publié visible au client autorisé, invisible à un autre client), F07 (client ne peut pas modifier).
- Preuves : F12 (upload PNG/PDF → stockage privé, SHA-256 correct, download `attachment`+`nosniff`), F13 (ID deviné refusé tant que non publié/visible), F14 (type interdit ou >10 Mio refusé, rien stocké durablement).
- Graphe : F08 (chemin Web→API→DB, **score 75.0** avec le jeu de référence, ordre stable), F09 (F2→`REMEDIATED` : chemin disparu sans supprimer l'edge), F10 (`ACCEPTED_RISK` : chemin réactivé), F11 (edge cross-engagement rejeté, base inchangée) ; `GRAPH_TOO_COMPLEX` (422) testé sur un graphe dense synthétique.
- Portail client API (#14) : constats publiés uniquement ; preuves publiées ET `client_visible`.
- Audit (#13) : F18 (action sensible → `audit_events`, aucun token/mot de passe dans les logs ou métadonnées).
- Seed (#15) : `python -m app.cli seed` idempotent (exécution doublée sans duplication), jeu de référence §1.
- Frontend : #20 (détail engagement) et #21 (graphe React Flow affichant **la vérité serveur**) fermés.

### J4 — 40–48 h — Finition (jalon 4 : E2E, isolation, CI verte, captures)

Critères mesurables :
- #22 fermé : portail client, admin plateforme (sans lecture de données métier), journal d'audit UI.
- #23 : suite E2E Playwright verte couvrant au minimum : installation propre F20 (`docker compose up --build` depuis clone + migrations + seed + bootstrap), persistance F19 (restart compose, sessions valides non expirées), XSS F15, CSRF F16, mass-assignment F17 ; scénarios publics §2 du plan de test rejoués via E2E.
- Matrice d'isolation cross-tenant (§3 plan de test) exécutée et documentée (lectures/écritures/téléchargements/filtres avec ID échangés).
- CI verte sur `main` ; `docs/QA_REPORT.md` final avec **commandes + logs réellement exécutés** ; README + `.env.example` vérifiés par un install testeur.
- Captures des 9 pages (spec §7) conservées dans le dépôt (dossier `docs/captures/` ou artefacts E2E).
- Aucun critère bloquant (§6 plan de test) connu non corrigé ; sinon issue ouverte + documentation explicite (règle 04 §PR).

## 4. Politique qualité (règles 03/04)

- **Toute PR** : revue **QA obligatoire** (rôle distinct de l'auteur) + revue **Cyber** si le diff touche auth/sessions/CSRF, invitations, RBAC, isolation tenant, upload/preuves, graphe, audit, portail client, seed, migrations.
- **Tests réellement exécutés et verts avant merge** : pytest (unit + intégration API sur Postgres), vitest, typecheck/build ; Playwright quand le diff concerne un parcours E2E. Interdiction de déclarer « vert » sans log conservé (CI et `QA_REPORT.md`).
- **CI sur PR et `main`** : échec CI = PR non fusionnée (correction dans la même branche ou commit de suivi).
- **Convention** : branches `feature/<issue>-slug`, commits conventionnels en français (`feat:`, `fix:`, `test:`, `docs:`, `security:`), un diff focalisé par issue, jamais de push direct sur `main`, `Closes #n` dans la PR.
- **Invariants métier sous test** : CVSS borné 0–10, statuts de mission/constat, `CLOSED` interdisant les mutations techniques (réouverture admin tenant), publication indépendante de l'état, `REMEDIATED` ≠ chemin actif, `ACCEPTED_RISK` = chemin actif.
- **Autocorrection autorisée** mais la revue finale d'une PR sensible reste due par un rôle distinct ; les limites de l'indépendance (même modèle, contextes séparés) sont documentées dans `QA_REPORT.md` (règle 03 §3).
- **Aucun secret commité** ; `.env.example` sans valeur réelle ; données 100 % fictives ; pas de scan de services tiers.

## 5. Registre des risques (top 8)

| # | Risque | Impact | Mitigation | Propriétaire |
|---|---|---|---|---|
| R1 | Chemin critique séquentiel backend (12 issues) en 48 h | Retard sur le cœur métier, jalons J2–J3 manqués | Vertical slice dès J2 ; frontend/infra en parallèle ; audit intégré au socle ; arbitrages prioritaires quotidiens (Tech Lead) | Tech Lead |
| R2 | Erreur sur l'algorithme contractuel du graphe (F08–F11) | Jalon 3 non validé, critère bloquant si mal géré | Tests unitaires sur le jeu de référence (score 75.0) + cas limites (cycles, égalités de score, >6 sauts, sans crown jewel, doublons d'edges) ; budget DFS 50 000 expansions → 422 `GRAPH_TOO_COMPLEX` documenté (D-10) | Développeur + QA |
| R3 | Fuite cross-tenant / IDOR sur une resource | Critère bloquant (§6) | RBAC par ressource (jamais par URL ni par rôle client fourni), FK composites dès que praticable, matrice §3 plan de test exécutée en J4, revue Cyber sur toute PR sensible | Cyber |
| R4 | Défaut sessions/CSRF/upload (F12–F14, F16) | Critère bloquant sécurité | THREAT_MODEL avant les endpoints (J1) ; Argon2id, sessions opaques hachées révoquables, `puremagic`+extension, plafond 10 Mio, `nosniff`/`attachment` ; tests F12–F14, F16 en J3–J4 | Cyber |
| R5 | Dérive de périmètre (bonus, pages factices, sur-design) | Manque de fonction obligatoire | Périmètre strict spec §9 ; bonus seulement après J3 stabilisé ; 10_UX : aucun mock pour une fonctionnalité métier ; arbitrages consignés dans DECISIONS.md | Tech Lead |
| R6 | Environnement non reproductible (F19/F20) | Clôture impossible, critère bloquant | Compose comme référence d'installation dès J1 ; healthchecks + migrations dans CI ; F19 (restart) et F20 (clone propre) testés explicitement en J4 | Développeur + QA |
| R7 | Indépendance de revue limitée (5 rôles = même modèle) | Défaut non détecté | Contextes et prompts strictement séparés par rôle ; reviews documentées dans les PR ; QA peut refuser un merge ; limitation explicitement déclarée dans QA_REPORT (règle 03 §3) | Tech Lead |
| R8 | Complexité UI graphe React Flow (dernier livrable frontend visible) | J4 non atteint, page 7 spec §7 absente | Le graphe UI n'affiche que la vérité serveur (pas de recalcul client, 10_UX) ; états vides/chargement/erreur dès #18 ; #21 borné à l'affichage nœuds/edges/chemin sélectionnable + positions persistées | Designer + Développeur |

## 6. Plan de clôture

### Livrables obligatoires (spec §10, 06 §livraison, 07)

- Dépôt clonable et README : installation (`docker compose up --build`), commandes lint/build/test, seed, bootstrap admin, URL de démo locale.
- `.env.example` **sans secret** (toutes les variables documentées, valeurs fictives).
- Migrations Alembic reproductibles + seed idempotent (`python -m app.cli seed`, `python -m app.cli create-platform-admin`).
- Docker Compose : frontend, backend, postgres 16, Mailpit (dev), healthchecks, migrations.
- Tests automatiques minimum : pytest (+ intégration Postgres), vitest, Playwright E2E — **réellement exécutés, logs conservés**.
- Documents : `docs/PLAN.md` (ce fichier), `docs/DECISIONS.md`, `docs/DESIGN.md`, `docs/THREAT_MODEL.md`, `docs/QA_REPORT.md`.
- Captures des 9 pages (spec §7) et preuves des scénarios de référence (F01–F20).
- Description des limites, choix d'architecture et dette technique restante.
- Candidats skills (le cas échéant) dans `skill_candidates/<slug>/SKILL.md`, statut « candidate (non activée) », gabarit 05 respecté.
- Bilan : commit/tag `benchmark-final`, liste des PR/issues, temps/tokens/contexte, déclaration honnête des tests exécutés, interventions extérieures (aucune attendue : Qwen uniquement).

### Procédure de clôture (fin J4)

1. Vérifier chaque livrable de la liste ci-dessus ; aucune case non remplie non documentée.
2. `QA_REPORT.md` final : commandes, logs, verdicts, limites (indépendance de revue, rate limiting mémoire, etc.).
3. Fermer les issues livrées ; ouvrir des issues de suivi explicites pour tout hors périmètre connu (règle 04).
4. Tag `benchmark-final` sur `main` (après merges revus et CI verte), archiver les logs CI/E2E.
5. Rapport de clôture au commanditaire : **faits sans auto-notation** (issues fermées, PR, CI, démo, blocages).
