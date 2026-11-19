import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { api, ApiError } from '../lib/api'
import { passwordIssue } from '../lib/password'
import { AuthCard } from './AuthCard'
import { Banner, Button, PasswordField } from '../components/fields'

/**
 * /reset?token=… — nouveau mot de passe + confirmation (DESIGN P1).
 * Validation côté client : 10–72 caractères, minuscules/majuscules/chiffres.
 * Le token est à usage unique côté serveur (spec §8, D-12).
 */
export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ password?: string; confirmation?: string }>({})
  const [formError, setFormError] = useState<{ message: string; requestId: string | null; expired: boolean } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (token === null || token.length === 0) {
    return (
      <AuthCard
        title="Lien de réinitialisation invalide"
        footer={
          <Link to="/login" className="font-medium text-accent hover:underline">
            Revenir à la connexion
          </Link>
        }
      >
        <Banner tone="neutral">Ce lien est manquant ou invalide. Demandez un nouveau lien depuis la page de connexion.</Banner>
      </AuthCard>
    )
  }
  // `token` est rétro-narrowé en string ; on fixe le type pour les closures
  // de soumission (le narrowing n'est pas conservé par les fonctions imbriquées).
  const tokenValue: string = token

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (submitting) return
    const errors: { password?: string; confirmation?: string } = {}
    const issue = passwordIssue(password)
    if (issue !== null) errors.password = issue
    if (confirmation !== password) errors.confirmation = 'Les mots de passe ne correspondent pas.'
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    setFormError(null)
    setSubmitting(true)
    try {
      // Contrat figé (D-19 / PR #32) : `password_confirmation` est exigé par le
      // serveur (422 si absent ou différent) — déjà validé côté client ci-dessus.
      await api.resetPassword(tokenValue, password, confirmation)
      navigate('/login?reset=1', { replace: true })
    } catch (error) {
      if (error instanceof ApiError && (error.status === 400 || error.status === 401 || error.status === 404 || error.status === 409)) {
        setFormError({ message: 'Ce lien a expiré ou a déjà été utilisé.', requestId: null, expired: true })
      } else if (error instanceof ApiError && error.status === 429) {
        setFormError({ message: 'Trop de requêtes. Réessayez dans un instant.', requestId: null, expired: false })
      } else if (error instanceof ApiError && error.status === 0) {
        setFormError({ message: 'Le serveur est injoignable. Vérifiez votre connexion puis réessayez.', requestId: null, expired: false })
      } else if (error instanceof ApiError) {
        setFormError({
          message: `Le serveur a refusé la requête (${error.status}). Réessayez plus tard.`,
          requestId: error.requestId,
          expired: false,
        })
      } else {
        setFormError({ message: 'Une erreur inattendue est survenue. Réessayez.', requestId: null, expired: false })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Réinitialiser le mot de passe"
      footer={
        <p>
          <Link to="/login" className="font-medium text-accent hover:underline">
            Revenir à la connexion
          </Link>
        </p>
      }
    >
      <form onSubmit={(event) => void handleSubmit(event)} noValidate className="flex flex-col gap-4">
        <PasswordField
          id="reset-password"
          label="Nouveau mot de passe"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          required
          error={fieldErrors.password}
          hint="10 à 72 caractères, au moins une minuscule, une majuscule et un chiffre."
        />
        <PasswordField
          id="reset-confirmation"
          label="Confirmer le mot de passe"
          value={confirmation}
          onChange={setConfirmation}
          autoComplete="new-password"
          required
          error={fieldErrors.confirmation}
        />
        {formError !== null && (
          <div aria-live="assertive">
            <Banner tone="danger">
              <p>{formError.message}</p>
              {formError.requestId !== null && (
                <p className="mt-1 font-mono text-xs text-ink-faint">request_id : {formError.requestId}</p>
              )}
              {formError.expired && (
                <p className="mt-2">
                  <Link to="/forgot" className="font-medium text-accent hover:underline">
                    Demander un nouveau lien
                  </Link>
                </p>
              )}
            </Banner>
          </div>
        )}
        <Button type="submit" loading={submitting}>
          Réinitialiser
        </Button>
      </form>
    </AuthCard>
  )
}
