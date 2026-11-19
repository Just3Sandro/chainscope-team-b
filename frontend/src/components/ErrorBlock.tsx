import { ApiError } from '../lib/api'
import { Button } from './fields'

/**
 * Bloc d'erreur inline (DESIGN §3.6, §4.1) : message factuel, `request_id`
 * en mono (≥ 12 px, jamais en ink-faint < 12 px) et bouton « Réessayer ».
 */
export function ErrorBlock({
  error,
  title = 'Une erreur est survenue.',
  onRetry,
}: {
  error: Error
  title?: string
  onRetry?: () => void
}) {
  const apiError = error instanceof ApiError ? error : null
  return (
    <div role="alert" className="rounded-sm border border-danger/30 bg-danger-soft p-4">
      <div className="flex items-start gap-3">
        <svg
          className="mt-0.5 h-4 w-4 shrink-0 text-danger"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-ink">{title}</p>
          <p className="mt-1 text-sm text-ink-soft">{error.message}</p>
          {apiError !== null && apiError.status > 0 && (
            <p className="mt-1 text-xs text-ink-soft">HTTP {apiError.status}</p>
          )}
          {apiError !== null && apiError.requestId !== null && (
            <p className="mt-1 font-mono text-xs text-ink-faint">request_id : {apiError.requestId}</p>
          )}
          {onRetry !== undefined && (
            <Button variant="ghost" onClick={onRetry} className="mt-3 h-8 px-3 text-xs">
              Réessayer
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
