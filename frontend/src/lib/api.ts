import type { AuthMe, CsrfResponse } from './types'

/**
 * Client HTTP ChainScope.
 *
 * - Origine unique : le navigateur ne parle qu'au backend (spec §2) →
 *   `credentials: 'same-origin'` et `baseURL` relative `/api/v1`.
 * - CSRF (DECISIONS D-05) : toute mutation cookie-based (POST/PATCH/PUT/DELETE)
 *   attache le header `X-CSRF-Token`, obtenu via `GET /auth/csrf` — cache en
 *   mémoire, 1 seul appel tant que le token est valide.
 * - Erreurs (spec §6, D-06) : enveloppe normalisée `{ error: { code, message, request_id } }`.
 * - 401 : émission de l'événement `SESSION_EXPIRED_EVENT` + callback injectable ;
 *   le handler par défaut redirige vers `/login` (jamais depuis une page auth).
 * - 403 : surfacé tel quel (ApiError), aucune redirection.
 */

export const API_BASE_URL = '/api/v1'

/** Nom de l'événement DOM émis sur 401 (« session expirée / absente »). */
export const SESSION_EXPIRED_EVENT = 'chainscope:session-expired'

const MUTATING_METHODS: readonly string[] = ['POST', 'PATCH', 'PUT', 'DELETE']

/** Préfixes des pages d'authentification : pas de redirection 401 depuis ces pages. */
const AUTH_PATH_PREFIXES: readonly string[] = ['/login', '/forgot', '/reset', '/invite']

interface ErrorEnvelope {
  error?: { code?: unknown; message?: unknown; request_id?: unknown }
}

export interface SessionExpiredInfo {
  /** true si le 401 provient d'une mutation (session expirée en cours d'action). */
  expired: boolean
}

/** Erreur d'API construite depuis l'enveloppe normalisée du backend. */
export class ApiError extends Error {
  /** Statut HTTP reçu ; 0 = erreur réseau (serveur injoignable). */
  readonly status: number
  readonly code: string
  readonly requestId: string | null

  constructor(status: number, code: string, message: string, requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
  }

  /** Construit une ApiError depuis l'enveloppe `{ error: { code, message, request_id } }`. */
  static fromEnvelope(status: number, payload: unknown): ApiError {
    const envelope =
      payload !== null && typeof payload === 'object' ? (payload as ErrorEnvelope).error : undefined
    const code =
      envelope !== undefined && typeof envelope.code === 'string' && envelope.code.length > 0
        ? envelope.code
        : `HTTP_${status}`
    const message =
      envelope !== undefined && typeof envelope.message === 'string' && envelope.message.length > 0
        ? envelope.message
        : `Le serveur a renvoyé une réponse inattendue (${status}).`
    const requestId =
      envelope !== undefined &&
      typeof envelope.request_id === 'string' &&
      envelope.request_id.length > 0
        ? envelope.request_id
        : null
    return new ApiError(status, code, message, requestId)
  }
}

export interface ApiClientOptions {
  baseUrl?: string
  /** Injectable pour les tests ; défaut : `window.fetch`. */
  fetchFn?: typeof fetch
  /** Callback appelé sur tout 401 (en plus de l'événement DOM). */
  onSessionExpired?: (info: SessionExpiredInfo) => void
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text()
  if (text.length === 0) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    // Corps non-JSON (page d'erreur du proxy, 502 de dev…) : l'appelant
    // reçoit alors une ApiError factuelle avec le statut.
    return null
  }
}

function buildUrl(baseUrl: string, path: string, query?: Record<string, string | number>): string {
  let url = `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`
  if (query !== undefined) {
    const params = new URLSearchParams()
    for (const [key, value] of Object.entries(query)) {
      params.set(key, String(value))
    }
    const qs = params.toString()
    if (qs.length > 0) url += `?${qs}`
  }
  return url
}

/**
 * URL cible du 401 : `/login?next=<url encodée>[&reason=expired]`.
 * Renvoie `null` si l'on est déjà sur une page auth (pas de boucle).
 */
export function buildSessionExpiredUrl(pathname: string, search: string, expired: boolean): string | null {
  const onAuthPage = AUTH_PATH_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  )
  if (onAuthPage) return null
  const next = encodeURIComponent(pathname + search)
  const reason = expired ? '&reason=expired' : ''
  return `/login?next=${next}${reason}`
}

function defaultSessionExpiredHandler(info: SessionExpiredInfo): void {
  const url = buildSessionExpiredUrl(window.location.pathname, window.location.search, info.expired)
  if (url !== null) window.location.assign(url)
}

export interface RequestOptions {
  method?: string
  query?: Record<string, string | number>
  /** Corps JSON (mutations). `undefined` = sans corps. */
  body?: unknown
}

