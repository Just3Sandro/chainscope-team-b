import type { ReactNode } from 'react'
import type { AuthMe } from '../../lib/types'
import { Topbar, type AppMode } from './Topbar'

/**
 * Shell commun aux apps (DESIGN §3) : skip-link « Aller au contenu principal »
 * (premier focusable, §7.3), topbar 56 px et gouttière contenu 24 px (px-6, §2.3).
 */
export function AppShell({ mode, user, children }: { mode: AppMode; user: AuthMe | null; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas">
      <a
        href="#contenu-principal"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-sm focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-ink focus:shadow-md"
      >
        Aller au contenu principal
      </a>
      <Topbar mode={mode} user={user} />
      <main id="contenu-principal" tabIndex={-1} className="mx-auto w-full max-w-5xl px-6 py-6 outline-none">
        {children}
      </main>
    </div>
  )
}
