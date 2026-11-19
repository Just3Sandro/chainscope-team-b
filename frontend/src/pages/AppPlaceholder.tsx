import { useLocation } from 'react-router'
import { useRequireAuth, SessionLoading } from '../components/layout/guards'
import { AppShell } from '../components/layout/AppShell'
import { Wordmark } from '../components/layout/Wordmark'
import type { TenantMembership } from '../lib/types'

/**
 * Écran « à venir » honnête de l'espace cabinet (DESIGN P2–P4, P9).
 * Sans données métier mockées : seul le tenant par défaut, transmis par la
 * page d'accueil (state de navigation), est signalé.
 */
export function AppPlaceholder() {
  const { user, status } = useRequireAuth()
  const location = useLocation()
  if (status === 'loading' || user === null) return <SessionLoading />

  const state = location.state as { defaultTenant?: TenantMembership } | null
  const defaultTenant = state?.defaultTenant
  const extraSpaces = user.tenant_memberships.length - 1

  return (
    <AppShell mode="cabinet" user={user}>
      <section className="rounded-md border border-border bg-surface p-6 shadow-xs">
        <Wordmark size={48} withText={false} muted className="mb-4" />
        <h1 className="text-xl font-semibold">Espace cabinet</h1>
        <p className="mt-2 text-sm text-ink-soft">
          Ce module (tableau de bord, missions, clients, constats et journal d’audit) arrive avec le Jalon 2.
        </p>
        {defaultTenant !== undefined && (
          <div className="mt-4 rounded-sm border border-border bg-surface-muted p-3 text-xs text-ink-soft">
            <p>
              Tenant sélectionné par défaut :{' '}
              <span className="font-medium text-ink">{defaultTenant.tenant_name}</span>{' '}
              <span className="font-mono text-ink-faint">({defaultTenant.slug})</span>
            </p>
            {extraSpaces > 0 && (
              <p className="mt-1">
                Votre compte appartient à {user.tenant_memberships.length} espaces ; le choix d’espace
                (/workspace) arrive avec le Jalon 2.
              </p>
            )}
          </div>
        )}
      </section>
    </AppShell>
  )
}
