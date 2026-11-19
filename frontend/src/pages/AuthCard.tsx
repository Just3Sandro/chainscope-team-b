import type { ReactNode } from 'react'
import { Wordmark } from '../components/layout/Wordmark'

/**
 * Carte d'authentification centrée 400 px sur fond `canvas` (DESIGN P1) :
 * écusson 32 px, logotype, titre 20/600.
 */
export function AuthCard({ title, children, footer }: { title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-[400px]">
        <div className="rounded-md border border-border bg-surface p-6 shadow-sm">
          <div className="mb-5 flex flex-col items-center gap-3">
            <Wordmark size={32} withText={false} />
            <Wordmark size={24} />
            <h1 className="text-xl font-semibold leading-tight">{title}</h1>
          </div>
          {children}
        </div>
        {footer !== undefined && (
          <div className="mt-4 text-center text-xs text-ink-soft">{footer}</div>
        )}
      </div>
    </div>
  )
}
