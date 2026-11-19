import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { api, ApiError } from '../lib/api'
import { passwordIssue } from '../lib/password'
import { AuthCard } from './AuthCard'
import { Banner, Button, PasswordField, TextField } from '../components/fields'

/**
 * /invite?token=…[&email=…] — acceptation d'invitation (DESIGN P1).
 * E-mail présélectionné si fourni par le lien ; le token est lié au destinataire
 * côté serveur (spec §8) : l'e-mail affiché est informatif, seul le token fait foi.
 * À l'acceptation, la connexion est automatique (redirection vers / → /auth/me).
 */
export function AcceptInvitationPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')
  const invitedEmail = searchParams.get('email')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [fieldErrors, setFieldErrors] = useState<{ password?: string; confirmation?: string }>({})
  const [formError, setFormError] = useState<{ message: string; requestId: string | null; expired: boolean } | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (token === null || token.length === 0) {
    return (
      <AuthCard
        title="Invitation invalide"
        footer={
          <Link to="/login" className="font-medium text-accent hover:underline">
            Revenir à la connexion
          </Link>
        }
      >
        <Banner tone="neutral">Ce lien d’invitation est manquant ou invalide. Contactez un administrateur de votre cabinet.</Banner>
      </AuthCard>
    )
  }
  // Comme ci-dessus : le narrowing de `token` n'est pas conservé dans les closures.
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
      await api.acceptInvitation(tokenValue, password)
      navigate('/', { replace: true })
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
      title="Accepter l’invitation"
      footer={
        <p>
          <Link to="/login" className="font-medium text-accent hover:underline">
            Revenir à la connexion
          </Link>
        </p>
      }
    >
      <form onSubmit={(event) => void handleSubmit(event)} noValidate className="flex flex-col gap-4">
        <p className="text-sm text-ink-soft">
          Choisissez un mot de passe pour votre compte. Après acceptation, vous serez connecté automatiquement.
        </p>
        {invitedEmail !== null && invitedEmail.length > 0 && (
          <TextField
            id="invite-email"
            label="Adresse e-mail (issu de l’invitation)"
            type="email"
            value={invitedEmail}
            disabled
            hint="L’adresse est définie par l’invitation ; seule sa modification, par un administrateur, peut la changer."
          />
        )}
        <PasswordField
          id="invite-password"
          label="Mot de passe"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          required
          error={fieldErrors.password}
          hint="10 à 72 caractères, au moins une minuscule, une majuscule et un chiffre."
        />
        <PasswordField
          id="invite-confirmation"
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
            </Banner>
          </div>
        )}
        <Button type="submit" loading={submitting}>
          Accepter l’invitation
        </Button>
      </form>
    </AuthCard>
  )
}
