import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { api, ApiError } from '../lib/api'
import type { AuthMe } from '../lib/types'
import { HomePage } from './HomePage'

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return {
    ...actual,
    api: { getMe: vi.fn() },
  }
})

function AppProbe() {
  const location = useLocation()
  const state = location.state as { defaultTenant?: { tenant_name: string; slug: string } } | null
  return <div data-testid="app">{`app:${state?.defaultTenant?.tenant_name ?? 'sans-tenant'}`}</div>
}

function renderAtHome(me: AuthMe | ApiError) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  vi.mocked(api.getMe).mockImplementation(async () => {
    if (me instanceof ApiError) throw me
    return me
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/platform/tenants" element={<div data-testid="platform">Plateforme</div>} />
          <Route path="/app" element={<AppProbe />} />
          <Route path="/client" element={<div data-testid="client">Portail client</div>} />
          <Route path="/login" element={<div data-testid="login">Login</div>} />
          <Route path="/no-access" element={<div data-testid="no-access">Accès refusé</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const PLATFORM_ADMIN: AuthMe = {
  id: 'u-0001',
  email: 'root@chainscope.fr',
  is_active: true,
  platform_admin: true,
  tenant_memberships: [],
  client_memberships: [],
}

const TENANT_USER: AuthMe = {
  id: 'u-0002',
  email: 'admin@aegis-red-team.fr',
  is_active: true,
  platform_admin: false,
  tenant_memberships: [
    { tenant_id: 't-0001', tenant_name: 'Aegis Red Team', slug: 'aegis-red-team', role: 'TENANT_ADMIN' },
    { tenant_id: 't-0002', tenant_name: 'Boreal Security', slug: 'boreal-security', role: 'PENTESTER' },
  ],
  client_memberships: [],
}

const CLIENT_USER: AuthMe = {
  id: 'u-0003',
  email: 'contact@acme-sante.fr',
  is_active: true,
  platform_admin: false,
  tenant_memberships: [],
  client_memberships: [
    { client_org_id: 'c-0001', client_org_name: 'Acme Santé', tenant_id: 't-0001', role: 'CLIENT_VIEWER' },
  ],
}

describe('HomePage (redirection selon /auth/me)', () => {
  it('redirige un platform_admin vers /platform/tenants', async () => {
    renderAtHome(PLATFORM_ADMIN)
    expect(await screen.findByTestId('platform')).toBeInTheDocument()
    expect(vi.mocked(api.getMe)).toHaveBeenCalledTimes(1)
  })

  it('redirige un membre de cabinet vers /app avec le tenant par défaut (signal)', async () => {
    renderAtHome(TENANT_USER)
    const probe = await screen.findByTestId('app')
    expect(probe).toHaveTextContent('app:Aegis Red Team')
  })

  it('redirige un client (sans membership cabinet) vers /client', async () => {
    renderAtHome(CLIENT_USER)
    expect(await screen.findByTestId('client')).toBeInTheDocument()
  })

  it('redirige vers /login quand /auth/me renvoie 401', async () => {
    renderAtHome(new ApiError(401, 'UNAUTHORIZED', 'Non authentifié.', null))
    expect(await screen.findByTestId('login')).toBeInTheDocument()
  })

  it('renvoie vers la page 403 quand le compte n’appartient à aucun espace', async () => {
    const ORPHAN: AuthMe = { ...CLIENT_USER, id: 'u-0004', client_memberships: [] }
    renderAtHome(ORPHAN)
    expect(await screen.findByTestId('no-access')).toBeInTheDocument()
  })
})
