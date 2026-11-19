/**
 * Règles de mot de passe ChainScope (validation côté client, miroir du backend).
 * 10–72 caractères, au moins une minuscule, une majuscule et un chiffre.
 */

const MIN_PASSWORD_LENGTH = 10
const MAX_PASSWORD_LENGTH = 72

/** Renvoie le libellé de l'erreur de force, ou `null` si le mot de passe est valide. */
export function passwordIssue(password: string): string | null {
  if (password.length < MIN_PASSWORD_LENGTH || password.length > MAX_PASSWORD_LENGTH) {
    return `Le mot de passe doit contenir entre ${MIN_PASSWORD_LENGTH} et ${MAX_PASSWORD_LENGTH} caractères.`
  }
  const missing: string[] = []
  if (!/[a-z]/.test(password)) missing.push('une minuscule')
  if (!/[A-Z]/.test(password)) missing.push('une majuscule')
  if (!/\d/.test(password)) missing.push('un chiffre')
  if (missing.length > 0) {
    return `Le mot de passe doit contenir ${missing.join(', ')}.`
  }
  return null
}
