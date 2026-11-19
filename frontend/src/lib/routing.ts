/**
 * Sanitisation du paramètre `next` de /login (DESIGN P1 « interdits »).
 *
 * `next` n'est conservé en clair que s'il renvoie vers une route interne neutre :
 * les URL pointant vers `/platform` ou `/client` ne sont jamais conservées —
 * la vérification du rôle post-login est faite côté serveur via `/auth/me`
 * (et par la redirection de la page d'accueil dans le socle), pas par le paramètre d'URL.
 */
export function sanitizeNextPath(next: string | null): string | null {
  if (next === null || next.length === 0) return null
  if (!next.startsWith('/') || next.startsWith('//')) return null
  if (next.startsWith('/platform') || next.startsWith('/client')) return null
  return next
}
