import { useEffect } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { useRequireAuth, SessionLoading } from '../components/layout/guards'
import { ErrorBlock } from '../components/ErrorBlock'

/**
 * Page d'accueil (route `/`) : après le succès de `GET /auth/me`, redirection
 * par rôle (DESIGN §3.1) :
 *  - `platform_admin`        → `/platform/tenants`
 *  - sinon tenant_memberships[0] → `/app` (tenant par défaut, signalé à la page cible)
 *  - sinon client_memberships    → `/client`
 *  - 401 → `/login` (le client API émet déjà l'événement + la redirection).
 */
export function HomePage() {
  const { user, status, error, refetch } = useRequireAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (status !== 'authenticated' || user === null) return
    if (user.platform_admin) {
      navigate('/platform/tenants', { replace: true })
      return
    }
    const firstTenant = user.tenant_memberships[0]
    if (firstTenant !== undefined) {
      // Choix de tenant par défaut + signal (state) : le choix d'espace
      // (/workspace) arrivera avec le Jalon 2.
      navigate('/app', { replace: true, state: { defaultTenant: firstTenant } })
      return
    }
    if (user.client_memberships.length > 0) {
      navigate('/client', { replace: true })
      return
    }
    navigate('/no-access', { replace: true })
  }, [status, user, navigate])

  if (status === 'authenticated' || status === 'loading') {
    // Redirection en cours : on reste sur l'écran de chargement de session.
    return <SessionLoading />
  }
  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />
  }
  return (
    <div className="mx-auto max-w-xl px-6 py-12">
      <ErrorBlock
        error={error ?? new Error('Erreur inattendue du chargement de session.')}
        title="Impossible de charger votre session."
        onRetry={() => void refetch()}
      />
    </div>
  )
}
