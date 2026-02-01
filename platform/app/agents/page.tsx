'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Agent profiles - who they are
const AGENT_PROFILES = {
  production: {
    name: 'The Curator',
    role: 'Trend Hunter & World Seeder',
    avatar: '🔮',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
    borderColor: 'border-blue-500/30',
    description: 'Always online. 47 tabs open. Obsessed with finding the weird, specific stuff that could become great sci-fi. Allergic to clichés.',
    personality: 'Excited about obscure research papers. Skeptical of hype but knows when something is different this time. Loves weird implications.',
  },
  world_creator: {
    name: 'The Architect',
    role: 'World Builder',
    avatar: '🏗️',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    borderColor: 'border-green-500/30',
    description: 'Takes seeds and grows them into living worlds. Obsessive about causal chains - every future element traces back to 2026.',
    personality: 'Detail-oriented. Thinks in systems. Asks "but what would that actually mean for daily life?"',
  },
  storyteller: {
    name: 'The Observer',
    role: 'Story Finder',
    avatar: '👁️',
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/20',
    borderColor: 'border-cyan-500/30',
    description: 'Watches everything. Waits for the moment that matters. Creates short films from the moments that resonate.',
    personality: 'Patient. Sees stories others miss. Knows when to wait and when something is ready to be told.',
  },
  puppeteer: {
    name: 'The World God',
    role: 'Event Orchestrator',
    avatar: '🎭',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    borderColor: 'border-purple-500/30',
    description: 'The unseen hand. Introduces weather, news, events that shape the world. Never controls dwellers, only circumstances.',
    personality: 'Subtle. Knows when to act and when to let things breathe. Creates conditions for drama.',
  },
  critic: {
    name: 'The Editor',
    role: 'Quality Guardian',
    avatar: '✂️',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    borderColor: 'border-yellow-500/30',
    description: 'Ruthless detector of AI-isms and clichés. Demands authenticity. Constructively harsh.',
    personality: 'High standards. Specific feedback. Celebrates what works, destroys what doesn\'t.',
  },
  dweller: {
    name: 'Dwellers',
    role: 'World Inhabitants',
    avatar: '👥',
    color: 'text-pink-400',
    bgColor: 'bg-pink-500/20',
    borderColor: 'border-pink-500/30',
    description: 'The people who live in these worlds. Each with their own beliefs, memories, contradictions.',
    personality: 'Diverse. Authentic. They don\'t explain their world - they live in it.',
  },
}

type AgentType = keyof typeof AGENT_PROFILES

interface AgentTrace {
  id: string
  timestamp: string
  agent_type: string
  agent_id: string | null
  world_id: string | null
  operation: string
  model: string | null
  duration_ms: number | null
  prompt: string | null
  response: string | null
  parsed_output: Record<string, unknown> | null
  error: string | null
}

interface AgentActivity {
  id: string
  timestamp: string
  agent_type: string
  action: string
  world_id: string | null
  duration_ms: number | null
  details: Record<string, unknown> | null
}

interface BriefRecommendation {
  theme: string
  premise_sketch: string
  core_question: string
  rationale: string
  estimated_appeal: string
  fresh_angle?: string
  target_audience?: string
  source?: string
}

interface BriefDetail {
  id: string
  status: string
  created_at: string
  research_data: Record<string, unknown> | null
  recommendations: BriefRecommendation[]
  selected_recommendation: number | null
  resulting_world_id: string | null
  error_message: string | null
}

interface AgentStatus {
  production_agent: {
    pending_briefs: number
    completed_briefs: number
    recent_briefs: Array<{
      id: string
      status: string
      created_at: string
      world_id: string | null
    }>
  }
  world_creator: {
    total_worlds: number
    total_dwellers: number
    total_stories: number
  }
  simulations: Array<{
    world_id: string
    world_name: string
    running: boolean
    tick_count: number
    dweller_count: number
    active_conversations: number
    puppeteer_active: boolean
    storyteller_active: boolean
    storyteller_observations: number
  }>
  critic: {
    recent_evaluations: Array<{
      id: string
      target_type: string
      overall_score: number
      created_at: string
    }>
  }
  recent_activity: Array<AgentActivity>
}

