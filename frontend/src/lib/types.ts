/**
 * Types du contrat d'authentification (spec §6, DECISIONS D-04/D-05).
 *
 * - `GET /auth/me` : figé par **D-17** (mergée).
 * - Autres routes auth (`/auth/csrf`, `/auth/login`, `/auth/reset-password`…) :
 *   contrat figé par le registre de décisions **D-19** (PR backend #32, issue #5,
 *   non mergée mais validée) — aligné dans cette issue #33.
 */

/** Rôles du cabinet, stockés dans `tenant_memberships` (spec §1). */
export type TenantRole = 'TENANT_ADMIN' | 'PENTESTER'

/** Rôle du portail client, stocké dans `client_memberships` (spec §1). */
export type ClientRole = 'CLIENT_VIEWER'

export interface TenantMembership {
  tenant_id: string
  tenant_name: string
  slug: string
  role: TenantRole
}

export interface ClientMembership {
  client_org_id: string
  client_org_name: string
  tenant_id: string
  role?: ClientRole
}

/** Contrat `GET /auth/me` (figé par D-17). */
export interface AuthMe {
  id: string
  email: string
  is_active: boolean
  platform_admin: boolean
  tenant_memberships: TenantMembership[]
  client_memberships: ClientMembership[]
}

/**
 * Réponse de `GET /auth/csrf` (contrat auth, D-19 / PR #32).
 * Le token est opaque par session ; seul son hash est stocké côté serveur.
 */
export interface CsrfResponse {
  csrf_token: string
}
