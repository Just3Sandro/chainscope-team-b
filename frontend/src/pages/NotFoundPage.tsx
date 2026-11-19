import { Link } from 'react-router'
import { buttonClass } from '../components/fields'
import { Wordmark } from '../components/layout/Wordmark'

/**
 * 404 (DESIGN §3.6) : « Cette ressource n'existe pas ou vous n'y avez pas accès. »
 * — identique que l'ID soit faux ou hors périmètre (pas de fuite d'existence).
 */
export function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-[400px] rounded-md border border-border bg-surface p-6 text-center shadow-sm">
        <Wordmark size={48} withText={false} muted className="mx-auto mb-4 block" />
        <h1 className="text-xl font-semibold">Page introuvable</h1>
        <p className="mt-2 text-sm text-ink-soft">Cette ressource n’existe pas ou vous n’y avez pas accès.</p>
        <Link to="/" className={`${buttonClass('ghost', '')} mt-5`}>
          Retour à l’accueil
        </Link>
      </div>
    </div>
  )
}
