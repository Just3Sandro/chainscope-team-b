import { describe, expect, it, vi } from 'vitest'
import {
  API_BASE_URL,
  ApiClient,
  ApiError,
  SESSION_EXPIRED_EVENT,
  buildSessionExpiredUrl,
  type SessionExpiredInfo,
} from './api'
import type { AuthMe } from './types'

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

/** Réponse HTTP factice (jsdom ne fournit pas `fetch`/`Response`). */
function json(status: number, body?: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => (body === undefined ? '' : JSON.stringify(body)),
  } as unknown as Response
}

type Handler = (url: string, init?: RequestInit) => Response
function mockFetch(handler: Handler) {
  return vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url
    return handler(url, init)
  }) as unknown as typeof fetch
}

function headersOf(init?: RequestInit): Headers {
  return new Headers(init?.headers)
}

describe('lib/api.ts', () => {
  it('GET : aucun appel CSRF, credentials same-origin, réponse JSON parsée', async () => {
    const fetchMock = mockFetch((url, init) => {
      expect(url).toBe(`${API_BASE_URL}/auth/me`)
      expect(init?.credentials).toBe('same-origin')
      return json(200, ME)
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    await expect(client.getMe()).resolves.toEqual(ME)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('mutations : un seul GET /auth/csrf (cache mémoire) puis X-CSRF-Token sur POST et PATCH', async () => {
    let csrfCalls = 0
    const seen: Array<{ url: string; token: string | null; credentials: string | undefined }> = []
    const fetchMock = mockFetch((url, init) => {
      if (url === `${API_BASE_URL}/auth/csrf`) {
        csrfCalls += 1
        return json(200, { csrf_token: 'tok-csrf-1' })
      }
      seen.push({ url, token: headersOf(init).get('X-CSRF-Token'), credentials: init?.credentials })
      return json(204)
    })
    const client = new ApiClient({ fetchFn: fetchMock })

    await client.login('admin@aegis-red-team.fr', 'mot-de-passe-test')
    await client.logout()

    expect(csrfCalls).toBe(1)
    expect(seen).toHaveLength(2)
    expect(seen[0]?.url).toBe(`${API_BASE_URL}/auth/login`)
    expect(seen[1]?.url).toBe(`${API_BASE_URL}/auth/logout`)
    for (const entry of seen) {
      expect(entry.token).toBe('tok-csrf-1')
      expect(entry.credentials).toBe('same-origin')
    }
  })

  it('parse l’enveloppe d’erreur normalisée en ApiError (code, message, request_id, status)', async () => {
    const fetchMock = mockFetch(() =>
      json(403, {
        error: { code: 'FORBIDDEN', message: 'Vous n’avez pas les droits sur cette ressource.', request_id: 'req-42' },
      }),
    )
    const client = new ApiClient({ fetchFn: fetchMock })
    const error = await client.getMe().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 403,
      code: 'FORBIDDEN',
      message: 'Vous n’avez pas les droits sur cette ressource.',
      requestId: 'req-42',
    })
  })

  it('corps non-JSON (ex. 502 du proxy) : ApiError factuelle, code HTTP_<status>, pas de crash', async () => {
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) return json(200, { csrf_token: 'tok' })
      const response: Response = {
        status: 502,
        ok: false,
        text: async () => 'Bad Gateway',
      } as unknown as Response
      return response
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    const error = await client.login('a@b.c', 'x').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 502, code: 'HTTP_502', requestId: null })
  })

  it('resetPassword : corps { token, password, password_confirmation } (contrat D-19 / PR #32), avec CSRF', async () => {
    let body: unknown = null
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith('/auth/csrf')) return json(200, { csrf_token: 'tok' })
      body = JSON.parse(String(init?.body)) as unknown
      return json(204)
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    await client.resetPassword('tk-123', 'Nouveau123', 'Nouveau123')
    expect(body).toEqual({ token: 'tk-123', password: 'Nouveau123', password_confirmation: 'Nouveau123' })
  })

  it('401 sur un chargement : événement DOM + callback injectable, expired=false, pas de boucle de mutation', async () => {
    const listener = vi.fn()
    window.addEventListener(SESSION_EXPIRED_EVENT, listener as EventListener)
    const onSessionExpired = vi.fn()
    const fetchMock = mockFetch(() =>
      json(401, { error: { code: 'UNAUTHORIZED', message: 'Non authentifié.', request_id: 'req-401' } }),
    )
    const client = new ApiClient({ fetchFn: fetchMock, onSessionExpired })
    const error = await client.getMe().catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 401, code: 'UNAUTHORIZED', requestId: 'req-401' })
    expect(onSessionExpired).toHaveBeenCalledTimes(1)
    expect(onSessionExpired).toHaveBeenCalledWith({ expired: false })
    expect(listener).toHaveBeenCalledTimes(1)
    const firstEvent = listener.mock.calls[0]?.[0]
    expect(firstEvent).toBeInstanceOf(CustomEvent)
    const detail = (firstEvent as CustomEvent<SessionExpiredInfo>).detail
    expect(detail).toEqual({ expired: false })
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener as EventListener)
  })

  it('401 sur une mutation : callback avec expired=true (session expirée en cours d’action)', async () => {
    const onSessionExpired = vi.fn()
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) return json(200, { csrf_token: 'tok' })
      return json(401, { error: { code: 'UNAUTHORIZED', message: 'Session expirée.', request_id: 'r' } })
    })
    const client = new ApiClient({ fetchFn: fetchMock, onSessionExpired })
    await expect(client.login('a@b.c', 'x')).rejects.toBeInstanceOf(ApiError)
    expect(onSessionExpired).toHaveBeenCalledWith({ expired: true })
  })

  it('401 sur /auth/csrf : la mutation n’est pas envoyée, session expirée signalée', async () => {
    const onSessionExpired = vi.fn()
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) {
        return json(401, { error: { code: 'UNAUTHORIZED', message: 'Non authentifié.', request_id: 'r' } })
      }
      throw new Error('la mutation ne doit pas être envoyée')
    })
    const client = new ApiClient({ fetchFn: fetchMock, onSessionExpired })
    const error = await client.login('a@b.c', 'x').catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 401 })
    expect(onSessionExpired).toHaveBeenCalledTimes(1)
    expect(onSessionExpired).toHaveBeenCalledWith({ expired: false })
  })

  it('échec du CSRF (5xx) : le cache est vidé, la mutation retente au prochain appel', async () => {
    let csrfAttempts = 0
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) {
        csrfAttempts += 1
        return csrfAttempts === 1
          ? json(500, { error: { code: 'INTERNAL', message: 'Erreur interne.', request_id: 'r' } })
          : json(200, { csrf_token: 'tok-retry' })
      }
      return json(200, ME)
    })
    const client = new ApiClient({ fetchFn: fetchMock })

    const first = await client.login('a@b.c', 'x').catch((e: unknown) => e)
    expect(first).toMatchObject({ status: 500 })

    await expect(client.login('a@b.c', 'x')).resolves.toEqual(ME)
    expect(csrfAttempts).toBe(2)
  })
})

describe('lib/api.ts — redirection 401 (helper pur)', () => {
  it('construit /login?next=<url encodée>&reason=expired pour une mutation 401', () => {
    expect(buildSessionExpiredUrl('/app', '', true)).toBe('/login?next=%2Fapp&reason=expired')
  })

  it('construit /login?next=<url encodée> sans reason pour un 401 de chargement', () => {
    expect(buildSessionExpiredUrl('/client/m/1', '?a=b', false)).toBe('/login?next=%2Fclient%2Fm%2F1%3Fa%3Db')
  })

  it('renvoie null si déjà sur une page auth (pas de boucle)', () => {
    expect(buildSessionExpiredUrl('/login', '', true)).toBeNull()
    expect(buildSessionExpiredUrl('/forgot', '', false)).toBeNull()
    expect(buildSessionExpiredUrl('/reset', '?token=x', false)).toBeNull()
    expect(buildSessionExpiredUrl('/invite', '', true)).toBeNull()
  })
})
