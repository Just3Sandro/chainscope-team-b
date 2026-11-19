import { Route, Routes } from 'react-router'
import { RoleGate } from './components/layout/guards'
import { AcceptInvitationPage } from './pages/AcceptInvitationPage'
import { AppPlaceholder } from './pages/AppPlaceholder'
import { ClientPortalPlaceholder } from './pages/ClientPortalPlaceholder'
import { ForgotPasswordPage } from './pages/ForgotPasswordPage'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { NoAccessPage } from './pages/NoAccessPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PlatformTenantsPlaceholder } from './pages/PlatformTenantsPlaceholder'
import { ResetPasswordPage } from './pages/ResetPasswordPage'

/**
 * Routes du socle (issue #18).
 * - Le serveur reste le seul à autoriser (spec §8) : RoleGate masque l'UI,
 *   les 403 API restent gérés page par page ensuite.
 * - URL directe vers une route d'un autre rôle ⇒ 403 (DESIGN §3.5-3).
 */
export default function App() {
  return (
    <Routes>
      <Route index element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot" element={<ForgotPasswordPage />} />
      <Route path="/reset" element={<ResetPasswordPage />} />
      <Route path="/invite" element={<AcceptInvitationPage />} />
      <Route
        path="/platform/tenants"
        element={
          <RoleGate requirement="platform">
            <PlatformTenantsPlaceholder />
          </RoleGate>
        }
      />
      <Route
        path="/app"
        element={
          <RoleGate requirement="tenant">
            <AppPlaceholder />
          </RoleGate>
        }
      />
      <Route
        path="/client"
        element={
          <RoleGate requirement="client">
            <ClientPortalPlaceholder />
          </RoleGate>
        }
      />
      <Route path="/no-access" element={<NoAccessPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
