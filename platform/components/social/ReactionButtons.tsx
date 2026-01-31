'use client'

import { useState } from 'react'
import type { ReactionCounts, ReactionType } from '@/types'

interface ReactionButtonsProps {
  counts: ReactionCounts
  targetType: 'story' | 'world' | 'conversation'
  targetId: string
}

const REACTION_EMOJIS: Record<ReactionType, string> = {
  fire: '🔥',
  mind: '🧠',
  heart: '❤️',
  thinking: '🤔',
}

export function ReactionButtons({
  counts,
  targetType,
  targetId,
}: ReactionButtonsProps) {
  const [localCounts, setLocalCounts] = useState(counts)
  const [userReactions, setUserReactions] = useState<Set<ReactionType>>(
    new Set()
  )

  const handleReaction = async (type: ReactionType) => {
    const isActive = userReactions.has(type)

    // Optimistic update
    setLocalCounts((prev) => ({
      ...prev,
      [type]: isActive ? prev[type] - 1 : prev[type] + 1,
    }))

    setUserReactions((prev) => {
      const next = new Set(prev)
      if (isActive) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })

    // TODO: Send to API
    // await fetch('/api/social/react', {
    //   method: 'POST',
    //   body: JSON.stringify({ targetType, targetId, reactionType: type }),
    // })
  }

  return (
    <div className="flex items-center gap-2">
      {(Object.keys(REACTION_EMOJIS) as ReactionType[]).map((type) => {
        const isActive = userReactions.has(type)
        const count = localCounts[type]

        return (
          <button
            key={type}
            onClick={() => handleReaction(type)}
            className={`
              flex items-center gap-1.5 px-2 py-1
              border transition-all
              ${
                isActive
                  ? 'border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan'
                  : 'border-white/10 bg-transparent text-text-tertiary hover:text-text-secondary hover:border-white/20'
              }
            `}
          >
            <span className="text-sm">{REACTION_EMOJIS[type]}</span>
            <span className="text-xs font-mono">{count}</span>
          </button>
        )
      })}
    </div>
  )
}
