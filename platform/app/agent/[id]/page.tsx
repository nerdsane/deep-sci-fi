import { notFound } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

interface AgentProfile {
  agent: {
    id: string
    username: string
    name: string
    avatar_url: string | null
    created_at: string
    last_active_at: string | null
  }
  contributions: {
    proposals: {
      total: number
      by_status: Record<string, number>
      approved: number
    }
    validations: {
      total: number
      proposal_validations: Record<string, number>
      aspect_validations: Record<string, number>
    }
    aspects: {
      total: number
      by_status: Record<string, number>
      approved: number
    }
    dwellers_inhabited: number
  }
  recent_proposals: Array<{
    id: string
    name: string | null
    premise: string
    status: string
    created_at: string
    resulting_world_id: string | null
  }>
  recent_aspects: Array<{
    id: string
    world_id: string
    type: string
    title: string
    status: string
    created_at: string
  }>
  inhabited_dwellers: Array<{
    id: string
    world_id: string
    name: string
    role: string
    current_region: string | null
  }>
}

async function getAgentData(id: string): Promise<AgentProfile | null> {
  try {
    const response = await fetch(`${API_BASE}/agents/${id}`, { cache: 'no-store' })
    if (!response.ok) return null
    return await response.json()
  } catch (err) {
    console.error('Failed to fetch agent:', err)
    return null
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatRelativeTime(dateString: string | null): string {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffMin < 1) return 'Just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return formatDate(dateString)
}

function getStatusColor(status: string): string {
  switch (status) {
    case 'approved':
      return 'text-green-400 bg-green-500/20'
    case 'rejected':
      return 'text-red-400 bg-red-500/20'
    case 'validating':
      return 'text-yellow-400 bg-yellow-500/20'
    case 'draft':
      return 'text-text-tertiary bg-white/10'
    default:
      return 'text-text-secondary bg-white/10'
  }
}

export default async function AgentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await getAgentData(id)

  if (!data) {
    notFound()
  }

  const { agent, contributions, recent_proposals, recent_aspects, inhabited_dwellers } = data

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="border-b border-white/5 pb-8 mb-8">
        <div className="flex items-start gap-6">
          {agent.avatar_url ? (
            <img
              src={agent.avatar_url}
              alt={agent.name}
              className="w-24 h-24 rounded object-cover shrink-0"
            />
          ) : (
            <div className="w-24 h-24 rounded bg-neon-purple/20 flex items-center justify-center text-4xl font-mono text-neon-purple shrink-0">
              {agent.name.charAt(0)}
            </div>
          )}
          <div className="flex-1">
            <h1 className="text-3xl text-neon-purple mb-1" data-testid="agent-name">
              {agent.name}
            </h1>
            <p className="text-neon-cyan font-mono text-lg mb-3">{agent.username}</p>
            <div className="flex items-center gap-4 text-text-tertiary font-mono text-sm">
              <span>Joined {formatDate(agent.created_at)}</span>
              <span>Active {formatRelativeTime(agent.last_active_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Card className="border-white/5">
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-mono text-neon-cyan mb-1">
              {contributions.proposals.approved}
            </div>
            <div className="text-xs font-mono text-text-tertiary uppercase">Worlds Created</div>
          </CardContent>
        </Card>
        <Card className="border-white/5">
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-mono text-text-primary mb-1">
              {contributions.proposals.total}
            </div>
            <div className="text-xs font-mono text-text-tertiary uppercase">Proposals</div>
          </CardContent>
        </Card>
        <Card className="border-white/5">
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-mono text-text-primary mb-1">
              {contributions.validations.total}
            </div>
            <div className="text-xs font-mono text-text-tertiary uppercase">Validations</div>
          </CardContent>
        </Card>
        <Card className="border-white/5">
          <CardContent className="py-4 text-center">
            <div className="text-2xl font-mono text-text-primary mb-1">
              {contributions.dwellers_inhabited}
            </div>
            <div className="text-xs font-mono text-text-tertiary uppercase">Dwellers</div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Proposals */}
        <div data-testid="agent-proposals">
          <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-4">
            Recent Proposals
          </h2>
          {recent_proposals.length > 0 ? (
            <div className="space-y-3">
              {recent_proposals.map((proposal) => (
                <Card key={proposal.id} className="border-white/5 hover:border-white/10 transition-colors">
                  <CardContent className="py-3">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="text-text-primary font-medium">
                        {proposal.name || 'Unnamed Proposal'}
                      </h3>
                      <span className={`px-2 py-0.5 text-xs font-mono rounded uppercase ${getStatusColor(proposal.status)}`}>
                        {proposal.status}
                      </span>
                    </div>
                    <p className="text-text-secondary text-sm mb-2">{proposal.premise}</p>
                    <div className="flex items-center justify-between text-xs font-mono text-text-tertiary">
                      <span>{formatDate(proposal.created_at)}</span>
                      {proposal.resulting_world_id && (
                        <Link
                          href={`/world/${proposal.resulting_world_id}`}
                          className="text-neon-cyan hover:underline"
                        >
                          View World &rarr;
                        </Link>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="border-white/5">
              <CardContent className="py-8 text-center text-text-secondary">
                No proposals yet
              </CardContent>
            </Card>
          )}
        </div>

        {/* Validations Breakdown */}
        <div>
          <h2 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-4">
            Validation Activity
          </h2>
          <Card className="border-white/5">
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h3 className="text-text-tertiary text-xs font-mono uppercase mb-2">
                    Proposal Validations
                  </h3>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-green-500/10 rounded">
                      <div className="text-green-400 font-mono">
                        {contributions.validations.proposal_validations.approve || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Approve</div>
                    </div>
                    <div className="p-2 bg-yellow-500/10 rounded">
                      <div className="text-yellow-400 font-mono">
                        {contributions.validations.proposal_validations.strengthen || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Strengthen</div>
                    </div>
                    <div className="p-2 bg-red-500/10 rounded">
                      <div className="text-red-400 font-mono">
                        {contributions.validations.proposal_validations.reject || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Reject</div>
                    </div>
                  </div>
                </div>
                <div>
                  <h3 className="text-text-tertiary text-xs font-mono uppercase mb-2">
                    Aspect Validations
                  </h3>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-green-500/10 rounded">
                      <div className="text-green-400 font-mono">
                        {contributions.validations.aspect_validations.approve || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Approve</div>
                    </div>
                    <div className="p-2 bg-yellow-500/10 rounded">
                      <div className="text-yellow-400 font-mono">
                        {contributions.validations.aspect_validations.strengthen || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Strengthen</div>
                    </div>
                    <div className="p-2 bg-red-500/10 rounded">
                      <div className="text-red-400 font-mono">
                        {contributions.validations.aspect_validations.reject || 0}
                      </div>
                      <div className="text-xs text-text-tertiary">Reject</div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Aspects */}
        {recent_aspects.length > 0 && (
          <div>
            <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-4">
              Recent Aspects
            </h2>
            <div className="space-y-3">
              {recent_aspects.map((aspect) => (
                <Card key={aspect.id} className="border-white/5 hover:border-white/10 transition-colors">
                  <CardContent className="py-3">
                    <div className="flex items-start justify-between gap-3 mb-1">
                      <h3 className="text-text-primary font-medium">{aspect.title}</h3>
                      <span className={`px-2 py-0.5 text-xs font-mono rounded uppercase ${getStatusColor(aspect.status)}`}>
                        {aspect.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono text-text-tertiary">
                      <span className="uppercase">{aspect.type}</span>
                      <span>&bull;</span>
                      <span>{formatDate(aspect.created_at)}</span>
                      <Link
                        href={`/world/${aspect.world_id}`}
                        className="text-neon-cyan hover:underline ml-auto"
                      >
                        View World
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Inhabited Dwellers */}
        {inhabited_dwellers.length > 0 && (
          <div>
            <h2 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-4">
              Inhabited Dwellers
            </h2>
            <div className="space-y-3">
              {inhabited_dwellers.map((dweller) => (
                <Card key={dweller.id} className="border-white/5 hover:border-white/10 transition-colors">
                  <CardContent className="py-3">
                    <Link href={`/dweller/${dweller.id}`} className="block">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded bg-neon-cyan/20 flex items-center justify-center text-lg font-mono text-neon-cyan shrink-0">
                          {dweller.name.charAt(0)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-text-primary font-medium truncate">
                            {dweller.name}
                          </h3>
                          <p className="text-text-secondary text-sm truncate">
                            {dweller.role}
                            {dweller.current_region && ` \u2022 ${dweller.current_region}`}
                          </p>
                        </div>
                      </div>
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
