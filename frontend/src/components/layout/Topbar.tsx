import { useState } from 'react'
import { api, ApiError } from '../../lib/api'
import type { AuthMe } from '../../lib/types'
import { Button } from '../fields'
import { Wordmark } from './Wordmark'

/**
 * Topbar 56 px (DESIGN §2.3) : écusson + logotype, chip de mode,
 * e-mail de session et « Se déconnecter » (POST /auth/logout avec CSRF,
 * DECISIONS D-04/D-05) puis rechargement sur /login.
 */
export type AppMode = 'platform' | 'cabinet' | 'client'

const MODE_LABELS: Record<AppMode, string> = {
  platform: 'Plateforme',
  cabinet: 'Cabinet',
  client: 'Portail client',
}

function modeChipClass(mode: AppMode): string {
  // Le chip « Portail client » est permanent et distingue nettement le mode lecture seule (DESIGN §3.3).
  if (mode === 'client') {
    return 'rounded-pill bg-mi-active-soft px-2.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-mi-active-ink'
  }
  return 'rounded-pill bg-surface-muted px-2.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-ink-soft'
}

export function Topbar({ mode, user }: { mode: AppMode; user: AuthMe | null }) {
  const [loggingOut, setLoggingOut] = useState(false)
  const [logoutError, setLogoutError] = useState<ApiError | null>(null)

  async function handleLogout(): Promise<void> {
    if (loggingOut) return
    setLoggingOut(true)
    setLogoutError(null)
    try {
      await api.logout()
      // Rechargement complet sur /login : la session est révoquée côté serveur.
      window.location.assign('/login')
    } catch (error) {
      setLogoutError(error instanceof ApiError ? error : new ApiError(0, 'NETWORK', "La déconnexion a échoué.", null))
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <header className="min-h-14 border-b border-border bg-surface">
      <div className="mx-auto flex min-h-14 w-full max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-1 px-6 py-1.5">
        <div className="flex min-w-0 items-center gap-3">
          <Wordmark size={24} />
          <span className={modeChipClass(mode)}>{MODE_LABELS[mode]}</span>
        </div>
        <div className="flex items-center gap-3">
          {user !== null && (
            <span className="hidden truncate text-xs text-ink-soft sm:inline">{user.email}</span>
          )}
          <Button variant="ghost" loading={loggingOut} onClick={() => void handleLogout()} className="h-8 px-3 text-xs">
            Se déconnecter
          </Button>
        </div>
      </div>
      {logoutError !== null && (
        <p className="border-t border-danger/30 bg-danger-soft px-6 py-1.5 text-xs text-danger">
          {logoutError.message}
          {logoutError.requestId !== null && (
            <span className="ml-2 font-mono text-ink-faint">request_id : {logoutError.requestId}</span>
          )}
        </p>
      )}
    </header>
  )
}
