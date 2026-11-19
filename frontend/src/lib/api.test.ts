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

  it('mutations : /auth/csrf absent pour la route anonyme, token sur la mutation session (cache mémoire)', async () => {
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

    expect(csrfCalls).toBe(1) // un seul appel : pour logout, jamais pour login (route anonyme)
    expect(seen).toHaveLength(2)
    expect(seen[0]?.url).toBe(`${API_BASE_URL}/auth/login`)
    expect(seen[0]?.token).toBeNull() // exemptée : aucun header X-CSRF-Token
    expect(seen[1]?.url).toBe(`${API_BASE_URL}/auth/logout`)
    expect(seen[1]?.token).toBe('tok-csrf-1')
    for (const entry of seen) {
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

  it('resetPassword : corps { token, password, password_confirmation } (contrat D-19 / PR #32), sans /auth/csrf (route anonyme)', async () => {
    const urls: string[] = []
    let body: unknown = null
    const fetchMock = mockFetch((url, init) => {
      urls.push(url)
      body = JSON.parse(String(init?.body)) as unknown
      return json(204)
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    await client.resetPassword('tk-123', 'Nouveau123', 'Nouveau123')
    expect(body).toEqual({ token: 'tk-123', password: 'Nouveau123', password_confirmation: 'Nouveau123' })
    expect(urls).toEqual([`${API_BASE_URL}/auth/reset-password`])
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

  it('401 sur /auth/csrf (mutation session) : la mutation n’est pas envoyée, session expirée signalée', async () => {
    const onSessionExpired = vi.fn()
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) {
        return json(401, { error: { code: 'UNAUTHORIZED', message: 'Non authentifié.', request_id: 'r' } })
      }
      throw new Error('la mutation ne doit pas être envoyée')
    })
    const client = new ApiClient({ fetchFn: fetchMock, onSessionExpired })
    const error = await client.logout().catch((e: unknown) => e)
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
      return json(204)
    })
    const client = new ApiClient({ fetchFn: fetchMock })

    const first = await client.logout().catch((e: unknown) => e)
    expect(first).toMatchObject({ status: 500 })

    await expect(client.logout()).resolves.toBeUndefined()
    expect(csrfAttempts).toBe(2)
  })
})

describe('lib/api.ts — rotation CSRF (arbitrage Cyber PR #32, issue #37)', () => {
  const ENGAGEMENTS = '/tenants/t-1/engagements'

  it('403 CSRF_INVALID sur mutation : invalidation du cache, re-fetch du token, retry unique réussi', async () => {
    let csrfCalls = 0
    let postCalls = 0
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith('/auth/csrf')) {
        csrfCalls += 1
        return json(200, { csrf_token: csrfCalls === 1 ? 'tok-ancien' : 'tok-roté' })
      }
      postCalls += 1
      if (postCalls === 1) {
        expect(headersOf(init).get('X-CSRF-Token')).toBe('tok-ancien')
        return json(403, {
          error: { code: 'CSRF_INVALID', message: 'Jeton CSRF invalide (roté par un autre appel).', request_id: 'req-csrf-1' },
        })
      }
      expect(headersOf(init).get('X-CSRF-Token')).toBe('tok-roté')
      return json(200, { created: true })
    })
    const client = new ApiClient({ fetchFn: fetchMock })

    await expect(client.request(ENGAGEMENTS, { method: 'POST', body: { name: 'Audit Web 2026' } })).resolves.toEqual({
      created: true,
    })
    expect(csrfCalls).toBe(2) // cache invalidé puis re-fetch
    expect(postCalls).toBe(2) // essai initial + retry unique
  })

  it('403 CSRF_INVALID persistant : ApiError surfacé, un seul retry, pas de boucle', async () => {
    let csrfCalls = 0
    let postCalls = 0
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) {
        csrfCalls += 1
        return json(200, { csrf_token: `tok-${csrfCalls}` })
      }
      postCalls += 1
      return json(403, {
        error: { code: 'CSRF_INVALID', message: 'Jeton CSRF invalide.', request_id: postCalls === 1 ? 'req-a' : 'req-b' },
      })
    })
    const client = new ApiClient({ fetchFn: fetchMock })

    const error = await client.request(ENGAGEMENTS, { method: 'POST', body: {} }).catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 403, code: 'CSRF_INVALID', requestId: 'req-b' })
    expect(postCalls).toBe(2) // exactement un retry
    expect(csrfCalls).toBe(2)
  })

  it('403 autre que CSRF_INVALID sur mutation : aucun retry (comportement inchangé)', async () => {
    let postCalls = 0
    const fetchMock = mockFetch((url) => {
      if (url.endsWith('/auth/csrf')) return json(200, { csrf_token: 'tok' })
      postCalls += 1
      return json(403, {
        error: { code: 'FORBIDDEN', message: 'Permission insuffisante.', request_id: 'req-f' },
      })
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    const error = await client.request(ENGAGEMENTS, { method: 'POST', body: {} }).catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 403, code: 'FORBIDDEN' })
    expect(postCalls).toBe(1)
  })

  it('GET 403 CSRF_INVALID : aucun retry (non mutation, pas de token géré)', async () => {
    let calls = 0
    const fetchMock = mockFetch(() => {
      calls += 1
      return json(403, {
        error: { code: 'CSRF_INVALID', message: 'Jeton CSRF invalide.', request_id: 'req-g' },
      })
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    const error = await client.request(ENGAGEMENTS).catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 403, code: 'CSRF_INVALID' })
    expect(calls).toBe(1)
  })

  it('routes anonymes (login, forgot, reset, accept) : aucun /auth/csrf, aucun header, aucun retry sur 403', async () => {
    let postCalls = 0
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith('/auth/csrf')) throw new Error('aucun /auth/csrf attendu pour une route anonyme')
      if (url.endsWith('/auth/login')) {
        postCalls += 1
        expect(headersOf(init).get('X-CSRF-Token')).toBeNull()
        // 403 (autre code) sur route exemptée : surfacé tel quel, jamais de re-fetch
        return json(403, {
          error: { code: 'FORBIDDEN', message: 'Refus.', request_id: 'req-x' },
        })
      }
      return json(204)
    })
    const client = new ApiClient({ fetchFn: fetchMock })
    const error = await client.login('a@b.c', 'x').catch((e: unknown) => e)
    expect(error).toMatchObject({ status: 403, code: 'FORBIDDEN' })
    expect(postCalls).toBe(1)
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
