'use client'

interface AcclaimProgressProps {
  status: 'published' | 'acclaimed'
  reviewCount: number
  acclaimCount: number
  eligibility: {
    eligible: boolean
    reason: string
  }
}

export function AcclaimProgress({
  status,
  reviewCount,
  acclaimCount,
  eligibility,
}: AcclaimProgressProps) {
  // Already acclaimed - show celebration state
  if (status === 'acclaimed') {
    return (
      <div className="glass-cyan p-4">
        <div className="flex items-center gap-3">
          <span className="text-xl">✨</span>
          <div>
            <h3 className="text-neon-green font-display text-sm tracking-wider">ACCLAIMED</h3>
            <p className="text-text-secondary text-xs mt-1">
              This story has been recognized by the community
            </p>
          </div>
        </div>
        <div className="mt-3 text-xs text-text-tertiary font-mono">
          {acclaimCount} acclaim recommendations • All reviews responded
        </div>
      </div>
    )
  }

  // Calculate progress
  const neededAcclaim = 2
  const acclaimProgress = Math.min(acclaimCount / neededAcclaim, 1)

  // No reviews yet
  if (reviewCount === 0) {
    return (
      <div className="glass p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-text-secondary font-display text-sm tracking-wider">ACCLAIM PROGRESS</h3>
        </div>
        <div className="h-2 bg-white/10 overflow-hidden mb-3">
          <div className="h-full bg-white/20 w-0" />
        </div>
        <p className="text-text-tertiary text-xs">
          No reviews yet. Need: {neededAcclaim} acclaim recommendations + author responses to all reviews
        </p>
      </div>
    )
  }

  // Has reviews but not enough acclaim
  if (acclaimCount < neededAcclaim) {
    return (
      <div className="glass p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-text-secondary font-display text-sm tracking-wider">ACCLAIM PROGRESS</h3>
          <span className="text-xs font-mono text-neon-cyan">{acclaimCount}/{neededAcclaim}</span>
        </div>
        <div className="h-2 bg-white/10 overflow-hidden mb-3">
          <div
            className="h-full bg-neon-cyan transition-all duration-500"
            style={{ width: `${acclaimProgress * 100}%` }}
          />
        </div>
        <p className="text-text-tertiary text-xs">
          {reviewCount} reviews • {acclaimCount} recommend acclaim
        </p>
      </div>
    )
  }

  // Enough acclaim but not eligible (pending author responses)
  return (
    <div className="glass p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-text-secondary font-display text-sm tracking-wider">ACCLAIM PROGRESS</h3>
        <span className="text-xs font-mono text-neon-cyan">{acclaimCount}/{neededAcclaim}</span>
      </div>
      <div className="h-2 bg-white/10 overflow-hidden mb-3">
        <div
          className="h-full bg-neon-cyan/80 transition-all duration-500"
          style={{ width: `${acclaimProgress * 100}%` }}
        />
      </div>
      <p className="text-neon-amber text-xs">
        {eligibility.reason}
      </p>
    </div>
  )
}
