import { Link } from 'react-router'
import { buttonClass } from '../components/fields'
import { Wordmark } from '../components/layout/Wordmark'

/**
 * 403 générique (DESIGN §3.6) : titre « Accès refusé », message factuel,
 * `request_id` en mono si présent. Le contenu interdit n'est jamais rendu.
 */
export function NoAccessPage({ requestId = null }: { requestId?: string | null }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-[400px] rounded-md border border-border bg-surface p-6 text-center shadow-sm">
        <Wordmark size={48} withText={false} muted className="mx-auto mb-4 block" />
        <h1 className="text-xl font-semibold">Accès refusé</h1>
        <p className="mt-2 text-sm text-ink-soft">Vous n’avez pas accès à cette ressource.</p>
        {requestId !== null && requestId.length > 0 && (
          <p className="mt-2 font-mono text-xs text-ink-faint">request_id : {requestId}</p>
        )}
        <Link to="/" className={`${buttonClass('ghost', '')} mt-5`}>
          Retour à l’accueil
        </Link>
      </div>
    </div>
  )
}
