/**
 * Écusson + logotype ChainScope (DESIGN §1.2).
 * Motif : deux maillons entrelacés dont le second s'ouvre en nœud de graphe.
 * Glyphe seul (sans fond), utilisable en mono ; taille minimale 24 px.
 */
export function Wordmark({
  size = 24,
  withText = true,
  muted = false,
  className = '',
}: {
  size?: number
  withText?: boolean
  /** « Écusson filaire » (DESIGN §4.1 états vides) : rendu en encre atténuée. */
  muted?: boolean
  className?: string
}) {
  const ink = muted ? 'text-ink-faint' : 'text-ink'
  const accent = muted ? 'text-ink-faint' : 'text-accent'
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" className="shrink-0">
        {/* Maillon 2 (accent) + nœud de graphe, dessinés en dessous. */}
        <rect x="14" y="11" width="11" height="10" rx="5" strokeWidth="2.5" className={`stroke-current ${accent}`} />
        <circle cx="27" cy="16" r="4" strokeWidth="2.5" className={`stroke-current ${accent}`} />
        {/* Maillon 1 (encre), entrelacé par-dessus au croisement. */}
        <rect x="3" y="11" width="12" height="10" rx="5" strokeWidth="2.5" className={`stroke-current ${ink}`} />
      </svg>
      {withText && (
        <span className="text-2xl font-semibold leading-none tracking-[-0.02em]">
          <span className={ink}>Chain</span>
          <span className={accent}>Scope</span>
        </span>
      )}
    </span>
  )
}
