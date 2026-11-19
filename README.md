# ChainScope — Benchmark V2 prêt au lancement

**Projet :** SaaS pentest multi-tenant, graphe d'attaque, preuves et portail client.  
**But :** comparer deux chaînes de développement sur un cahier des charges unique.  
**Équipe A :** architecte commun + développeurs Claude/Codex.  
**Équipe B :** même architecte commun + développeurs Qwen3.8-27B.  
**Temps :** 48 h par équipe, horloge de travail documentée.  
**Notes :** aucune avant les deux clôtures.  
**Statut :** V2 figée au lancement ; changements uniquement via addendum écrit communiqué à A et B.

## Démarrage rapide

1. Conserver ce dossier comme **source unique** et noter son SHA-256 (archive ou commit).
2. Créer deux dépôts privés **séparés** à partir du même commit initial (A et B), contenant ces documents et les modèles GitHub. Ne pas fournir l'évaluation privée ni le dépôt de l'autre équipe.
3. Configurer dans chaque dépôt les mêmes permissions, règles de protection de `main`, secrets de développement *fictifs* et environnements d'outils. Les agents doivent créer les scripts CI réels dans leur code.
4. Donner **strictement** `07_PROMPT_COMMUN.md` aux deux équipes ; ne changer que l'identifiant neutre A/B et les paramètres du fournisseur consigné.
5. Lancer le chronomètre de chaque équipe à l'accès effectif au dépôt, au même plafond de 48 h. Les interruptions humaines et pannes sont enregistrées.
6. Suivre librement l'avancement sans donner de notes. Les demandes de changement passent par `08_JOURNAL_INTERVENTIONS.md`, et la même instruction est reçue par A et B.
7. Clore chaque équipe sur un **commit/tag immuable** ; sauvegarder le diff Git, les PR, le journal d'actions et les coûts. Tester ensuite avec `09_REVUE_FINALE.md` et le plan indépendant.

## Fichiers

- `01_SPECIFICATIONS_ET_ARCHITECTURE.md` : exigences et contrats API normatifs.
- `02_PLAN_DE_TEST_ET_SECURITE.md` : critères publics et matrice d'audit.
- `03_ROLES_ET_HANDOFFS.md` : cinq rôles, responsabilités et livrables.
- `04_GIT_ISSUES_PR_CI.md` : GitHub, branches, PR et qualité des changements.
- `05_SKILLS_ET_AMELIORATION.md` : apprentissage procédural et candidats skills.
- `06_PROTOCOLE_48H.md` : conditions de comparaison, observations, métriques.
- `07_PROMPT_COMMUN.md` : unique prompt de lancement pour A et B.
- `08_JOURNAL_INTERVENTIONS.md` : modèle d'amendements et remontées.
- `09_REVUE_FINALE.md` : grille d'analyse sans notes prédéfinies.
- `10_UX_CREATIVITE.md` : inspirations et liberté visuelle.
- `.github/` : modèles d'issues et de PR identiques.

## Sécurité et périmètre

Uniquement des comptes et données de démonstration **fictifs**. Pas de scans offensifs réels ni de déploiement public sans validation. Ne pas donner aux agents les secrets personnels, tokens de production ni droits d'administrateur GitHub. Ce dossier est un **benchmark d'ingénierie**, pas un produit certifié.

## Lancement de l'application (Docker Compose de dev — issue #16)

### Prérequis

- Docker (daemon actif) et le plugin `docker compose` (v2 ou supérieur).
- Aucune autre dépendance hôte : Postgres 16, Mailpit, backend et frontend sont servis par des conteneurs.

### Démarrage

```bash
# Optionnel : .env local (jamais commité) pour surcharger ports / mots de passe dev.
cp .env.example .env
docker compose up --build
```

Premier démarrage : les migrations Alembic s'exécutent dans le conteneur `backend` (entrypoint `./entrypoint.sh`) avant le lancement de l'API. La persistance des données et des preuves est assurée par les volumes nommés `dbdata` et `evidencedata`.

### URLs (ports standards)

| Service | URL |
|---|---|
| UI (nginx, SPA) | http://localhost:8080 |
| API (health) | http://localhost:8000/api/v1/health |
| Mailpit (UI ; SMTP sur le port 1025) | http://localhost:8025 |

nginx reverse-proxy `/api/` vers le service `backend:8000` (`frontend/nginx.conf`) : `http://localhost:8080/api/v1/health` doit répondre 200, comme l'API directe.

### Mode décalé (cohabitation avec des conteneurs `cs-*` locaux)

Si des conteneurs de dev (ex. `cs-pg-dev` sur 5432, `cs-mailpit-dev` sur 8025/1025) tournent déjà sur la machine, créez un `.env` local **non commité** avec les ports hôtes décalés, puis relancez :

```bash
POSTGRES_PORT=15432
MAILPIT_UI_PORT=18025
MAILPIT_SMTP_PORT=11025
```

`BACKEND_PORT` (8000) et `FRONTEND_PORT` (8080) restent aux valeurs standards sauf conflit ; si `FRONTEND_PORT` change, `PUBLIC_BASE_URL` doit le suivre (liens des e-mails, D-12). Les variables et défauts sont documentés dans `.env.example`.

### Dev sans Docker (Postgres local `cs-pg-dev`)

```bash
# Backend (terminal 1)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL="postgresql+psycopg2://chainscope:<mot-de-passe>@127.0.0.1:5432/chainscope"
python -m alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2) — vite proxye /api vers 127.0.0.1:8000 (vite.config.ts)
cd frontend
npm ci
npm run dev   # http://localhost:5173
```

### Bootstrap administrateur plateforme (D-14)

```bash
python -m app.cli create-platform-admin --email <email> --password <password>
```

Commande prévue par `docs/DECISIONS.md` (D-14), livrée avec l'authentification (issue #5) ; à exécuter depuis le répertoire `backend/` avec un venv ou dans le conteneur `backend`. Alternative sans CLI : variables `PLATFORM_ADMIN_EMAIL` / `PLATFORM_ADMIN_PASSWORD` au premier démarrage, si aucune ligne `platform_admins` n'existe.

### Seed (données fictives de démonstration)

À venir — issue #15 (`python -m app.cli seed`, idempotent).

### Arrêter / laver les données

```bash
docker compose down        # arrête les conteneurs ; les volumes (dbdata, evidencedata) sont conservés
docker compose down -v     # ⚠️ DESTRUCTIF : supprime aussi les volumes (base de données + preuves)
```
