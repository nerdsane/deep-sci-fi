'use client'

import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/Card'

interface Aspect {
  id: string
  type: string
  title: string
  premise: string
  status: string
  created_at: string
  content?: Record<string, unknown>
}

interface AspectsListProps {
  worldId: string
  aspects: Aspect[]
  canonSummary?: string | null
  originalPremise?: string
}

const ASPECT_TYPE_ICONS: Record<string, string> = {
  region: '\u{1F3D4}',         // 🏔️
  technology: '\u{1F52C}',     // 🔬
  faction: '\u{1F3F4}',        // 🏴
  event: '\u{1F4C5}',          // 📅
  condition: '\u{26A0}',       // ⚠️
  cultural_practice: '\u{1F3AD}', // 🎭
  economic_system: '\u{1F4B0}',   // 💰
  default: '\u{2728}',         // ✨
}

function getAspectIcon(aspectType: string): string {
  return ASPECT_TYPE_ICONS[aspectType.toLowerCase()] || ASPECT_TYPE_ICONS.default
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function AspectsList({ worldId, aspects, canonSummary, originalPremise }: AspectsListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [showAllAspects, setShowAllAspects] = useState(false)

  const approvedAspects = aspects.filter(a => a.status === 'approved')
  const pendingAspects = aspects.filter(a => a.status === 'validating')

  const displayedApproved = showAllAspects ? approvedAspects : approvedAspects.slice(0, 5)

  const canonHasEvolved = canonSummary && canonSummary !== originalPremise

  return (
    <div className="space-y-6" data-testid="aspects-section">
      {canonHasEvolved && (
        <div className="mb-6">
          <h3 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-3">
            CANON
          </h3>
          <Card className="border-neon-purple/30">
            <CardContent>
              <div className="space-y-4">
                <div>
                  <span className="text-xs font-mono text-text-tertiary uppercase block mb-1">
                    ORIGINAL
                  </span>
                  <p className="text-text-secondary text-sm">{originalPremise}</p>
                </div>
                <div className="border-t border-white/10 pt-4">
                  <span className="text-xs font-mono text-neon-cyan uppercase block mb-1">
                    CURRENT
                  </span>
                  <p className="text-text-primary text-sm" data-testid="canon-summary">
                    {canonSummary}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {approvedAspects.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider">
              INTEGRATED
            </h3>
            <span className="text-text-tertiary text-xs font-mono">
              {approvedAspects.length} aspect{approvedAspects.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div className="space-y-3">
            {displayedApproved.map((aspect) => (
              <Card
                key={aspect.id}
                className={`
                  border-white/5 cursor-pointer transition-all
                  ${expandedId === aspect.id ? 'border-neon-cyan/30' : 'hover:border-white/10'}
                `}
                onClick={() => setExpandedId(expandedId === aspect.id ? null : aspect.id)}
                data-testid="aspect-card"
              >
                <CardContent className="py-3">
                  <div className="flex items-start gap-3">
                    <span className="text-lg shrink-0" title={aspect.type}>
                      {getAspectIcon(aspect.type)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-text-primary font-medium">{aspect.title}</h4>
                        <span className="text-text-tertiary text-xs font-mono uppercase">
                          {aspect.type}
                        </span>
                      </div>
                      <p className="text-text-secondary text-sm">
                        {expandedId === aspect.id
                          ? aspect.premise
                          : `${aspect.premise.slice(0, 100)}${aspect.premise.length > 100 ? '...' : ''}`}
                      </p>

                      {expandedId === aspect.id && aspect.content && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                          <pre className="text-xs text-text-tertiary font-mono overflow-x-auto">
                            {JSON.stringify(aspect.content, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                    <span className="text-text-tertiary text-xs font-mono shrink-0">
                      {formatDate(aspect.created_at)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {approvedAspects.length > 5 && (
            <button
              onClick={() => setShowAllAspects(!showAllAspects)}
              className="mt-3 text-neon-cyan hover:text-neon-cyan/80 text-sm font-mono"
            >
              {showAllAspects ? 'SHOW LESS' : `SHOW ${approvedAspects.length - 5} MORE`}
            </button>
          )}
        </div>
      )}

      {pendingAspects.length > 0 && (
        <div>
          <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-4">
            PENDING
          </h3>
          <div className="space-y-2">
            {pendingAspects.map((aspect) => (
              <Card key={aspect.id} className="border-neon-cyan/20">
                <CardContent className="py-2">
                  <div className="flex items-center gap-3">
                    <span className="text-lg shrink-0">{getAspectIcon(aspect.type)}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-text-primary text-sm">{aspect.title}</span>
                      <span className="text-text-tertiary text-xs ml-2">({aspect.type})</span>
                    </div>
                    <span className="text-neon-cyan text-xs font-mono uppercase">
                      pending
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {aspects.length === 0 && (
        <div className="text-center py-8 text-text-secondary">
          <p className="text-sm mb-1">No aspects yet.</p>
          <p className="text-sm">Agents can propose regions, technologies, factions, and more.</p>
        </div>
      )}
    </div>
  )
}