export class ApiClient {
  private readonly baseUrl: string
  private readonly fetchFn: typeof fetch
  private readonly onSessionExpired: (info: SessionExpiredInfo) => void
  private csrfToken: string | null = null
  private csrfPromise: Promise<string> | null = null

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = options.baseUrl ?? API_BASE_URL
    this.fetchFn = options.fetchFn ?? ((input, init) => fetch(input, init))
    this.onSessionExpired = options.onSessionExpired ?? defaultSessionExpiredHandler
  }

  /** Libère le cache CSRF (usage : test, ou après changement de session). */
  resetCsrfCache(): void {
    this.csrfToken = null
    this.csrfPromise = null
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const method = (options.method ?? 'GET').toUpperCase()
    const headers = new Headers()
    headers.set('Accept', 'application/json')
    if (options.body !== undefined) headers.set('Content-Type', 'application/json')
    if (MUTATING_METHODS.includes(method)) {
      headers.set('X-CSRF-Token', await this.resolveCsrfToken())
    }
    let response: Response
    try {
      response = await this.fetchFn(buildUrl(this.baseUrl, path, options.query), {
        method,
        headers,
        credentials: 'same-origin',
        body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      })
    } catch {
      throw new ApiError(0, 'NETWORK', 'Le serveur est injoignable.', null)
    }
    if (response.status === 204) return undefined as T
    const payload = await readJson(response)
    if (!response.ok) {
      const error = ApiError.fromEnvelope(response.status, payload)
      if (response.status === 401) this.notifySessionExpired(MUTATING_METHODS.includes(method))
      throw error
    }
    return payload as T
  }

  /** `GET /auth/csrf` : token opaque par session (D-05). Un seul appel tant que le token est en cache. */
  private resolveCsrfToken(): Promise<string> {
    if (this.csrfToken !== null) return Promise.resolve(this.csrfToken)
    if (this.csrfPromise === null) {
      this.csrfPromise = this.fetchCsrfToken().finally(() => {
        // Échec (réseau, 401, 5xx) : le cache est vidé pour permettre une nouvel
        // tentative à l'appelant suivant ; succès : le token reste en mémoire.
        if (this.csrfToken === null) this.csrfPromise = null
      })
    }
    return this.csrfPromise
  }

  private async fetchCsrfToken(): Promise<string> {
    let response: Response
    try {
      response = await this.fetchFn(`${this.baseUrl}/auth/csrf`, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        credentials: 'same-origin',
      })
    } catch {
      throw new ApiError(0, 'NETWORK', 'Le serveur est injoignable.', null)
    }
    if (!response.ok) {
      const error = ApiError.fromEnvelope(response.status, await readJson(response))
      // Session absente/expirée : on signale avant même la mutation.
      if (response.status === 401) this.notifySessionExpired(false)
      throw error
    }
    const body = (await readJson(response)) as CsrfResponse | null
    if (body === null || typeof body.csrf_token !== 'string' || body.csrf_token.length === 0) {
      throw new ApiError(response.status, 'CSRF_MALFORMED', 'Le jeton CSRF renvoyé par le serveur est invalide.', null)
    }
    this.csrfToken = body.csrf_token
    return body.csrf_token
  }

  private notifySessionExpired(expired: boolean): void {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent<SessionExpiredInfo>(SESSION_EXPIRED_EVENT, { detail: { expired } }))
    }
    this.onSessionExpired({ expired })
  }

  // ---- Routes d'authentification (spec §6) ----

  /** `POST /auth/login` — cookie de session + résultat utilisateur (contrat provisoire, cf. PR #5). */
  login(email: string, password: string): Promise<AuthMe> {
    return this.request<AuthMe>('/auth/login', { method: 'POST', body: { email, password } })
  }

  /** `GET /auth/me` — identité et memberships de la session courante. */
  getMe(): Promise<AuthMe> {
    return this.request<AuthMe>('/auth/me')
  }

  /** `POST /auth/logout` — révocation de la session (D-04). */
  logout(): Promise<void> {
    return this.request<void>('/auth/logout', { method: 'POST' })
  }

  /** `POST /auth/forgot-password` — réponse non révélatrice d'existence de compte. */
  forgotPassword(email: string): Promise<void> {
    return this.request<void>('/auth/forgot-password', { method: 'POST', body: { email } })
  }

  /** `POST /auth/reset-password` — token à usage unique (D-12). */
  resetPassword(token: string, password: string): Promise<void> {
    return this.request<void>('/auth/reset-password', { method: 'POST', body: { token, password } })
  }

  /** `POST /auth/accept-invitation` — token et nouveau mot de passe ; connexion automatique. */
  acceptInvitation(token: string, password: string): Promise<void> {
    return this.request<void>('/auth/accept-invitation', { method: 'POST', body: { token, password } })
  }
}

/** Instance partagée de l'application (singleton). */
export const api = new ApiClient()
