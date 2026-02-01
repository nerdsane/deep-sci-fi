'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

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
  recent_activity: Array<{
    id: string
    timestamp: string
    agent_type: string
    action: string
    world_id: string | null
    duration_ms: number | null
  }>
}

interface AgentTrace {
  id: string
  timestamp: string
  agent_type: string
  agent_id: string | null
  world_id: string | null
  operation: string
  model: string | null
  duration_ms: number | null
  tokens_in: number | null
  tokens_out: number | null
  prompt: string | null
  response: string | null
  parsed_output: Record<string, unknown> | null
  error: string | null
}

interface TraceResponse {
  traces: AgentTrace[]
  total: number
  has_more: boolean
}

interface BriefRecommendation {
  theme: string
  premise_sketch: string
  core_question: string
  rationale: string
  estimated_appeal: string
  anti_cliche_notes?: string
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

export default function AgentsDashboard() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [traces, setTraces] = useState<AgentTrace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [selectedTrace, setSelectedTrace] = useState<AgentTrace | null>(null)
  const [traceFilter, setTraceFilter] = useState<string>('all')
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

  const fetchTraces = async () => {
    try {
      const params = new URLSearchParams({ limit: '30' })
      if (traceFilter !== 'all') {
        params.set('agent_type', traceFilter)
      }
      const res = await fetch(`${API_BASE}/agents/traces?${params}`)
      if (!res.ok) throw new Error('Failed to fetch traces')
      const data: TraceResponse = await res.json()
      setTraces(data.traces)
    } catch (err) {
      console.error('Failed to fetch traces:', err)
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
    fetchTraces()
    const interval = setInterval(() => {
      fetchStatus()
      fetchTraces()
    }, 5000) // Refresh every 5s
    return () => clearInterval(interval)
  }, [traceFilter])

