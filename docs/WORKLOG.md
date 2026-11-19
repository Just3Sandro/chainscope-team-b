# WORKLOG — Équipe B (chaîne Qwen3.8-27B, OpenCode)

Journal opérationnel : horodatage (Europe/Paris), faits, interventions, état. Ce fichier vit sur la branche `docs/worklog-state` ; il sera consolidé dans la PR de clôture (#23) puis mis à jour à chaque incident.

## Chronologie

| Heure (Paris) | Événement |
|---|---|
| 2026-11-19 11:58 | **TOP DÉPART** — feu vert du commanditaire, accès effectif au dépôt `chainscope-team-b` (baseline `b13cd42`) |
| 11:59–12:01 | Lecture intégrale des documents 01–10 + AGENTS.md ; vérification environnement (gh auth OK, Python 3.14, Node 22, Docker CLI présent) |
| 12:02 | Création des labels (feature, security, infrastructure, docs, test) ; venv Python partagé lancé en arrière-plan |
| 12:02–12:03 | Création des 23 issues GitHub (#1–#23, mapping interne CS-01…CS-23, cf. `docs/PLAN.md`) |
| 12:04 | Lancement Jalon 1 : 3 sous-agents Qwen en parallèle (tech-lead → `feature/1-plan-backlog`, designer → `feature/2-design-system`, cyber → `feature/3-threat-model`) |
| 12:04:35 | tech-lead livré : `docs/PLAN.md` + `docs/DECISIONS.md` (D-01…D-16) ; **PR #24** ouverte 12:04:41 |
| 12:04:53 | cyber livré : `docs/THREAT_MODEL.md` (50 menaces T-01…T-50, matrice de couverture) ; **PR #25** ouverte 12:05:00 |
| 12:05:12 | designer livré : `docs/DESIGN.md` (tokens Tailwind v4, 9 pages, graphe, a11y, bonus) ; **PR #26** ouverte 12:05:20 |
| 12:05–12:09 | Revue orchestrator des 3 livrables : conformité spec vérifiée (aucun changement normatif), qualité jugée suffisante pour la passe QA |
| 12:05 | Incident environnement : daemon Docker non démarré (pas de socket) ; EDB ne fournit plus de tarball Postgres Linux ; PyPI accessible |
| 12:07 | Question 1 au commanditaire (mode Postgres/Docker) → réponse : « Tu lances Docker » |
| 12:08 | Socket Docker présent mais `root:docker 0660` et groupe `docker` vide → permission denied ; question 2 |
| 12:09 | **Commanditaire** : redémarrage du poste prévu pour corriger Docker ; consigne d'arrêt propre — changements sauvegardés sur branches, pas de push direct sur main |
| 12:09–12:10 | `docs/WORKLOG.md` écrit et poussé sur `docs/worklog-state` |

### INTERRUPTION (redémarrage du poste) — 12:10 → 13:43

| Heure (Paris) | Événement |
|---|---|
| 13:43 | **REPRISE** — message de reprise commun ; incident Docker déclaré résolu (daemon 29.10.0, overlay2) |
| 13:45 | Vérification état : main à `b13cd42`, 3 PR ouvertes, 23 issues ouvertes, worktrees `/tmp/opencode/wt-*` et venv perdus au redémarrage ; `git worktree prune` effectué |
| 13:47 | Accès socket Docker encore refusé : le commanditaire a exécuté `usermod -aG docker pedruntu` (groupe visible) mais la session OpenCode (démarrée avant) n'en hérite pas — limitation Linux : un arbre de processus ne gagne pas de groupes supplémentaires après son démarrage |
| 13:55 | Question au commanditaire ; choix : `sudo chmod 666 /var/run/docker.sock` (immédiat) — **intervention environnement, non technique** |
| 14:00 | Accès Docker validé (socket 666, daemon overlay2) ; conteneurs de dev relancés : `cs-pg-dev` (postgres:16, user `chainscope`, DBs `chainscope` + `chainscope_test`) et `cs-mailpit-dev` (SMTP 1025, UI 8025) |
| 14:02 | venv Python partagé recréé (`/tmp/opencode/venv`, SQLAlchemy 2.1.9, dépendances identiques) |
| 14:05 | Passe QA (sous-agent Qwen) lancée sur PR #24/#25/#26 |

**Interventions extérieures cumulées** : aucune instruction de développement. Deux interventions infrastructure (relancer Docker puis autoriser l'accès socket) et deux questions environnement posées au commanditaire. Tous les sous-agents restent sur `openrouter/qwen/qwen3.8-27b`.

## État courant

**Fermé (livré, en attente de merge) :**
- Jalon 1 (planification) : 3 PR ouvertes et MERGEABLE, à reviewer par QA puis merge orchestrator :
  - #24 `feature/1-plan-backlog` — PLAN.md + DECISIONS.md (Closes #1)
  - #25 `feature/3-threat-model` — THREAT_MODEL.md (Closes #3)
  - #26 `feature/2-design-system` — DESIGN.md (Closes #2)
- Backlog GitHub : 23 issues créées et mappées (#1–#23).

**Interactions humaines / assistance (déclaration 07_PROMPT) :**
- Aucune instruction technique reçue. Échanges environnement uniquement (lancer Docker, redémarrer le poste). Aucun appel cloud non-Qwen ; tous les sous-agents tournent sur `openrouter/qwen/qwen3.8-27b` (opencode.json).
- Les 2 questions posées au commanditaire (mode Postgres local ; accès Docker) sont des demandes d'infrastructure, pas d'assistance développement.

**À faire (ordre) — 1 à 3 exécutés à 14:02 :**
1. ✅ Docker validé ; conteneurs de dev relancés (`cs-pg-dev` postgres:16 — user `chainscope`, DBs `chainscope` + `chainscope_test` ; `cs-mailpit-dev` — SMTP 1025, UI 8025). Mots de passe fictifs dev-only ; les valeurs livrées passent par `.env.example` sans secret réel.
2. ✅ venv recréé (`/tmp/opencode/venv` : fastapi, uvicorn[standard], sqlalchemy, alembic, pydantic, pydantic-settings, argon2-cffi, httpx, pytest, pytest-asyncio, puremagic, python-multipart, email-validator, greenlet).
3. ✅ `git worktree prune` (les worktrees `/tmp/opencode/wt-*` étaient perdus ; les branches vivent sur GitHub).
4. ✅ Revue QA #1 (13:02Z) : #24 approuvé ; #25/#26 demandent corrections → corrections poussées par Cyber (`d05139a`) et Designer (`b5095ab`) + retours Tech Lead sur #24 (`b861477`) ; coquille DESIGN P8 corrigée par l'orchestrator (`02da5ff`).
5. ✅ Re-revue QA (13:02Z) : 3 × « prêt à merge » (0 écart restant, cohérence croisée D↔T↔DESIGN vérifiée).
6. ✅ **Jalon 1 CLOS** (13:03Z) : PR #24/#25/#26 fusionnées en squash sur main (`77c5220`, `3f45af8`, `24651ed`) ; issues #1/#2/#3 fermées.
7. Issue de suivi **#27** créée (visibilité comptes plateforme P8, P2, à trancher avec #7).
8. ✅ **Jalon 2 lancé** (13:10Z) : 2 sous-agents Développeur en parallèle — socle backend `feature/4-backend-socle` (issue #4) et socle frontend `feature/18-frontend-socle` (issue #18, DESIGN.md §2.2/§4/§5.P1).

**Rappels de process (03/04) :** branche par issue, PR avec `Closes #n`, revue QA (+ Cyber si sensible) par un rôle distinct, tests réellement exécutés avant merge, jamais de push direct sur `main`, commits conventionnels en français.
