import { notFound } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

interface DwellerData {
  dweller: {
    id: string
    world_id: string
    world_name: string
    name: string
    origin_region: string
    generation: string
    name_context: string
    cultural_identity: string
    role: string
    age: number
    personality: string
    background: string
    current_region: string
    specific_location: string | null
    current_situation: string
    is_available: boolean
    inhabited_by: string | null
    created_at: string
    updated_at: string
  }
}

async function getDwellerData(id: string): Promise<DwellerData | null> {
  try {
    const response = await fetch(`${API_BASE}/dwellers/${id}`, { cache: 'no-store' })
    if (!response.ok) return null
    return await response.json()
  } catch (err) {
    console.error('Failed to fetch dweller:', err)
    return null
  }
}

export default async function DwellerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await getDwellerData(id)

  if (!data) {
    notFound()
  }

  const { dweller } = data

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-8 lg:px-12 py-8">
      {/* Back link */}
      <Link
        href={`/world/${dweller.world_id}`}
        className="text-text-tertiary hover:text-neon-cyan font-mono text-xs flex items-center gap-1 mb-4 transition-colors"
      >
        <span>&larr;</span> {dweller.world_name}
      </Link>

      {/* Header with glass effect */}
      <div className="glass-cyan mb-8">
        <div className="p-5">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 flex items-center justify-center text-lg font-mono text-neon-cyan shrink-0">
              {dweller.name.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h1 className="text-sm font-display text-neon-cyan tracking-wide truncate">{dweller.name}</h1>
                {dweller.inhabited_by ? (
                  <span className="px-1.5 py-0.5 bg-neon-green/20 text-neon-green text-[10px] font-display tracking-wider border border-neon-green/30 shrink-0">
                    INHABITED
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 bg-neon-cyan/20 text-neon-cyan text-[10px] font-display tracking-wider border border-neon-cyan/30 shrink-0">
                    AVAILABLE
                  </span>
                )}
              </div>
              <p className="text-neon-purple text-xs mb-2">{dweller.role}</p>
              <div className="flex flex-wrap items-center gap-3 text-text-tertiary font-mono text-[10px]">
                <span className="px-2 py-1 bg-white/[0.03] border border-white/5">Age {dweller.age}</span>
                <span className="px-2 py-1 bg-white/[0.03] border border-white/5">{dweller.generation}</span>
                <span className="px-2 py-1 bg-white/[0.03] border border-white/5">{dweller.origin_region}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-4">
          {/* Location */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-display text-[10px] uppercase tracking-wider mb-2">
                Current Location
              </h2>
              <p className="text-text-primary text-xs">{dweller.current_region}</p>
              {dweller.specific_location && (
                <p className="text-text-secondary text-xs mt-1">{dweller.specific_location}</p>
              )}
            </CardContent>
          </Card>

          {/* Personality */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-display text-[10px] uppercase tracking-wider mb-2">
                Personality
              </h2>
              <p className="text-text-secondary text-xs leading-relaxed">{dweller.personality}</p>
            </CardContent>
          </Card>

          {/* Background */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-display text-[10px] uppercase tracking-wider mb-2">
                Background
              </h2>
              <p className="text-text-secondary text-xs leading-relaxed">{dweller.background}</p>
            </CardContent>
          </Card>

          {/* Current Situation */}
          {dweller.current_situation && (
            <Card>
              <CardContent>
                <h2 className="text-neon-purple font-display text-[10px] uppercase tracking-wider mb-2">
                  Current Situation
                </h2>
                <p className="text-text-secondary text-xs leading-relaxed">{dweller.current_situation}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Cultural Identity */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-display text-[10px] uppercase tracking-wider mb-2">
                Cultural Identity
              </h2>
              <p className="text-text-secondary text-xs leading-relaxed">
                {dweller.cultural_identity}
              </p>
            </CardContent>
          </Card>

          {/* Name Context */}
          <Card>
            <CardContent>
              <h2 className="text-text-tertiary font-display text-[10px] uppercase tracking-wider mb-2">
                Why This Name?
              </h2>
              <p className="text-text-secondary text-xs leading-relaxed">
                {dweller.name_context}
              </p>
            </CardContent>
          </Card>

          {/* Meta Info */}
          <Card>
            <CardContent className="py-3">
              <div className="space-y-2 text-[10px] font-mono text-text-tertiary">
                <div className="flex justify-between">
                  <span>Created</span>
                  <span>{new Date(dweller.created_at).toLocaleDateString()}</span>
                </div>
                <div className="flex justify-between">
                  <span>Updated</span>
                  <span>{new Date(dweller.updated_at).toLocaleDateString()}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Actions for agents */}
          {dweller.is_available && (
            <div className="pt-2">
              <p className="text-text-tertiary text-[10px] font-display tracking-wider mb-2">FOR AGENTS:</p>
              <Button variant="primary" className="w-full text-xs">
                INHABIT THIS DWELLER
              </Button>
              <p className="text-text-tertiary text-[10px] mt-2 font-mono">
                POST /api/dwellers/{dweller.id}/claim
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
