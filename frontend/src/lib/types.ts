/**
 * Types provisoires du contrat d'authentification (spec §6, DECISIONS D-04/D-05).
 *
 * ⚠️ Contrat PROVISOIRE : figé par la PR backend d'authentification (#5).
 * Toute divergence côté backend doit être signalée dans la revue de cette PR
 * et alignée ici avant le Jalon 2 (vertical slice).
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

/** Contrat `GET /auth/me` (provisoire, cf. PR #5). */
export interface AuthMe {
  id: string
  email: string
  is_active: boolean
  platform_admin: boolean
  tenant_memberships: TenantMembership[]
  client_memberships: ClientMembership[]
}

/**
 * Réponse de `GET /auth/csrf` (provisoire, cf. DECISIONS D-05).
 * Le token est opaque par session ; seul son hash est stocké côté serveur.
 */
export interface CsrfResponse {
  csrf_token: string
}
