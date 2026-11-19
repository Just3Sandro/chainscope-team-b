# Frontend ChainScope (issue #18)

Socle de l'application web : **Vite + React 19 + TypeScript strict + Tailwind CSS v4 (tokens DESIGN.md §2.2) + React Router v7 + TanStack Query v5**. Polices Inter / JetBrains Mono embarquées (`@fontsource-variable`, aucun lien Google Fonts : l'app fonctionne hors réseau après build).

Aucune donnée mockée : l'interface ne consomme que le backend (contrat `spec §6`, erreurs normalisées `{ error: { code, message, request_id } }`).

## Périmètre de ce socle

- Client API (`src/lib/api.ts`) : `credentials: same-origin`, CSRF par session via `GET /auth/csrf` + header `X-CSRF-Token` sur toutes les mutations (DECISIONS D-05), `ApiError` depuis l'enveloppe normalisée, événement `chainscope:session-expired` + redirection `/login` sur 401.
- Types provisoires du contrat `/auth/me` (`src/lib/types.ts`) — **à figer avec la PR backend d'authentification (#5)**.
- Pages auth (`/login`, `/forgot`, `/reset`, `/invite`), redirection par rôle depuis `/` (platform_admin → `/platform/tenants`, cabinet → `/app` avec tenant par défaut signalé, client → `/client`), gardes de route (`useRequireAuth`, `RoleGate`), écrans « à venir » honnêtes (Jalon 2 / Jalon 4), 404 et 403 dédiés.
- Déconnexion : `POST /auth/logout` (CSRF) puis rechargement sur `/login`.

## Commandes

```bash
npm install
npm run dev         # http://localhost:5173 (proxy /api → http://127.0.0.1:8000)
npm run typecheck   # tsc -b (strict)
npm run test        # vitest run
npm run build       # tsc -b && vite build → dist/
npm run preview     # sert le build
```

## Docker

`Dockerfile` multi-stage `node:22-alpine` (build) → `nginx:alpine` (service, port 80) ; `nginx.conf` : SPA fallback + `location /api/` vers le service `backend` (compose racine, à l'issue de l'infra #16).

## À suivre (issues de suivi, pas de dette cachée)

- Le choix d'espace `/workspace` (DESIGN §3.1) n'appartient pas à ce socle : avec plusieurs memberships, le premier tenant est choisi par défaut et signalé sur `/app`.
- `GET /auth/csrf` est supposé répondre `{ csrf_token: string }` — à confirmer avec la PR #5.
- Le contrat `POST /auth/login` renvoie l'utilisateur connecté (formé comme `/auth/me`) — à confirmer avec la PR #5.