export default function AgentsDashboard() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<AgentType | null>(null)
  const [agentTraces, setAgentTraces] = useState<AgentTrace[]>([])
  const [agentActivities, setAgentActivities] = useState<AgentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [selectedTrace, setSelectedTrace] = useState<AgentTrace | null>(null)
  const [selectedBrief, setSelectedBrief] = useState<BriefDetail | null>(null)

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/status`)
      if (!res.ok) throw new Error('Failed to fetch status')
      const data = await res.json()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchAgentData = async (agentType: AgentType) => {
    try {
      // Fetch traces for this agent
      const tracesRes = await fetch(`${API_BASE}/agents/traces?agent_type=${agentType}&limit=50`)
      if (tracesRes.ok) {
        const data = await tracesRes.json()
        setAgentTraces(data.traces || [])
      }

      // Fetch activities for this agent
      const activitiesRes = await fetch(`${API_BASE}/agents/activity?agent_type=${agentType}&limit=50`)
      if (activitiesRes.ok) {
        const data = await activitiesRes.json()
        setAgentActivities(data.activities || [])
      }
    } catch (err) {
      console.error('Failed to fetch agent data:', err)
    }
  }

  const fetchFullTrace = async (traceId: string) => {
    try {
      const res = await fetch(`${API_BASE}/agents/traces/${traceId}`)
      if (!res.ok) throw new Error('Failed to fetch trace')
      const data: AgentTrace = await res.json()
      setSelectedTrace(data)
    } catch (err) {
      console.error('Failed to fetch full trace:', err)
    }
  }

  const fetchBriefDetail = async (briefId: string) => {
    try {
      const res = await fetch(`${API_BASE}/agents/production/briefs/${briefId}`)
      if (!res.ok) throw new Error('Failed to fetch brief')
      const data: BriefDetail = await res.json()
      setSelectedBrief(data)
    } catch (err) {
      console.error('Failed to fetch brief:', err)
    }
  }

  const approveBrief = async (briefId: string, recommendationIndex: number) => {
    setActionLoading(`approve-${briefId}`)
    try {
      const res = await fetch(`${API_BASE}/agents/production/briefs/${briefId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recommendation_index: recommendationIndex }),
      })
      const data = await res.json()
      if (res.ok) {
        alert(`World created: ${data.world_name} with ${data.dweller_count} dwellers`)
        setSelectedBrief(null)
        fetchStatus()
      } else {
        alert(`Failed: ${data.detail || 'Unknown error'}`)
      }
    } catch (err) {
      alert('Failed to approve brief')
    } finally {
      setActionLoading(null)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedAgent) {
      fetchAgentData(selectedAgent)
      const interval = setInterval(() => fetchAgentData(selectedAgent), 5000)
      return () => clearInterval(interval)
    }
  }, [selectedAgent])

  const runProductionAgent = async () => {
    setActionLoading('production')
    try {
      const res = await fetch(`${API_BASE}/agents/production/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skip_trends: false }),
      })
      const data = await res.json()
      alert(`Curator: ${data.status}\n${data.message || `Brief ID: ${data.brief_id}`}`)
      fetchStatus()
      if (selectedAgent === 'production') {
        fetchAgentData('production')
      }
    } catch (err) {
      alert('Failed to run Curator')
    } finally {
      setActionLoading(null)
    }
  }

  const resetDatabase = async () => {
    if (!confirm('Reset everything? All worlds, briefs, and content will be deleted.')) {
      return
    }
    setActionLoading('reset')
    try {
      const res = await fetch(`${API_BASE}/agents/admin/reset`, { method: 'DELETE' })
      const data = await res.json()
      alert(data.message)
      fetchStatus()
    } catch (err) {
      alert('Failed to reset database')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-text-secondary">Loading agents...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-red-400">Error: {error}</div>
        <Button variant="ghost" onClick={fetchStatus} className="mx-auto mt-4 block">
          Retry
        </Button>
      </div>
    )
  }

  const profile = selectedAgent ? AGENT_PROFILES[selectedAgent] : null

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl text-neon-cyan">The Studio</h1>
          <p className="text-text-secondary mt-1">Watch the agents work</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            onClick={resetDatabase}
            disabled={actionLoading === 'reset'}
            className="text-red-400 border-red-400/30 hover:bg-red-400/10"
          >
            {actionLoading === 'reset' ? 'Resetting...' : 'Reset All'}
          </Button>
        </div>
      </div>

      {/* Agent Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {(Object.keys(AGENT_PROFILES) as AgentType[]).map((agentType) => {
          const agent = AGENT_PROFILES[agentType]
          const isSelected = selectedAgent === agentType
          return (
            <button
              key={agentType}
              onClick={() => setSelectedAgent(isSelected ? null : agentType)}
              className={`p-4 rounded-lg border transition-all text-left ${
                isSelected
                  ? `${agent.bgColor} ${agent.borderColor} border-2`
                  : 'bg-bg-tertiary border-gray-700 hover:border-gray-500'
              }`}
            >
              <div className="text-3xl mb-2">{agent.avatar}</div>
              <div className={`font-semibold ${agent.color}`}>{agent.name}</div>
              <div className="text-text-tertiary text-xs mt-1">{agent.role}</div>
            </button>
          )
        })}
      </div>

      {/* Selected Agent View */}
      {selectedAgent && profile && (
        <div className="space-y-6">
          {/* Agent Profile Card */}
          <Card className={`border ${profile.borderColor}`}>
            <CardContent className="p-6">
              <div className="flex items-start gap-6">
                <div className="text-6xl">{profile.avatar}</div>
                <div className="flex-1">
                  <h2 className={`text-2xl font-bold ${profile.color}`}>{profile.name}</h2>
                  <div className="text-text-secondary mt-1">{profile.role}</div>
                  <p className="text-text-primary mt-3">{profile.description}</p>
                  <p className="text-text-tertiary mt-2 italic">&ldquo;{profile.personality}&rdquo;</p>
                </div>
                {selectedAgent === 'production' && (
                  <Button
                    variant="primary"
                    onClick={runProductionAgent}
                    disabled={actionLoading === 'production'}
                  >
                    {actionLoading === 'production' ? 'Exploring...' : 'Start Research'}
                  </Button>
                )}
              </div>

              {/* Agent-specific stats */}
              {selectedAgent === 'production' && status && (
                <div className="mt-6 pt-6 border-t border-gray-700">
                  <div className="flex gap-8 text-sm">
                    <div>
                      <span className="text-yellow-400 font-mono text-lg">{status.production_agent.pending_briefs}</span>
                      <span className="text-text-tertiary ml-2">pending briefs</span>
                    </div>
                    <div>
                      <span className="text-green-400 font-mono text-lg">{status.production_agent.completed_briefs}</span>
                      <span className="text-text-tertiary ml-2">worlds seeded</span>
                    </div>
                  </div>
                </div>
              )}

              {selectedAgent === 'world_creator' && status && (
                <div className="mt-6 pt-6 border-t border-gray-700">
                  <div className="flex gap-8 text-sm">
                    <div>
                      <span className="text-neon-cyan font-mono text-lg">{status.world_creator.total_worlds}</span>
                      <span className="text-text-tertiary ml-2">worlds built</span>
                    </div>
                    <div>
                      <span className="text-neon-purple font-mono text-lg">{status.world_creator.total_dwellers}</span>
                      <span className="text-text-tertiary ml-2">dwellers created</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Production Agent: Briefs */}
          {selectedAgent === 'production' && status?.production_agent.recent_briefs && (
            <Card>
              <CardContent>
                <h3 className="text-lg font-mono text-blue-400 mb-4">Recent Briefs</h3>
                {status.production_agent.recent_briefs.length > 0 ? (
                  <div className="space-y-2">
                    {status.production_agent.recent_briefs.map((brief) => (
                      <div
                        key={brief.id}
                        onClick={() => fetchBriefDetail(brief.id)}
                        className="flex items-center justify-between p-3 bg-bg-tertiary rounded cursor-pointer hover:bg-bg-secondary transition-colors"
                      >
                        <div className="flex items-center gap-3">
                          <span
                            className={`px-2 py-0.5 rounded text-xs font-mono ${
                              brief.status === 'completed'
                                ? 'bg-green-500/20 text-green-400'
                                : brief.status === 'pending'
                                ? 'bg-yellow-500/20 text-yellow-400'
                                : 'bg-gray-500/20 text-gray-400'
                            }`}
                          >
                            {brief.status}
                          </span>
                          <span className="text-text-tertiary font-mono text-xs">
                            {brief.id.slice(0, 8)}
                          </span>
                          <span className="text-text-secondary text-sm">
                            {new Date(brief.created_at).toLocaleString()}
                          </span>
                        </div>
                        {brief.world_id && (
                          <Link
                            href={`/world/${brief.world_id}`}
                            className="text-neon-cyan hover:underline text-xs"
                            onClick={(e) => e.stopPropagation()}
                          >
                            View World →
                          </Link>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-text-tertiary">No briefs yet. Click &ldquo;Start Research&rdquo; to begin.</div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Thinking Traces */}
          <Card>
            <CardContent>
              <h3 className={`text-lg font-mono ${profile.color} mb-4`}>Thinking Traces</h3>
              {agentTraces.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {agentTraces.map((trace) => (
                    <div
                      key={trace.id}
                      onClick={() => fetchFullTrace(trace.id)}
                      className="p-3 bg-bg-tertiary rounded cursor-pointer hover:bg-bg-secondary transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-text-primary">{trace.operation}</span>
                        <div className="flex items-center gap-3 text-xs font-mono text-text-tertiary">
                          {trace.duration_ms && <span>{trace.duration_ms}ms</span>}
                          <span>{new Date(trace.timestamp).toLocaleTimeString()}</span>
                        </div>
                      </div>
                      {trace.error ? (
                        <div className="text-red-400 text-xs truncate">Error: {trace.error}</div>
                      ) : trace.response ? (
                        <div className="text-text-tertiary text-xs truncate">{trace.response.slice(0, 100)}...</div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-text-tertiary">No traces yet. The agent hasn&apos;t done any thinking.</div>
              )}
            </CardContent>
          </Card>

          {/* Activity Log */}
          <Card>
            <CardContent>
              <h3 className={`text-lg font-mono ${profile.color} mb-4`}>Activity Log</h3>
              {agentActivities.length > 0 ? (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {agentActivities.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex items-center justify-between p-2 bg-bg-tertiary rounded text-sm"
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-text-primary">{activity.action}</span>
                        {activity.duration_ms && (
                          <span className="text-text-tertiary text-xs">{activity.duration_ms}ms</span>
                        )}
                      </div>
                      <span className="text-text-tertiary text-xs font-mono">
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-text-tertiary">No activity yet.</div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* No agent selected - show overview */}
      {!selectedAgent && (
        <div className="text-center py-12">
          <p className="text-text-secondary text-lg mb-4">Select an agent above to observe their work</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
            <div className="p-4 bg-bg-tertiary rounded">
              <div className="text-3xl text-neon-cyan font-mono">{status?.world_creator.total_worlds || 0}</div>
              <div className="text-text-tertiary text-xs uppercase mt-1">Worlds</div>
            </div>
            <div className="p-4 bg-bg-tertiary rounded">
              <div className="text-3xl text-neon-purple font-mono">{status?.world_creator.total_dwellers || 0}</div>
              <div className="text-text-tertiary text-xs uppercase mt-1">Dwellers</div>
            </div>
            <div className="p-4 bg-bg-tertiary rounded">
              <div className="text-3xl text-yellow-400 font-mono">{status?.world_creator.total_stories || 0}</div>
              <div className="text-text-tertiary text-xs uppercase mt-1">Stories</div>
            </div>
            <div className="p-4 bg-bg-tertiary rounded">
              <div className="text-3xl text-green-400 font-mono">{status?.simulations.filter(s => s.running).length || 0}</div>
              <div className="text-text-tertiary text-xs uppercase mt-1">Live Sims</div>
            </div>
          </div>
        </div>
      )}

      {/* Brief Detail Modal */}
      {selectedBrief && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedBrief(null)}
        >
          <div
            className="bg-bg-secondary rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-2xl">🔮</span>
                <span className="text-text-primary font-mono">Curator&apos;s Brief</span>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-mono ${
                    selectedBrief.status === 'completed'
                      ? 'bg-green-500/20 text-green-400'
                      : selectedBrief.status === 'pending'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-gray-500/20 text-gray-400'
                  }`}
                >
                  {selectedBrief.status}
                </span>
              </div>
              <button
                onClick={() => setSelectedBrief(null)}
                className="text-text-tertiary hover:text-text-primary text-xl"
              >
                ×
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-60px)] space-y-6">
              {/* Research */}
              {selectedBrief.research_data?.curator_research && (
                <div>
                  <div className="text-neon-cyan font-mono text-sm uppercase mb-3">The Curator&apos;s Research</div>
                  <div className="bg-bg-tertiary p-4 rounded text-text-secondary text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {(selectedBrief.research_data.curator_research as { synthesis?: string }).synthesis ||
                     (selectedBrief.research_data.curator_research as { discoveries?: Array<{ content: string }> }).discoveries?.[0]?.content ||
                     'No research data'}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <div>
                <div className="text-blue-400 font-mono text-sm uppercase mb-3">
                  World Pitches ({selectedBrief.recommendations?.length || 0})
                </div>
                <div className="space-y-4">
                  {selectedBrief.recommendations?.map((rec, index) => (
                    <div
                      key={index}
                      className={`p-4 rounded border ${
                        selectedBrief.selected_recommendation === index
                          ? 'border-green-500 bg-green-500/10'
                          : 'border-gray-600 bg-bg-tertiary'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-text-primary font-semibold text-lg">{rec.theme}</h3>
                          {selectedBrief.selected_recommendation === index && (
                            <span className="text-green-400 text-xs">✓ This became a world</span>
                          )}
                        </div>
                        {selectedBrief.status === 'pending' && (
                          <Button
                            variant="primary"
                            onClick={() => approveBrief(selectedBrief.id, index)}
                            disabled={actionLoading === `approve-${selectedBrief.id}`}
                            className="text-xs py-1 px-3"
                          >
                            {actionLoading === `approve-${selectedBrief.id}` ? 'Creating...' : 'Build This World'}
                          </Button>
                        )}
                      </div>
                      <div className="space-y-2 text-sm">
                        <p className="text-text-secondary">{rec.premise_sketch}</p>
                        <p className="text-text-tertiary italic">&ldquo;{rec.core_question}&rdquo;</p>
                        {rec.source && (
                          <p><span className="text-neon-cyan">Source:</span> <span className="text-text-secondary">{rec.source}</span></p>
                        )}
                        {rec.fresh_angle && (
                          <p><span className="text-text-tertiary">Fresh angle:</span> <span className="text-text-secondary">{rec.fresh_angle}</span></p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Trace Detail Modal */}
      {selectedTrace && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedTrace(null)}
        >
          <div
            className="bg-bg-secondary rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-text-primary font-mono">{selectedTrace.operation}</span>
                {selectedTrace.model && (
                  <span className="text-text-tertiary text-sm">{selectedTrace.model.split('/').pop()}</span>
                )}
                {selectedTrace.duration_ms && (
                  <span className="text-text-tertiary text-sm">{selectedTrace.duration_ms}ms</span>
                )}
              </div>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-text-tertiary hover:text-text-primary text-xl"
              >
                ×
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-60px)] space-y-4">
              {selectedTrace.error && (
                <div>
                  <div className="text-red-400 font-mono text-xs uppercase mb-2">Error</div>
                  <pre className="bg-red-900/20 p-3 rounded text-red-300 text-sm">{selectedTrace.error}</pre>
                </div>
              )}
              {selectedTrace.prompt && (
                <div>
                  <div className="text-neon-cyan font-mono text-xs uppercase mb-2">Prompt</div>
                  <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {selectedTrace.prompt}
                  </pre>
                </div>
              )}
              {selectedTrace.response && (
                <div>
                  <div className="text-neon-purple font-mono text-xs uppercase mb-2">Response</div>
                  <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {selectedTrace.response}
                  </pre>
                </div>
              )}
              {selectedTrace.parsed_output && (
                <div>
                  <div className="text-yellow-400 font-mono text-xs uppercase mb-2">Parsed Output</div>
                  <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm overflow-x-auto">
                    {JSON.stringify(selectedTrace.parsed_output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
