import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { api, ApiError } from '../lib/api'
import { sanitizeNextPath } from '../lib/routing'
import { AuthCard } from './AuthCard'
import { Banner, Button, PasswordField, TextField } from '../components/fields'

/** Format e-mail minimal, côté client (le serveur reste l'autorité). */
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface FormError {
  message: string
  requestId: string | null
}

/**
 * Erreur de connexion : jamais révélatrice de l'existence d'un compte (DESIGN §1.5/P1).
 * 401/400 → message générique ; 429 → limitation ; 5xx/réseau → fait + issue.
 */
function toLoginError(error: unknown): FormError {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 400) {
      return { message: 'E-mail ou mot de passe incorrect.', requestId: null }
    }
    if (error.status === 429) {
      return { message: 'Trop de requêtes. Réessayez dans un instant.', requestId: null }
    }
    if (error.status === 0) {
      return { message: 'Le serveur est injoignable. Vérifiez votre connexion puis réessayez.', requestId: null }
    }
    return {
      message: `Le serveur a refusé la requête (${error.status}). Réessayez plus tard.`,
      requestId: error.requestId,
    }
  }
  return { message: 'Une erreur inattendue est survenue. Réessayez.', requestId: null }
}

export function LoginPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})
  const [formError, setFormError] = useState<FormError | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const reason = searchParams.get('reason')
  const resetDone = searchParams.get('reset')
  const next = searchParams.get('next')

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (submitting) return
    const errors: { email?: string; password?: string } = {}
    const trimmedEmail = email.trim()
    if (trimmedEmail.length === 0) errors.email = 'L’adresse e-mail est requise.'
    else if (!EMAIL_PATTERN.test(trimmedEmail)) errors.email = 'Adresse e-mail invalide.'
    if (password.length === 0) errors.password = 'Le mot de passe est requis.'
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setFormError(null)
    setSubmitting(true)
    try {
      // Le jeton CSRF est géré par le client API (D-05) ; le serveur est la
      // source de vérité du rôle — la redirection suit /auth/me, pas l'URL.
      await api.login(trimmedEmail, password)
      navigate(sanitizeNextPath(next) ?? '/', { replace: true })
    } catch (error) {
      setFormError(toLoginError(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Connexion"
      footer={
        <p>
          Vous avez reçu une invitation ?{' '}
          <Link to="/invite" className="font-medium text-accent hover:underline">
            Accepter l’invitation
          </Link>
        </p>
      }
    >
      <form onSubmit={(event) => void handleSubmit(event)} noValidate className="flex flex-col gap-4">
        {reason === 'expired' && (
          <Banner tone="neutral">Session expirée. Reconnectez-vous pour continuer.</Banner>
        )}
        {resetDone === '1' && (
          <Banner tone="success">Mot de passe réinitialisé. Connectez-vous avec votre nouveau mot de passe.</Banner>
        )}
        <TextField
          id="login-email"
          label="Adresse e-mail"
          type="email"
          inputMode="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldErrors.email}
        />
        <PasswordField
          id="login-password"
          value={password}
          onChange={setPassword}
          autoComplete="current-password"
          required
          error={fieldErrors.password}
        />
        {formError !== null && (
          <div id="login-erreur" aria-live="assertive">
            <Banner tone="danger">
              <p>{formError.message}</p>
              {formError.requestId !== null && (
                <p className="mt-1 font-mono text-xs text-ink-faint">request_id : {formError.requestId}</p>
              )}
            </Banner>
          </div>
        )}
        <div className="flex items-center justify-between">
          <Link to="/forgot" className="text-xs font-medium text-accent hover:underline">
            Mot de passe oublié ?
          </Link>
        </div>
        <Button type="submit" loading={submitting}>
          Se connecter
        </Button>
      </form>
    </AuthCard>
  )
}
