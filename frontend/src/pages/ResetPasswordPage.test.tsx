import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router'
import { api, ApiError } from '../lib/api'
import { passwordIssue } from '../lib/password'
import { ResetPasswordPage } from './ResetPasswordPage'

vi.mock('../lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../lib/api')>()
  return {
    ...actual,
    api: { resetPassword: vi.fn() },
  }
})

function renderAtReset(initialEntry = '/reset?token=tk-123') {
  const user = userEvent.setup()
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/reset" element={<ResetPasswordPage />} />
          <Route path="/login" element={<div data-testid="login">Login</div>} />
          <Route path="/forgot" element={<div data-testid="forgot">Mot de passe oublié</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return { user, ...utils }
}

function submitReset(user: ReturnType<typeof userEvent.setup>) {
  return user.click(screen.getByRole('button', { name: 'Réinitialiser' }))
}

// Les labels incluent l'astérisque de champ requis : correspondance par préfixe.
const NEW_PASSWORD_LABEL = /^Nouveau mot de passe/
const CONFIRM_PASSWORD_LABEL = /^Confirmer le mot de passe/

describe('ResetPasswordPage — validation du mot de passe', () => {
  it('refuse moins de 10 caractères', () => {
    expect(passwordIssue('Abcdef12')).toMatch(/entre 10 et 72/)
  })

  it('refuse plus de 72 caractères', () => {
    expect(passwordIssue('A'.repeat(71) + '1a')).toMatch(/entre 10 et 72/)
  })

  it('exige minuscules, majuscules et chiffres', () => {
    expect(passwordIssue('nouveau123')).toBe('Le mot de passe doit contenir une majuscule.')
    expect(passwordIssue('NOUVEAU123')).toBe('Le mot de passe doit contenir une minuscule.')
    expect(passwordIssue('AaAaAaAaAa')).toBe('Le mot de passe doit contenir un chiffre.')
    expect(passwordIssue('Aa12345678')).toBeNull()
  })

  it('valide un mot de passe conforme (10–72, minuscule, majuscule, chiffre)', async () => {
    vi.mocked(api.resetPassword).mockResolvedValue(undefined)
    const { user } = renderAtReset()
    await user.type(screen.getByLabelText(NEW_PASSWORD_LABEL), 'Nouveau123')
    await user.type(screen.getByLabelText(CONFIRM_PASSWORD_LABEL), 'Nouveau123')
    await submitReset(user)
    expect(await screen.findByTestId('login')).toBeInTheDocument()
    expect(vi.mocked(api.resetPassword)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(api.resetPassword)).toHaveBeenCalledWith('tk-123', 'Nouveau123')
  })

  it('refuse une confirmation non correspondante (le mot de passe est conforme)', async () => {
    vi.mocked(api.resetPassword).mockResolvedValue(undefined)
    const { user } = renderAtReset()
    await user.type(screen.getByLabelText(NEW_PASSWORD_LABEL), 'Nouveau123')
    await user.type(screen.getByLabelText(CONFIRM_PASSWORD_LABEL), 'Nouveau124')
    await submitReset(user)
    expect(await screen.findByText(/Les mots de passe ne correspondent pas/)).toBeInTheDocument()
    expect(vi.mocked(api.resetPassword)).not.toHaveBeenCalled()
  })

  it('affiche l’erreur de force du mot de passe trop faible à la soumission', async () => {
    vi.mocked(api.resetPassword).mockResolvedValue(undefined)
    const { user } = renderAtReset()
    await user.type(screen.getByLabelText(NEW_PASSWORD_LABEL), 'court')
    await user.type(screen.getByLabelText(CONFIRM_PASSWORD_LABEL), 'court')
    await submitReset(user)
    expect(await screen.findByText(/entre 10 et 72 caractères/)).toBeInTheDocument()
    expect(vi.mocked(api.resetPassword)).not.toHaveBeenCalled()
  })

  it('affiche l’état dédié « lien expiré ou déjà utilisé » (409) avec retour vers /forgot', async () => {
    vi.mocked(api.resetPassword).mockRejectedValue(
      new ApiError(409, 'PASSWORD_RESET_CONSUMED', 'Ce lien a déjà été utilisé.', 'req-9'),
    )
    const { user } = renderAtReset()
    await user.type(screen.getByLabelText(NEW_PASSWORD_LABEL), 'Nouveau123')
    await user.type(screen.getByLabelText(CONFIRM_PASSWORD_LABEL), 'Nouveau123')
    await submitReset(user)
    expect(await screen.findByText('Ce lien a expiré ou a déjà été utilisé.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Demander un nouveau lien/ })).toHaveAttribute('href', '/forgot')
  })

  it('refuse un lien manquant (pas de token en query string)', () => {
    renderAtReset('/reset')
    expect(screen.getByText(/Ce lien est manquant ou invalide/)).toBeInTheDocument()
    expect(vi.mocked(api.resetPassword)).not.toHaveBeenCalled()
  })
})
