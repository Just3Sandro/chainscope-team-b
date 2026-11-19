import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { api, ApiError } from '../lib/api'
import type { AuthMe } from '../lib/types'
import { LoginPage } from './LoginPage'

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return {
    ...actual,
    api: { login: vi.fn() },
  }
})

const ME: AuthMe = {
  id: 'u-0001',
  email: 'admin@aegis-red-team.fr',
  is_active: true,
  platform_admin: false,
  tenant_memberships: [
    { tenant_id: 't-0001', tenant_name: 'Aegis Red Team', slug: 'aegis-red-team', role: 'TENANT_ADMIN' },
  ],
  client_memberships: [],
}

function renderAtLogin(initialEntry = '/login') {
  const user = userEvent.setup()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forgot" element={<div data-testid="forgot">Mot de passe oublié</div>} />
          <Route path="/" element={<div data-testid="home">Accueil</div>} />
          <Route path="/app" element={<div data-testid="app">Espace cabinet</div>} />
          <Route path="/platform/tenants" element={<div data-testid="platform">Plateforme</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { user, ...utils }
}

function submitLogin(user: ReturnType<typeof userEvent.setup>) {
  return user.click(screen.getByRole('button', { name: 'Se connecter' }))
}

// Les labels incluent l'astérisque de champ requis (« Adresse e-mail* ») :
// les correspondances utilisent donc un préfixe regex, pas de chaîne exacte.
const EMAIL_LABEL = /^Adresse e-mail/
const PASSWORD_LABEL = /^Mot de passe/

describe('LoginPage', () => {
  it('ne soumet pas un formulaire vide et affiche les erreurs de champ', async () => {
    const { user } = renderAtLogin()
    await submitLogin(user)
    expect(await screen.findByText(/L’adresse e-mail est requise/)).toBeInTheDocument()
    expect(screen.getByText(/Le mot de passe est requis/)).toBeInTheDocument()
    expect(vi.mocked(api.login)).not.toHaveBeenCalled()
  })

  it('refuse une adresse e-mail mal formée', async () => {
    const { user } = renderAtLogin()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'sandro-sans-at')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByText(/Adresse e-mail invalide/)).toBeInTheDocument()
    expect(vi.mocked(api.login)).not.toHaveBeenCalled()
  })

  it('soumet les identifiants (jeton CSRF géré par le client API) et navigue vers l’accueil', async () => {
    vi.mocked(api.login).mockResolvedValue(ME)
    const { user } = renderAtLogin()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByTestId('home')).toBeInTheDocument()
    expect(vi.mocked(api.login)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.login)).toHaveBeenCalledWith('admin@aegis-red-team.fr', 'SuperPasse123')
  })

  it('affiche l’erreur générique non révélatrice en cas d’échec 401', async () => {
    vi.mocked(api.login).mockRejectedValue(
      new ApiError(401, 'UNAUTHORIZED', 'E-mail ou mot de passe incorrect.', null),
    )
    const { user } = renderAtLogin()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByText('E-mail ou mot de passe incorrect.')).toBeInTheDocument()
    // Jamais de révélation d'existence de compte : pas de request_id affiché.
    expect(screen.queryByText(/request_id/)).not.toBeInTheDocument()
  })

  it('affiche le message de limitation sur 429', async () => {
    vi.mocked(api.login).mockRejectedValue(
      new ApiError(429, 'RATE_LIMITED', 'Trop de requêtes.', null),
    )
    const { user } = renderAtLogin()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByText('Trop de requêtes. Réessayez dans un instant.')).toBeInTheDocument()
  })

  it('marque le bouton en aria-busy pendant la soumission', async () => {
    vi.mocked(api.login).mockImplementation(() => new Promise<AuthMe>(() => {}))
    const { user } = renderAtLogin()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    const button = await screen.findByRole('button', { name: /Se connecter/ })
    expect(button).toHaveAttribute('aria-busy', 'true')
    expect(button).toBeDisabled()
  })

  it('affiche le bandeau « Session expirée » et revient sur next=/app après reconnexion', async () => {
    vi.mocked(api.login).mockResolvedValue(ME)
    const { user } = renderAtLogin('/login?reason=expired&next=%2Fapp')
    expect(await screen.findByText('Session expirée. Reconnectez-vous pour continuer.')).toBeInTheDocument()
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByTestId('app')).toBeInTheDocument()
  })

  it('n’ignore pas next=/platform/tenants (interdit DESIGN P1) : retourne à l’accueil', async () => {
    vi.mocked(api.login).mockResolvedValue(ME)
    const { user } = renderAtLogin('/login?next=%2Fplatform%2Ftenants')
    await user.type(screen.getByLabelText(EMAIL_LABEL), 'admin@aegis-red-team.fr')
    await user.type(screen.getByLabelText(PASSWORD_LABEL), 'SuperPasse123')
    await submitLogin(user)
    expect(await screen.findByTestId('home')).toBeInTheDocument()
    expect(screen.queryByTestId('platform')).not.toBeInTheDocument()
  })
})
