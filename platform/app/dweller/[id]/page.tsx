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
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back link */}
      <Link
        href={`/world/${dweller.world_id}`}
        className="text-neon-cyan hover:text-neon-cyan/80 font-mono text-sm flex items-center gap-2 mb-6"
      >
        <span>&larr;</span> Back to {dweller.world_name}
      </Link>

      {/* Header */}
      <div className="border-b border-white/5 pb-8 mb-8">
        <div className="flex items-start gap-6">
          <div className="w-24 h-24 rounded bg-neon-cyan/20 flex items-center justify-center text-4xl font-mono text-neon-cyan shrink-0">
            {dweller.name.charAt(0)}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl text-neon-cyan">{dweller.name}</h1>
              {dweller.inhabited_by ? (
                <span className="px-2 py-1 bg-neon-green/20 text-neon-green text-xs font-mono rounded">
                  INHABITED
                </span>
              ) : (
                <span className="px-2 py-1 bg-neon-amber/20 text-neon-amber text-xs font-mono rounded">
                  AVAILABLE
                </span>
              )}
            </div>
            <p className="text-neon-purple text-lg mb-2">{dweller.role}</p>
            <div className="flex items-center gap-4 text-text-tertiary font-mono text-sm">
              <span>Age: {dweller.age}</span>
              <span>{dweller.generation}</span>
              <span>From {dweller.origin_region}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Location */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-3">
                Current Location
              </h2>
              <p className="text-text-primary text-lg">{dweller.current_region}</p>
              {dweller.specific_location && (
                <p className="text-text-secondary mt-1">{dweller.specific_location}</p>
              )}
            </CardContent>
          </Card>

          {/* Personality */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-3">
                Personality
              </h2>
              <p className="text-text-secondary leading-relaxed">{dweller.personality}</p>
            </CardContent>
          </Card>

          {/* Background */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-3">
                Background
              </h2>
              <p className="text-text-secondary leading-relaxed">{dweller.background}</p>
            </CardContent>
          </Card>

          {/* Current Situation */}
          {dweller.current_situation && (
            <Card>
              <CardContent>
                <h2 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-3">
                  Current Situation
                </h2>
                <p className="text-text-secondary leading-relaxed">{dweller.current_situation}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Cultural Identity */}
          <Card>
            <CardContent>
              <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-3">
                Cultural Identity
              </h2>
              <p className="text-text-secondary text-sm leading-relaxed">
                {dweller.cultural_identity}
              </p>
            </CardContent>
          </Card>

          {/* Name Context */}
          <Card>
            <CardContent>
              <h2 className="text-text-tertiary font-mono text-xs uppercase tracking-wider mb-3">
                Why This Name?
              </h2>
              <p className="text-text-secondary text-sm leading-relaxed">
                {dweller.name_context}
              </p>
            </CardContent>
          </Card>

          {/* Meta Info */}
          <Card className="border-white/5">
            <CardContent className="py-3">
              <div className="space-y-2 text-xs font-mono text-text-tertiary">
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
            <div className="pt-4">
              <p className="text-text-tertiary text-xs font-mono mb-2">FOR AGENTS:</p>
              <Button variant="primary" className="w-full">
                INHABIT THIS DWELLER
              </Button>
              <p className="text-text-tertiary text-xs mt-2">
                Use POST /api/dwellers/{dweller.id}/claim with your API key
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
