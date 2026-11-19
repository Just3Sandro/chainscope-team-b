import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router'
import type { ReactNode } from 'react'
import { api, ApiError } from '../../lib/api'
import type { AuthMe } from '../../lib/types'
import { NoAccessPage } from '../../pages/NoAccessPage'
import { ErrorBlock } from '../ErrorBlock'
import { Spinner } from '../fields'

/**
 * Gardes de route (DESIGN §3.5).
 *
 * `useRequireAuth` : charge `/auth/me` (cache TanStack, retry off — le 401 est
 * géré par le client API : événement + redirection /login).
 *
 * ⚠️ Le frontend masque seulement ce qu'il ne doit pas afficher : le serveur
 * reste le seul à autoriser (spec §8).
 */

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'error'

export interface RequireAuthState {
  user: AuthMe | null
  status: AuthStatus
  error: Error | null
  refetch: () => Promise<unknown>
}

export function useRequireAuth(): RequireAuthState {
  const { data, isPending, isError, error, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => api.getMe(),
    // Le 401 est traité par api.ts (événement + redirection) ; pas de retry automatique.
    retry: false,
  })
  if (isPending) return { user: null, status: 'loading', error: null, refetch }
  if (isError) {
    if (error instanceof ApiError && error.status === 401) {
      return { user: null, status: 'unauthenticated', error, refetch }
    }
    const normalized: Error =
      error instanceof Error ? error : new Error('Erreur inattendue du chargement de session.')
    return { user: null, status: 'error', error: normalized, refetch }
  }
  return { user: data, status: 'authenticated', error: null, refetch }
}

/** Garde générique « connecté » : me → 401 ⇒ /login. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, status, error, refetch } = useRequireAuth()
  if (status === 'loading') return <SessionLoading />
  if (status === 'unauthenticated') return <Navigate to="/login" replace />
  if (status === 'error') {
    return (
      <div className="mx-auto max-w-xl px-6 py-12">
        <ErrorBlock error={error as Error} onRetry={() => void refetch()} title="Impossible de charger votre session." />
      </div>
    )
  }
  if (user === null) return <Navigate to="/login" replace />
  return <>{children}</>
}

/** Écran de chargement de session (aria-busy, DESIGN §4.1). */
export function SessionLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas" aria-busy="true">
      <div className="flex flex-col items-center gap-3 text-sm text-ink-soft">
        <Spinner className="h-6 w-6 text-accent" />
        <p>Chargement de la session…</p>
      </div>
    </div>
  )
}

/** Plateforme ⇄ cabinet ⇄ client : URL directe vers une route d'un autre rôle ⇒ 403 (DESIGN §3.5-3). */
export type RoleRequirement = 'platform' | 'tenant' | 'client'

export function isAllowed(user: AuthMe, requirement: RoleRequirement): boolean {
  switch (requirement) {
    case 'platform':
      return user.platform_admin
    case 'tenant':
      return user.tenant_memberships.length > 0
    case 'client':
      return user.client_memberships.length > 0
  }
}

export function RoleGate({ requirement, children }: { requirement: RoleRequirement; children: ReactNode }) {
  const { user, status, error, refetch } = useRequireAuth()
  if (status === 'loading') return <SessionLoading />
  if (status === 'unauthenticated') return <Navigate to="/login" replace />
  if (status === 'error') {
    return (
      <div className="mx-auto max-w-xl px-6 py-12">
        <ErrorBlock error={error as Error} onRetry={() => void refetch()} title="Impossible de charger votre session." />
      </div>
    )
  }
  if (user === null || !isAllowed(user, requirement)) return <NoAccessPage />
  return <>{children}</>
}
