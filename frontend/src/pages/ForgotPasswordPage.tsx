import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router'
import { api, ApiError } from '../lib/api'
import { AuthCard } from './AuthCard'
import { Banner, Button, TextField } from '../components/fields'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

type Stage = 'form' | 'sent'

/**
 * /forgot — e-mail seul → message NEUTRE d'envoi (DESIGN P1) :
 * aucune énumération de compte (spec §8, D-07).
 */
export function ForgotPasswordPage() {
  const [stage, setStage] = useState<Stage>('form')
  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)
  const [formError, setFormError] = useState<{ message: string; requestId: string | null } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    if (submitting) return
    const trimmed = email.trim()
    if (trimmed.length === 0) {
      setFieldError('L’adresse e-mail est requise.')
      return
    }
    if (!EMAIL_PATTERN.test(trimmed)) {
      setFieldError('Adresse e-mail invalide.')
      return
    }
    setFieldError(null)
    setFormError(null)
    setSubmitting(true)
    try {
      await api.forgotPassword(trimmed)
      setStage('sent')
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setFormError({ message: 'Trop de requêtes. Réessayez dans un instant.', requestId: null })
      } else if (error instanceof ApiError && error.status === 0) {
        setFormError({ message: 'Le serveur est injoignable. Vérifiez votre connexion puis réessayez.', requestId: null })
      } else if (error instanceof ApiError) {
        // Non révélateur d'existence (D-07) : fait + issue seulement.
        setFormError({
          message: `Le serveur a refusé la requête (${error.status}). Réessayez plus tard.`,
          requestId: error.requestId,
        })
      } else {
        setFormError({ message: 'Une erreur inattendue est survenue. Réessayez.', requestId: null })
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Mot de passe oublié"
      footer={
        <p>
          <Link to="/login" className="font-medium text-accent hover:underline">
            Revenir à la connexion
          </Link>
        </p>
      }
    >
      {stage === 'sent' ? (
        <div className="flex flex-col gap-4">
          <Banner tone="success">Si un compte existe pour cette adresse, un lien a été envoyé.</Banner>
          <Button variant="ghost" onClick={() => setStage('form')}>
            Utiliser une autre adresse
          </Button>
        </div>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)} noValidate className="flex flex-col gap-4">
          <p className="text-sm text-ink-soft">
            Saisissez votre adresse e-mail : si un compte existe, vous recevrez un lien de réinitialisation à usage unique.
          </p>
          <TextField
            id="forgot-email"
            label="Adresse e-mail"
            type="email"
            inputMode="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            error={fieldError}
          />
          {formError !== null && (
            <div aria-live="assertive">
              <Banner tone="danger">
                <p>{formError.message}</p>
                {formError.requestId !== null && (
                  <p className="mt-1 font-mono text-xs text-ink-faint">request_id : {formError.requestId}</p>
                )}
              </Banner>
            </div>
          )}
          <Button type="submit" loading={submitting}>
            Envoyer le lien
          </Button>
        </form>
      )}
    </AuthCard>
  )
}
