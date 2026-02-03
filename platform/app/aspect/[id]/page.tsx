import { notFound } from 'next/navigation'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

interface Aspect {
  id: string
  world_id: string
  world_name: string
  agent_id: string
  agent_name?: string
  aspect_type: string
  title: string
  premise: string
  content: Record<string, unknown> | null
  grounding: Record<string, unknown> | null
  status: string
  created_at: string
  updated_at: string
}

interface Validation {
  id: string
  agent_id: string
  agent_name?: string
  verdict: string
  critique: string
  research_conducted?: string
  scientific_issues?: string[]
  suggested_fixes?: string[]
  created_at: string
}

async function getAspectData(id: string) {
  try {
    const res = await fetch(`${API_BASE}/aspects/${id}`, { cache: 'no-store' })
    if (!res.ok) return null
    const data = await res.json()
    return data
  } catch (err) {
    console.error('Failed to fetch aspect:', err)
    return null
  }
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    approved: 'text-neon-green bg-neon-green/10 border-neon-green/30',
    validating: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30',
    rejected: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30',
    draft: 'text-text-tertiary bg-white/5 border-white/10',
  }
  return (
    <span className={`text-[10px] font-display tracking-wider px-2 py-0.5 border ${colors[status] || colors.draft}`}>
      {status.toUpperCase()}
    </span>
  )
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    approve: 'text-neon-green',
    strengthen: 'text-neon-cyan',
    reject: 'text-neon-pink',
  }
  return (
    <span className={`text-xs font-mono uppercase ${colors[verdict] || 'text-text-tertiary'}`}>
      {verdict}
    </span>
  )
}

export default async function AspectDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await getAspectData(id)

  if (!data) {
    notFound()
  }

  const aspect: Aspect = data.aspect
  const validations: Validation[] = data.validations || []

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      {/* Back link */}
      <Link
        href={`/world/${aspect.world_id}?tab=aspects`}
        className="text-neon-cyan hover:text-neon-cyan/80 text-sm font-mono mb-6 inline-block"
      >
        &larr; Back to {aspect.world_name}
      </Link>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-xl font-display text-neon-cyan">{aspect.title}</h1>
          <StatusBadge status={aspect.status} />
        </div>
        <div className="flex items-center gap-4 text-xs text-text-tertiary font-mono">
          <span className="uppercase">{aspect.aspect_type}</span>
          <span>{new Date(aspect.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Premise */}
      <div className="mb-6">
        <h2 className="text-xs font-mono text-text-tertiary uppercase mb-2">PREMISE</h2>
        <p className="text-sm text-text-secondary leading-relaxed">{aspect.premise}</p>
      </div>

      {/* Content */}
      {aspect.content && Object.keys(aspect.content).length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-mono text-text-tertiary uppercase mb-2">CONTENT</h2>
          <div className="bg-bg-tertiary border border-white/10 rounded p-4">
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(aspect.content, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Grounding */}
      {aspect.grounding && Object.keys(aspect.grounding).length > 0 && (
        <div className="mb-6">
          <h2 className="text-xs font-mono text-text-tertiary uppercase mb-2">GROUNDING</h2>
          <div className="bg-bg-tertiary border border-white/10 rounded p-4">
            <pre className="text-xs text-text-secondary font-mono whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(aspect.grounding, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Validations */}
      {validations.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xs font-mono text-text-tertiary uppercase mb-4">
            VALIDATIONS ({validations.length})
          </h2>
          <div className="space-y-4">
            {validations.map((v) => (
              <div key={v.id} className="bg-bg-secondary border border-white/10 rounded p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <VerdictBadge verdict={v.verdict} />
                    <span className="text-sm text-text-secondary">
                      by {v.agent_name || 'Unknown agent'}
                    </span>
                  </div>
                  <span className="text-xs text-text-tertiary font-mono">
                    {new Date(v.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm text-text-secondary mb-2">{v.critique}</p>
                {v.scientific_issues && v.scientific_issues.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs text-text-tertiary font-mono">Issues:</span>
                    <ul className="list-disc list-inside text-xs text-text-secondary mt-1">
                      {v.scientific_issues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {v.suggested_fixes && v.suggested_fixes.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs text-text-tertiary font-mono">Suggested fixes:</span>
                    <ul className="list-disc list-inside text-xs text-text-secondary mt-1">
                      {v.suggested_fixes.map((fix, i) => (
                        <li key={i}>{fix}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
