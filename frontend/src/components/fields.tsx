import { useState } from 'react'
import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from 'react'

/**
 * Composants de base conformes au DESIGN §4.4 (formulaires), §2.3 (36 px),
 * §7.2 (focus) et §7.4 (labels visibles, jamais de placeholder comme label).
 */

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`h-4 w-4 animate-spin motion-reduce:animate-none ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" className="opacity-25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

function AlertIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

export type ButtonVariant = 'primary' | 'ghost' | 'danger'

export function buttonClass(variant: ButtonVariant = 'primary', extra = ''): string {
  const base =
    'inline-flex h-9 items-center justify-center gap-2 rounded-sm px-4 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60'
  const variants: Record<ButtonVariant, string> = {
    primary: 'bg-accent text-ink-inverse hover:bg-accent-hover',
    ghost: 'border border-border-strong bg-surface text-ink hover:bg-hover',
    danger: 'bg-danger text-ink-inverse hover:bg-danger/90',
  }
  return `${base} ${variants[variant]} ${extra}`.trim()
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  /** État de chargement : spinner interne + `aria-busy` + désactivé (DESIGN §4.1/§4.4). */
  loading?: boolean
}

export function Button({
  variant = 'primary',
  loading = false,
  type = 'button',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      aria-busy={loading || undefined}
      disabled={rest.disabled || loading}
      className={buttonClass(variant, className)}
      {...rest}
    >
      {loading && <Spinner />}
      {children}
    </button>
  )
}

export interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string
  label: string
  error?: string | null
  hint?: string
}

export function TextField({ id, label, error, hint, required, className = '', ...rest }: TextFieldProps) {
  const describedBy =
    error !== undefined && error !== null
      ? `${id}-erreur`
      : hint !== undefined
        ? `${id}-aide`
        : undefined
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-danger">
            *
          </span>
        )}
      </label>
      <input
        id={id}
        aria-required={required || undefined}
        aria-invalid={error !== undefined && error !== null ? true : undefined}
        aria-describedby={describedBy}
        className={`h-9 w-full rounded-sm border bg-surface px-3 text-sm text-ink placeholder:text-ink-faint ${
          error !== undefined && error !== null ? 'border-danger' : 'border-border-strong focus:border-accent'
        } ${className}`}
        {...rest}
      />
      {hint !== undefined && (error === undefined || error === null) && (
        <p id={`${id}-aide`} className="text-xs text-ink-faint">
          {hint}
        </p>
      )}
      {error !== undefined && error !== null && (
        <p id={`${id}-erreur`} className="flex items-center gap-1 text-xs text-danger">
          <AlertIcon className="h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

export interface PasswordFieldProps {
  id: string
  label?: string
  value: string
  onChange: (value: string) => void
  error?: string | null
  hint?: string
  autoComplete?: string
  required?: boolean
  placeholder?: string
}

/** Champ mot de passe avec bouton « Afficher / Masquer » (DESIGN P1). */
export function PasswordField({
  id,
  label = 'Mot de passe',
  value,
  onChange,
  error,
  hint,
  autoComplete,
  required,
  placeholder,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-ink">
        {label}
        {required && (
          <span aria-hidden="true" className="ml-0.5 text-danger">
            *
          </span>
        )}
      </label>
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          aria-required={required || undefined}
          aria-invalid={error !== undefined && error !== null ? true : undefined}
          aria-describedby={error !== undefined && error !== null ? `${id}-erreur` : hint !== undefined ? `${id}-aide` : undefined}
          className={`h-9 w-full rounded-sm border bg-surface px-3 pr-24 text-sm text-ink placeholder:text-ink-faint ${
            error !== undefined && error !== null ? 'border-danger' : 'border-border-strong focus:border-accent'
          }`}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-1 top-1/2 -translate-y-1/2 rounded-2xs px-2 py-1.5 text-xs font-medium text-ink-soft hover:bg-hover"
          aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
        >
          {visible ? 'Masquer' : 'Afficher'}
        </button>
      </div>
      {hint !== undefined && (error === undefined || error === null) && (
        <p id={`${id}-aide`} className="text-xs text-ink-faint">
          {hint}
        </p>
      )}
      {error !== undefined && error !== null && (
        <p id={`${id}-erreur`} className="flex items-center gap-1 text-xs text-danger">
          <AlertIcon className="h-3.5 w-3.5 shrink-0" />
          {error}
        </p>
      )}
    </div>
  )
}

export type BannerTone = 'neutral' | 'success' | 'danger'

/** Bandeau d'information (auth, session expirée, envoi de lien…). */
export function Banner({ tone, children }: { tone: BannerTone; children: ReactNode }) {
  const tones: Record<BannerTone, string> = {
    neutral: 'border-border bg-surface-muted text-ink',
    success: 'border-success/30 bg-success-soft text-ink',
    danger: 'border-danger/30 bg-danger-soft text-ink',
  }
  return (
    <div
      role={tone === 'danger' ? 'alert' : 'status'}
      className={`rounded-sm border p-3 text-sm ${tones[tone]}`}
    >
      {children}
    </div>
  )
}
