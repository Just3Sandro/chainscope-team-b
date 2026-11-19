import { useRequireAuth, SessionLoading } from '../components/layout/guards'
import { AppShell } from '../components/layout/AppShell'
import { Wordmark } from '../components/layout/Wordmark'

/** Écran « à venir » honnête de l'administration plateforme (DESIGN P8). */
export function PlatformTenantsPlaceholder() {
  const { user, status } = useRequireAuth()
  if (status === 'loading' || user === null) return <SessionLoading />

  return (
    <AppShell mode="platform" user={user}>
      <section className="rounded-md border border-border bg-surface p-6 shadow-xs">
        <Wordmark size={48} withText={false} muted className="mb-4" />
        <h1 className="text-xl font-semibold">Administration plateforme — Tenants</h1>
        <p className="mt-2 text-sm text-ink-soft">Ce module arrive avec le Jalon 4.</p>
      </section>
    </AppShell>
  )
}
