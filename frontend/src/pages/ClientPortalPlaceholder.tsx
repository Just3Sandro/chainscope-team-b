import { useRequireAuth, SessionLoading } from '../components/layout/guards'
import { AppShell } from '../components/layout/AppShell'
import { Wordmark } from '../components/layout/Wordmark'

/** Écran « à venir » honnête du portail client (DESIGN P7). */
export function ClientPortalPlaceholder() {
  const { user, status } = useRequireAuth()
  if (status === 'loading' || user === null) return <SessionLoading />

  return (
    <AppShell mode="client" user={user}>
      <section className="rounded-md border border-border bg-surface p-6 shadow-xs">
        <Wordmark size={48} withText={false} muted className="mb-4" />
        <h1 className="text-xl font-semibold">Portail client</h1>
        <p className="mt-2 text-sm text-ink-soft">
          Ce module (missions et constats publiés, lecture seule) arrive avec le Jalon 4.
        </p>
      </section>
    </AppShell>
  )
}