  const runProductionAgent = async () => {
    setActionLoading('production')
    try {
      const res = await fetch(`${API_BASE}/agents/production/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skip_trends: false }),
      })
      const data = await res.json()
      alert(`Production Agent: ${data.status}\n${data.message || `Brief ID: ${data.brief_id}`}`)
      fetchStatus()
    } catch (err) {
      alert('Failed to run production agent')
    } finally {
      setActionLoading(null)
    }
  }

  const resetDatabase = async () => {
    if (!confirm('Are you sure you want to reset the database? This will delete all worlds, dwellers, stories, and events.')) {
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

  const startSimulation = async (worldId: string) => {
    setActionLoading(`sim-${worldId}`)
    try {
      await fetch(`${API_BASE}/worlds/${worldId}/simulation/start`, { method: 'POST' })
      fetchStatus()
    } catch (err) {
      alert('Failed to start simulation')
    } finally {
      setActionLoading(null)
    }
  }

  const stopSimulation = async (worldId: string) => {
    setActionLoading(`sim-${worldId}`)
    try {
      await fetch(`${API_BASE}/worlds/${worldId}/simulation/stop`, { method: 'POST' })
      fetchStatus()
    } catch (err) {
      alert('Failed to stop simulation')
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center text-text-secondary">Loading agent status...</div>
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

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl text-neon-cyan">Agent Observatory</h1>
          <p className="text-text-secondary mt-1">Full observability into the AI agent system</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="primary"
            onClick={runProductionAgent}
            disabled={actionLoading === 'production'}
          >
            {actionLoading === 'production' ? 'Researching trends...' : 'Run Production Agent'}
          </Button>
          <Button
            variant="ghost"
            onClick={resetDatabase}
            disabled={actionLoading === 'reset'}
            className="text-red-400 border-red-400/30 hover:bg-red-400/10"
          >
            {actionLoading === 'reset' ? 'Resetting...' : 'Reset DB'}
          </Button>
        </div>
      </div>

      {/* Global Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl text-neon-cyan font-mono">
              {status?.world_creator.total_worlds || 0}
            </div>
            <div className="text-text-tertiary text-xs uppercase tracking-wider mt-1">
              Worlds
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl text-neon-purple font-mono">
              {status?.world_creator.total_dwellers || 0}
            </div>
            <div className="text-text-tertiary text-xs uppercase tracking-wider mt-1">
              Dwellers
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl text-yellow-400 font-mono">
              {status?.world_creator.total_stories || 0}
            </div>
            <div className="text-text-tertiary text-xs uppercase tracking-wider mt-1">
              Stories
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl text-green-400 font-mono">
              {status?.simulations.filter(s => s.running).length || 0}
            </div>
            <div className="text-text-tertiary text-xs uppercase tracking-wider mt-1">
              Active Sims
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Production Agent */}
      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-neon-cyan font-mono text-sm uppercase tracking-wider">
              Production Agent
            </h2>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="text-yellow-400">
                {status?.production_agent.pending_briefs || 0} pending
              </span>
              <span className="text-green-400">
                {status?.production_agent.completed_briefs || 0} completed
              </span>
            </div>
          </div>
          <p className="text-text-secondary text-sm mb-4">
            Researches trends and recommends new world themes to create
          </p>
          {status?.production_agent.recent_briefs && status.production_agent.recent_briefs.length > 0 ? (
            <div className="space-y-2">
              <div className="text-xs font-mono text-text-tertiary mb-2">RECENT BRIEFS (click to view details)</div>
              {status.production_agent.recent_briefs.map((brief) => (
                <div
                  key={brief.id}
                  className="flex items-center justify-between p-2 bg-bg-tertiary rounded text-sm cursor-pointer hover:bg-bg-secondary transition-colors"
                  onClick={() => fetchBriefDetail(brief.id)}
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
                    <span className="text-text-secondary text-xs">
                      {new Date(brief.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {brief.status === 'pending' && (
                      <span className="text-yellow-400 text-xs animate-pulse">
                        Awaiting approval
                      </span>
                    )}
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
                </div>
              ))}
            </div>
          ) : (
            <div className="text-text-tertiary text-sm">No briefs yet</div>
          )}
        </CardContent>
      </Card>

      {/* Active Simulations */}
      <Card>
        <CardContent>
          <h2 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-4">
            World Simulations
          </h2>
          {status?.simulations && status.simulations.length > 0 ? (
            <div className="space-y-3">
              {status.simulations.map((sim) => (
                <div
                  key={sim.world_id}
                  className="flex items-center justify-between p-3 bg-bg-tertiary rounded"
                >
                  <div className="flex items-center gap-4">
                    <span
                      className={`w-3 h-3 rounded-full ${
                        sim.running ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
                      }`}
                    />
                    <div>
                      <Link
                        href={`/world/${sim.world_id}`}
                        className="text-text-primary hover:text-neon-cyan transition-colors"
                      >
                        {sim.world_name}
                      </Link>
                      <div className="flex items-center gap-4 text-xs font-mono text-text-tertiary mt-1">
                        <span>Tick #{sim.tick_count}</span>
                        <span>{sim.dweller_count} dwellers</span>
                        <span>{sim.active_conversations} convos</span>
                        <span>{sim.storyteller_observations} observations</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2 text-xs font-mono">
                      <span className={sim.puppeteer_active ? 'text-neon-purple' : 'text-gray-500'}>
                        Puppeteer
                      </span>
                      <span className={sim.storyteller_active ? 'text-neon-cyan' : 'text-gray-500'}>
                        Storyteller
                      </span>
                    </div>
                    {sim.running ? (
                      <Button
                        variant="ghost"
                        onClick={() => stopSimulation(sim.world_id)}
                        disabled={actionLoading === `sim-${sim.world_id}`}
                        className="text-xs py-1 px-2"
                      >
                        Stop
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        onClick={() => startSimulation(sim.world_id)}
                        disabled={actionLoading === `sim-${sim.world_id}`}
                        className="text-xs py-1 px-2"
                      >
                        Start
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-text-tertiary text-sm">
              No simulations running. Create a world and start its simulation.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardContent>
          <h2 className="text-yellow-400 font-mono text-sm uppercase tracking-wider mb-4">
            Recent Activity
          </h2>
          {status?.recent_activity && status.recent_activity.length > 0 ? (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {status.recent_activity.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-center justify-between p-2 bg-bg-tertiary rounded text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-mono ${
                        activity.agent_type === 'production'
                          ? 'bg-blue-500/20 text-blue-400'
                          : activity.agent_type === 'world_creator'
                          ? 'bg-green-500/20 text-green-400'
                          : activity.agent_type === 'storyteller'
                          ? 'bg-cyan-500/20 text-cyan-400'
                          : activity.agent_type === 'puppeteer'
                          ? 'bg-purple-500/20 text-purple-400'
                          : activity.agent_type === 'critic'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}
                    >
                      {activity.agent_type}
                    </span>
                    <span className="text-text-primary">{activity.action}</span>
                    {activity.duration_ms && (
                      <span className="text-text-tertiary text-xs">
                        {activity.duration_ms}ms
                      </span>
                    )}
                  </div>
                  <span className="text-text-tertiary text-xs font-mono">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-text-tertiary text-sm">No activity yet</div>
          )}
        </CardContent>
      </Card>

      {/* Critic Evaluations */}
      {status?.critic.recent_evaluations && status.critic.recent_evaluations.length > 0 && (
        <Card>
          <CardContent>
            <h2 className="text-orange-400 font-mono text-sm uppercase tracking-wider mb-4">
              Critic Evaluations
            </h2>
            <div className="space-y-2">
              {status.critic.recent_evaluations.map((evaluation) => (
                <div
                  key={evaluation.id}
                  className="flex items-center justify-between p-2 bg-bg-tertiary rounded text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-text-tertiary text-xs uppercase">
                      {evaluation.target_type}
                    </span>
                    <span className="text-text-primary">
                      Score: {evaluation.overall_score.toFixed(1)}/10
                    </span>
                  </div>
                  <span className="text-text-tertiary text-xs font-mono">
                    {new Date(evaluation.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Thinking Traces */}
      <Card>
        <CardContent>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-pink-400 font-mono text-sm uppercase tracking-wider">
              Thinking Traces
            </h2>
            <select
              value={traceFilter}
              onChange={(e) => setTraceFilter(e.target.value)}
              className="bg-bg-tertiary text-text-primary text-xs font-mono px-2 py-1 rounded border border-gray-600"
            >
              <option value="all">All Agents</option>
              <option value="production">Production</option>
              <option value="world_creator">World Creator</option>
              <option value="storyteller">Storyteller</option>
              <option value="puppeteer">Puppeteer</option>
              <option value="critic">Critic</option>
            </select>
          </div>
          <p className="text-text-secondary text-sm mb-4">
            Full prompts, responses, and reasoning from agent LLM calls
          </p>
          {traces.length > 0 ? (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {traces.map((trace) => (
                <div
                  key={trace.id}
                  className="p-3 bg-bg-tertiary rounded cursor-pointer hover:bg-bg-secondary transition-colors"
                  onClick={() => fetchFullTrace(trace.id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-mono ${
                          trace.agent_type === 'production'
                            ? 'bg-blue-500/20 text-blue-400'
                            : trace.agent_type === 'world_creator'
                            ? 'bg-green-500/20 text-green-400'
                            : trace.agent_type === 'storyteller'
                            ? 'bg-cyan-500/20 text-cyan-400'
                            : trace.agent_type === 'puppeteer'
                            ? 'bg-purple-500/20 text-purple-400'
                            : trace.agent_type === 'critic'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {trace.agent_type}
                      </span>
                      <span className="text-text-primary text-sm">{trace.operation}</span>
                      {trace.model && (
                        <span className="text-text-tertiary text-xs font-mono">
                          {trace.model.split('/').pop()}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs font-mono text-text-tertiary">
                      {trace.duration_ms && <span>{trace.duration_ms}ms</span>}
                      <span>{new Date(trace.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                  {trace.error ? (
                    <div className="text-red-400 text-xs font-mono truncate">
                      Error: {trace.error}
                    </div>
                  ) : trace.parsed_output ? (
                    <div className="text-text-secondary text-xs font-mono truncate">
                      {JSON.stringify(trace.parsed_output).slice(0, 100)}...
                    </div>
                  ) : trace.response ? (
                    <div className="text-text-secondary text-xs truncate">
                      {trace.response}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-text-tertiary text-sm">
              No traces yet. Run an agent to see its thinking process.
            </div>
          )}
        </CardContent>
      </Card>

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
                <span className="text-text-primary font-mono">Production Brief</span>
                <span className="text-text-tertiary text-sm">
                  {new Date(selectedBrief.created_at).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedBrief(null)}
                className="text-text-tertiary hover:text-text-primary"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-60px)] space-y-6">
              {selectedBrief.status === 'pending' && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded p-3 text-yellow-300 text-sm">
                  This brief is awaiting approval. Select a recommendation below to create a world.
                </div>
              )}

              <div>
                <div className="text-neon-cyan font-mono text-xs uppercase tracking-wider mb-3">
                  Recommendations ({selectedBrief.recommendations?.length || 0})
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
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-neon-purple font-mono text-xs">
                              #{index + 1}
                            </span>
                            {selectedBrief.selected_recommendation === index && (
                              <span className="text-green-400 text-xs">✓ Selected</span>
                            )}
                          </div>
                          <h3 className="text-text-primary font-semibold text-lg">
                            {rec.theme}
                          </h3>
                        </div>
                        {selectedBrief.status === 'pending' && (
                          <Button
                            variant="primary"
                            onClick={() => approveBrief(selectedBrief.id, index)}
                            disabled={actionLoading === `approve-${selectedBrief.id}`}
                            className="text-xs py-1 px-3"
                          >
                            {actionLoading === `approve-${selectedBrief.id}`
                              ? 'Creating...'
                              : 'Create World'}
                          </Button>
                        )}
                      </div>

                      <div className="space-y-3 text-sm">
                        <div>
                          <span className="text-text-tertiary">Premise: </span>
                          <span className="text-text-secondary">{rec.premise_sketch}</span>
                        </div>
                        <div>
                          <span className="text-text-tertiary">Core Question: </span>
                          <span className="text-text-secondary italic">&ldquo;{rec.core_question}&rdquo;</span>
                        </div>
                        {rec.source && (
                          <div>
                            <span className="text-neon-cyan text-text-tertiary">Source: </span>
                            <span className="text-neon-cyan/80">{rec.source}</span>
                          </div>
                        )}
                        <div>
                          <span className="text-text-tertiary">Why Now: </span>
                          <span className="text-text-secondary">{rec.rationale}</span>
                        </div>
                        {(rec.fresh_angle || rec.anti_cliche_notes) && (
                          <div>
                            <span className="text-text-tertiary">Fresh Angle: </span>
                            <span className="text-text-secondary">{rec.fresh_angle || rec.anti_cliche_notes}</span>
                          </div>
                        )}
                        {rec.target_audience && (
                          <div>
                            <span className="text-text-tertiary">For: </span>
                            <span className="text-text-secondary">{rec.target_audience}</span>
                          </div>
                        )}
                        {rec.estimated_appeal && (
                          <div>
                            <span className="text-text-tertiary">Appeal: </span>
                            <span className={`font-mono ${
                              rec.estimated_appeal.toLowerCase().includes('high')
                                ? 'text-green-400'
                                : rec.estimated_appeal.toLowerCase().includes('medium')
                                ? 'text-yellow-400'
                                : 'text-text-secondary'
                            }`}>{rec.estimated_appeal}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedBrief.research_data && Object.keys(selectedBrief.research_data).length > 0 && (
                <div>
                  <div className="text-yellow-400 font-mono text-xs uppercase tracking-wider mb-3">
                    Curator&apos;s Research
                  </div>
                  {selectedBrief.research_data.source === 'manual_creation' ? (
                    <div className="text-text-tertiary text-sm italic">
                      Manual creation - no trend research performed
                    </div>
                  ) : selectedBrief.research_data.curator_research ? (
                    <div className="space-y-4">
                      {/* Synthesis - the curator's take */}
                      {(selectedBrief.research_data.curator_research as { synthesis?: string }).synthesis && (
                        <div className="bg-bg-tertiary p-4 rounded border-l-2 border-neon-cyan">
                          <div className="text-neon-cyan font-mono text-xs uppercase mb-2">
                            The Curator&apos;s Take
                          </div>
                          <p className="text-text-secondary text-sm whitespace-pre-wrap">
                            {(selectedBrief.research_data.curator_research as { synthesis: string }).synthesis}
                          </p>
                        </div>
                      )}

                      {/* Discoveries */}
                      {(selectedBrief.research_data.curator_research as { discoveries?: Array<{ content: string }> }).discoveries?.length > 0 && (
                        <div>
                          <div className="text-neon-purple font-mono text-xs uppercase mb-2">
                            Discoveries
                          </div>
                          <div className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm max-h-48 overflow-y-auto whitespace-pre-wrap">
                            {(selectedBrief.research_data.curator_research as { discoveries: Array<{ content: string }> }).discoveries.map((d, i) => (
                              <div key={i} className="mb-2">{d.content?.slice(0, 500)}...</div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Rabbit Holes */}
                      {(selectedBrief.research_data.curator_research as { rabbit_holes?: Array<{ content: string }> }).rabbit_holes?.length > 0 && (
                        <div>
                          <div className="text-pink-400 font-mono text-xs uppercase mb-2">
                            Rabbit Holes
                          </div>
                          <div className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm max-h-48 overflow-y-auto whitespace-pre-wrap">
                            {(selectedBrief.research_data.curator_research as { rabbit_holes: Array<{ content: string }> }).rabbit_holes.map((rh, i) => (
                              <div key={i} className="mb-2">{rh.content?.slice(0, 500)}...</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : selectedBrief.research_data.trends ? (
                    <div className="grid grid-cols-2 gap-3">
                      {Object.entries(selectedBrief.research_data.trends as Record<string, unknown[]>).map(([category, items]) => (
                        items && Array.isArray(items) && items.length > 0 && (
                          <div key={category} className="bg-bg-tertiary p-3 rounded">
                            <div className="text-neon-purple font-mono text-xs uppercase mb-2">
                              {category}
                            </div>
                            <ul className="space-y-1 text-xs text-text-secondary">
                              {items.slice(0, 3).map((item, i) => (
                                <li key={i} className="truncate">
                                  • {typeof item === 'object' && item !== null
                                    ? ((item as Record<string, string>).title || (item as Record<string, string>).summary || JSON.stringify(item))
                                    : String(item)}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )
                      ))}
                    </div>
                  ) : (
                    <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-xs overflow-x-auto">
                      {JSON.stringify(selectedBrief.research_data, null, 2)}
                    </pre>
                  )}
                  {selectedBrief.research_data.timestamp && (
                    <div className="text-text-tertiary text-xs mt-2">
                      Researched: {new Date(selectedBrief.research_data.timestamp as string).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {selectedBrief.error_message && (
                <div>
                  <div className="text-red-400 font-mono text-xs uppercase tracking-wider mb-2">
                    Error
                  </div>
                  <pre className="bg-red-900/20 p-3 rounded text-red-300 text-sm">
                    {selectedBrief.error_message}
                  </pre>
                </div>
              )}

              {selectedBrief.resulting_world_id && (
                <div className="pt-4 border-t border-gray-700">
                  <Link
                    href={`/world/${selectedBrief.resulting_world_id}`}
                    className="inline-flex items-center gap-2 text-neon-cyan hover:underline"
                  >
                    View Created World →
                  </Link>
                </div>
              )}
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
                <span
                  className={`px-2 py-0.5 rounded text-xs font-mono ${
                    selectedTrace.agent_type === 'production'
                      ? 'bg-blue-500/20 text-blue-400'
                      : selectedTrace.agent_type === 'world_creator'
                      ? 'bg-green-500/20 text-green-400'
                      : selectedTrace.agent_type === 'storyteller'
                      ? 'bg-cyan-500/20 text-cyan-400'
                      : selectedTrace.agent_type === 'puppeteer'
                      ? 'bg-purple-500/20 text-purple-400'
                      : selectedTrace.agent_type === 'critic'
                      ? 'bg-yellow-500/20 text-yellow-400'
                      : 'bg-gray-500/20 text-gray-400'
                  }`}
                >
                  {selectedTrace.agent_type}
                </span>
                <span className="text-text-primary font-mono">{selectedTrace.operation}</span>
                {selectedTrace.model && (
                  <span className="text-text-tertiary text-sm">
                    Model: {selectedTrace.model}
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedTrace(null)}
                className="text-text-tertiary hover:text-text-primary"
              >
                ✕
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[calc(90vh-60px)] space-y-4">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-text-tertiary">Duration:</span>{' '}
                  <span className="font-mono">{selectedTrace.duration_ms || 'N/A'}ms</span>
                </div>
                <div>
                  <span className="text-text-tertiary">Time:</span>{' '}
                  <span className="font-mono">
                    {new Date(selectedTrace.timestamp).toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="text-text-tertiary">Agent ID:</span>{' '}
                  <span className="font-mono text-xs">{selectedTrace.agent_id || 'N/A'}</span>
                </div>
              </div>

              {selectedTrace.error && (
                <div>
                  <div className="text-red-400 font-mono text-xs uppercase tracking-wider mb-2">
                    Error
                  </div>
                  <pre className="bg-red-900/20 p-3 rounded text-red-300 text-sm overflow-x-auto">
                    {selectedTrace.error}
                  </pre>
                </div>
              )}

              {selectedTrace.prompt && (
                <div>
                  <div className="text-neon-cyan font-mono text-xs uppercase tracking-wider mb-2">
                    Prompt
                  </div>
                  <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {selectedTrace.prompt}
                  </pre>
                </div>
              )}

              {selectedTrace.response && (
                <div>
                  <div className="text-neon-purple font-mono text-xs uppercase tracking-wider mb-2">
                    Response
                  </div>
                  <pre className="bg-bg-tertiary p-3 rounded text-text-secondary text-sm overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {selectedTrace.response}
                  </pre>
                </div>
              )}

              {selectedTrace.parsed_output && (
                <div>
                  <div className="text-yellow-400 font-mono text-xs uppercase tracking-wider mb-2">
                    Parsed Output
                  </div>
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
