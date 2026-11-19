import type { AuthMe, CsrfResponse } from './types'

/**
 * Client HTTP ChainScope.
 *
 * - Origine unique : le navigateur ne parle qu'au backend (spec §2) →
 *   `credentials: 'same-origin'` et `baseURL` relative `/api/v1`.
 * - CSRF (DECISIONS D-05, rotation arbitrée Cyber PR #32 / issue #37) :
 *   les mutations session (POST/PATCH/PUT/DELETE hors routes anonymes)
 *   attachent le header `X-CSRF-Token`, obtenu via `GET /auth/csrf` — cache
 *   mémoire, 1 seul appel ; le backend **rotate** le token à chaque
 *   `/auth/csrf`, donc sur `403 CSRF_INVALID` : re-fetch + **retry unique**
 *   de la mutation (un second 403 est surfacé). Les routes anonymes
 *   (login, forgot-password, reset-password, accept-invitation) ne
 *   déclenchent aucun `/auth/csrf` (pas de session ⇒ 401 garanti).
 * - Erreurs (spec §6, D-06) : enveloppe normalisée `{ error: { code, message, request_id } }`.
 * - 401 : émission de l'événement `SESSION_EXPIRED_EVENT` + callback injectable ;
 *   le handler par défaut redirige vers `/login` (jamais depuis une page auth).
 * - 403 : surfacé tel quel (ApiError), aucune redirection ; exception :
 *   `CSRF_INVALID` sur une mutation → re-fetch du token + retry unique (cf. CSRF).
 */

export const API_BASE_URL = '/api/v1'

/** Nom de l'événement DOM émis sur 401 (« session expirée / absente »). */
export const SESSION_EXPIRED_EVENT = 'chainscope:session-expired'

const MUTATING_METHODS: readonly string[] = ['POST', 'PATCH', 'PUT', 'DELETE']

/**
 * Routes exemptées CSRF : routes d'authentification anonymes (pas de session,
 * donc pas de cookie `cs_session`) — le serveur ne vérifie pas `X-CSRF-Token`
 * dessus (arbitrage Cyber sur la PR #32, issue #37 ; cf. D-05 « mutations
 * fondées sur les cookies » et D-07 : les quatre POST anonymes). Le client ne
 * déclenche donc **aucun** `GET /auth/csrf` avant elles, et le 403
 * `CSRF_INVALID` n'y surviendra pas : pas de retry pour ces routes.
 */
const CSRF_EXEMPT_PATHS: readonly string[] = [
  '/auth/login',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/auth/accept-invitation',
]

/** Code d'erreur normalisé renvoyé par le backend quand le token CSRF est invalide (roté). */
const CSRF_INVALID_CODE = 'CSRF_INVALID'

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

/** Résultat typé d'un échange HTTP (le 4xx/5xx n'est pas levé ici : c'est `request` qui décide). */
type FetchOutcome = { ok: true; data: unknown } | { ok: false; error: ApiError }

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
    const isMutation = MUTATING_METHODS.includes(method)
    // Les routes exemptées (anonymes) n'ont pas de token à récupérer : le
    // premier appel de /auth/csrf y renverrait un 401 (pas de session) et
    // bloquerait la soumission (issue #37).
    const needsCsrf = isMutation && !CSRF_EXEMPT_PATHS.includes(path)
    const headers = new Headers()
    headers.set('Accept', 'application/json')
    const body = options.body !== undefined ? JSON.stringify(options.body) : undefined
    if (body !== undefined) headers.set('Content-Type', 'application/json')
    if (needsCsrf) {
      headers.set('X-CSRF-Token', await this.resolveCsrfToken())
    }

    const url = buildUrl(this.baseUrl, path, options.query)
    let outcome = await this.fetchOutcome(url, method, headers, body)

    // Contrat de rotation CSRF (arbitrage Cyber PR #32, issue #37) : le backend
    // rotate le token à chaque GET /auth/csrf — le token en cache mémoire peut
    // être invalidé par un appel concurrent (ex. un autre onglet). Sur 403
    // `CSRF_INVALID` : invalidation du cache, re-fetch du token, puis retry
    // UNIQUE de la mutation ; un second 403 est surfacé tel quel.
    if (
      !outcome.ok &&
      needsCsrf &&
      outcome.error.status === 403 &&
      outcome.error.code === CSRF_INVALID_CODE
    ) {
      this.resetCsrfCache()
      headers.set('X-CSRF-Token', await this.resolveCsrfToken())
      outcome = await this.fetchOutcome(url, method, headers, body)
    }

    if (!outcome.ok) {
      if (outcome.error.status === 401) this.notifySessionExpired(isMutation)
      throw outcome.error
    }
    return outcome.data as T
  }

  /** Effectue l'appel et le convertit en `FetchOutcome` (réseau → ApiError 0/NETWORK). */
  private async fetchOutcome(
    url: string,
    method: string,
    headers: Headers,
    body: string | undefined,
  ): Promise<FetchOutcome> {
    let response: Response
    try {
      response = await this.fetchFn(url, { method, headers, credentials: 'same-origin', body })
    } catch {
      return { ok: false, error: new ApiError(0, 'NETWORK', 'Le serveur est injoignable.', null) }
    }
    if (response.status === 204) return { ok: true, data: undefined }
    const payload = await readJson(response)
    if (!response.ok) {
      return { ok: false, error: ApiError.fromEnvelope(response.status, payload) }
    }
    return { ok: true, data: payload }
  }

  /** `GET /auth/csrf` : token opaque par session (D-05). Un seul appel tant que le token est en cache. */
  private resolveCsrfToken(): Promise<string> {
    if (this.csrfToken !== null) return Promise.resolve(this.csrfToken)
    if (this.csrfPromise === null) {
      this.csrfPromise = this.fetchCsrfToken().finally(() => {
        // Échec (réseau, 401, 5xx) : le cache est vidé pour permettre une nouvelle
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

  /**
   * `POST /auth/reset-password` — token à usage unique (D-12).
   * Contrat figé (contrat auth D-19 / PR #32, issue #5) : le corps exige
   * `password_confirmation` (422 si absent ou différent du mot de passe).
   */
  resetPassword(token: string, password: string, passwordConfirmation: string): Promise<void> {
    return this.request<void>('/auth/reset-password', {
      method: 'POST',
      body: { token, password, password_confirmation: passwordConfirmation },
    })
  }

  /** `POST /auth/accept-invitation` — token et nouveau mot de passe ; connexion automatique. */
  acceptInvitation(token: string, password: string): Promise<void> {
    return this.request<void>('/auth/accept-invitation', { method: 'POST', body: { token, password } })
  }
}

/** Instance partagée de l'application (singleton). */
export const api = new ApiClient()
