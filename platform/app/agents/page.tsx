'use client'

import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Platform-wide agents
const AGENTS = {
  production: { name: 'Curator', color: '#60a5fa', shortDesc: 'trend research' },
  world_creator: { name: 'Architect', color: '#4ade80', shortDesc: 'world building' },
  editor: { name: 'Editor', color: '#facc15', shortDesc: 'quality review' },
} as const

type AgentType = keyof typeof AGENTS

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
  }>
  editor: {
    recent_evaluations: Array<{
      id: string
      target_type: string
      overall_score: number
      created_at: string
    }>
  }
  recent_activity: Array<AgentActivity>
}

// Unified log entry type
interface LogEntry {
  id: string
  timestamp: string
  type: 'trace' | 'activity' | 'brief'
  agentType: string
  operation: string
  duration?: number | null
  error?: string | null
  preview?: string
  data: AgentTrace | AgentActivity | BriefDetail
}

export default function AgentsDashboard() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<AgentType | null>(null)
  const [allTraces, setAllTraces] = useState<AgentTrace[]>([])
  const [allActivities, setAllActivities] = useState<AgentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null)
  const [selectedBrief, setSelectedBrief] = useState<BriefDetail | null>(null)
  const logRef = useRef<HTMLDivElement>(null)

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

  const fetchAllData = async () => {
    try {
      // Fetch all traces
      const tracesRes = await fetch(`${API_BASE}/agents/traces?limit=100`)
      if (tracesRes.ok) {
        const data = await tracesRes.json()
        setAllTraces(data.traces || [])
      }

      // Fetch all activities
      const activitiesRes = await fetch(`${API_BASE}/agents/activity?limit=100`)
      if (activitiesRes.ok) {
        const data = await activitiesRes.json()
        setAllActivities(data.activities || [])
      }
    } catch (err) {
      console.error('Failed to fetch data:', err)
    }
  }

  const fetchAgentData = async (agentType: AgentType) => {
    try {
      const tracesRes = await fetch(`${API_BASE}/agents/traces?agent_type=${agentType}&limit=100`)
      if (tracesRes.ok) {
        const data = await tracesRes.json()
        setAllTraces(data.traces || [])
      }

      const activitiesRes = await fetch(`${API_BASE}/agents/activity?agent_type=${agentType}&limit=100`)
      if (activitiesRes.ok) {
        const data = await activitiesRes.json()
        setAllActivities(data.activities || [])
      }
    } catch (err) {
      console.error('Failed to fetch agent data:', err)
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
        setSelectedBrief(null)
        fetchStatus()
        fetchAllData()
      } else {
        console.error(`Failed: ${data.detail || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Failed to approve brief')
    } finally {
      setActionLoading(null)
    }
  }

  useEffect(() => {
    fetchStatus()
    fetchAllData()
    const interval = setInterval(() => {
      fetchStatus()
      if (selectedAgent) {
        fetchAgentData(selectedAgent)
      } else {
        fetchAllData()
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [selectedAgent])

  const runProductionAgent = async () => {
    setActionLoading('production')
    try {
      const res = await fetch(`${API_BASE}/agents/production/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skip_trends: false }),
      })
      await res.json()
      fetchStatus()
      fetchAllData()
    } catch (err) {
      console.error('Failed to run Curator')
    } finally {
      setActionLoading(null)
    }
  }

  const resetDatabase = async () => {
    if (!confirm('Reset everything?')) return
    setActionLoading('reset')
    try {
      await fetch(`${API_BASE}/agents/admin/reset`, { method: 'DELETE' })
      fetchStatus()
      fetchAllData()
    } catch (err) {
      console.error('Failed to reset')
    } finally {
      setActionLoading(null)
    }
  }

  // Build unified log from traces and activities
  const buildLog = (): LogEntry[] => {
    const entries: LogEntry[] = []

    // Add traces
    allTraces.forEach(trace => {
      entries.push({
        id: `trace-${trace.id}`,
        timestamp: trace.timestamp,
        type: 'trace',
        agentType: trace.agent_type,
        operation: trace.operation,
        duration: trace.duration_ms,
        error: trace.error,
        preview: trace.error
          ? `ERROR: ${trace.error.slice(0, 80)}`
          : trace.response?.slice(0, 100) || trace.operation,
        data: trace,
      })
    })

    // Add activities
    allActivities.forEach(activity => {
      entries.push({
        id: `activity-${activity.id}`,
        timestamp: activity.timestamp,
        type: 'activity',
        agentType: activity.agent_type,
        operation: activity.action,
        duration: activity.duration_ms,
        preview: activity.details
          ? JSON.stringify(activity.details).slice(0, 100)
          : activity.action,
        data: activity,
      })
    })

    // Sort by timestamp descending
    entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    return entries
  }

  const log = buildLog()

  const getAgentColor = (agentType: string): string => {
    const agent = AGENTS[agentType as AgentType]
    return agent?.color || '#888'
  }

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour12: false })
  }

  const formatResearch = (research: unknown): string => {
    if (typeof research === 'string') return research
    if (research && typeof research === 'object') {
      const r = research as Record<string, unknown>
      if (r.synthesis) return String(r.synthesis)
      if (r.discoveries && Array.isArray(r.discoveries)) {
        return (r.discoveries as Array<{ content: string }>).map(d => d.content).join('\n\n')
      }
      return JSON.stringify(r, null, 2)
    }
    return String(research)
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center font-mono text-text-secondary">
        loading...
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-screen flex flex-col items-center justify-center font-mono">
        <div className="text-red-400 mb-4">error: {error}</div>
        <button onClick={fetchStatus} className="text-text-secondary hover:text-text-primary">
          retry
        </button>
      </div>
    )
  }

  return (
    <div className="h-screen flex font-mono text-sm">
      {/* Left Sidebar - Agents */}
      <div className="w-48 border-r border-white/10 flex flex-col bg-bg-primary">
        {/* Header */}
        <div className="p-3 border-b border-white/10">
          <div className="text-text-primary text-xs uppercase tracking-wider">studio</div>
        </div>

        {/* Stats */}
        <div className="p-3 border-b border-white/10 space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-text-tertiary">worlds</span>
            <span className="text-text-secondary">{status?.world_creator.total_worlds || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-tertiary">dwellers</span>
            <span className="text-text-secondary">{status?.world_creator.total_dwellers || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-tertiary">stories</span>
            <span className="text-text-secondary">{status?.world_creator.total_stories || 0}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-tertiary">live sims</span>
            <span className="text-green-400">{status?.simulations.filter(s => s.running).length || 0}</span>
          </div>
        </div>

        {/* Agent List */}
        <div className="flex-1 overflow-y-auto">
          {/* All agents option */}
          <button
            onClick={() => {
              setSelectedAgent(null)
              fetchAllData()
            }}
            className={`w-full text-left p-3 border-b border-white/5 transition-colors ${
              selectedAgent === null ? 'bg-white/5' : 'hover:bg-white/5'
            }`}
          >
            <div className="text-text-primary text-xs">all agents</div>
            <div className="text-text-tertiary text-xs mt-0.5">{log.length} entries</div>
          </button>

          {/* Individual agents */}
          {(Object.keys(AGENTS) as AgentType[]).map((agentType) => {
            const agent = AGENTS[agentType]
            const isSelected = selectedAgent === agentType
            const traceCount = allTraces.filter(t => t.agent_type === agentType).length
            const activityCount = allActivities.filter(a => a.agent_type === agentType).length

            return (
              <button
                key={agentType}
                onClick={() => {
                  setSelectedAgent(isSelected ? null : agentType)
                  if (!isSelected) fetchAgentData(agentType)
                }}
                className={`w-full text-left p-3 border-b border-white/5 transition-colors ${
                  isSelected ? 'bg-white/5' : 'hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-2">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: agent.color }}
                  />
                  <span className="text-text-primary text-xs">{agent.name}</span>
                </div>
                <div className="text-text-tertiary text-xs mt-0.5 ml-4">
                  {agent.shortDesc}
                </div>
                {(traceCount > 0 || activityCount > 0) && (
                  <div className="text-text-tertiary text-xs mt-1 ml-4">
                    {traceCount} traces, {activityCount} actions
                  </div>
                )}
              </button>
            )
          })}
        </div>

        {/* Actions */}
        <div className="p-3 border-t border-white/10 space-y-2">
          <button
            onClick={runProductionAgent}
            disabled={actionLoading === 'production'}
            className="w-full text-left text-xs px-2 py-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded disabled:opacity-50"
          >
            {actionLoading === 'production' ? 'running...' : 'run curator'}
          </button>
          <button
            onClick={resetDatabase}
            disabled={actionLoading === 'reset'}
            className="w-full text-left text-xs px-2 py-1.5 text-red-400 hover:bg-red-500/10 rounded disabled:opacity-50"
          >
            {actionLoading === 'reset' ? 'resetting...' : 'reset all'}
          </button>
        </div>

        {/* Pending Briefs */}
        {status?.production_agent.recent_briefs.filter(b => b.status === 'pending').map(brief => (
          <div
            key={brief.id}
            onClick={() => fetchBriefDetail(brief.id)}
            className="p-3 border-t border-white/10 cursor-pointer hover:bg-white/5"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-yellow-400" />
              <span className="text-yellow-400 text-xs">pending brief</span>
            </div>
            <div className="text-text-tertiary text-xs mt-1 ml-4 truncate">
              {brief.id.slice(0, 8)}
            </div>
          </div>
        ))}
      </div>

      {/* Main Content - Log Stream */}
      <div className="flex-1 flex flex-col bg-bg-secondary overflow-hidden">
        {/* Log Header */}
        <div className="p-3 border-b border-white/10 flex items-center justify-between">
          <div className="text-text-secondary text-xs">
            {selectedAgent ? (
              <span style={{ color: AGENTS[selectedAgent].color }}>
                {AGENTS[selectedAgent].name}
              </span>
            ) : (
              'all agents'
            )}{' '}
            <span className="text-text-tertiary">
              | {log.length} entries
            </span>
          </div>
          <div className="text-text-tertiary text-xs">
            auto-refresh 3s
          </div>
        </div>

        {/* Log Stream */}
        <div ref={logRef} className="flex-1 overflow-y-auto">
          {log.length === 0 ? (
            <div className="p-8 text-center text-text-tertiary">
              no activity yet
            </div>
          ) : (
            log.map((entry) => {
              const isExpanded = expandedEntry === entry.id
              const trace = entry.type === 'trace' ? (entry.data as AgentTrace) : null
              const activity = entry.type === 'activity' ? (entry.data as AgentActivity) : null

              return (
                <div
                  key={entry.id}
                  className={`border-b border-white/5 ${isExpanded ? 'bg-white/5' : 'hover:bg-white/[0.02]'}`}
                >
                  {/* Entry Header */}
                  <div
                    onClick={() => setExpandedEntry(isExpanded ? null : entry.id)}
                    className="p-2 cursor-pointer flex items-start gap-3"
                  >
                    {/* Timestamp */}
                    <div className="text-text-tertiary text-xs w-16 shrink-0">
                      {formatTime(entry.timestamp)}
                    </div>

                    {/* Agent indicator */}
                    <div
                      className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
                      style={{ backgroundColor: getAgentColor(entry.agentType) }}
                    />

                    {/* Operation */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-text-primary text-xs">
                          {entry.operation}
                        </span>
                        {entry.type === 'trace' && (
                          <span className="text-text-tertiary text-xs">llm</span>
                        )}
                        {entry.duration && (
                          <span className="text-text-tertiary text-xs">
                            {entry.duration}ms
                          </span>
                        )}
                        {entry.error && (
                          <span className="text-red-400 text-xs">error</span>
                        )}
                      </div>
                      {!isExpanded && (
                        <div className="text-text-tertiary text-xs truncate mt-0.5">
                          {entry.preview}
                        </div>
                      )}
                    </div>

                    {/* Expand indicator */}
                    <div className="text-text-tertiary text-xs shrink-0">
                      {isExpanded ? '−' : '+'}
                    </div>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="px-2 pb-3 ml-[76px] space-y-3">
                      {/* Trace details */}
                      {trace && (
                        <>
                          {trace.model && (
                            <div>
                              <div className="text-text-tertiary text-xs mb-1">model</div>
                              <div className="text-text-secondary text-xs bg-black/30 p-2 rounded">
                                {trace.model}
                              </div>
                            </div>
                          )}
                          {trace.prompt && (
                            <div>
                              <div className="text-text-tertiary text-xs mb-1">prompt</div>
                              <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded whitespace-pre-wrap max-h-48 overflow-y-auto">
                                {trace.prompt}
                              </pre>
                            </div>
                          )}
                          {trace.response && (
                            <div>
                              <div className="text-text-tertiary text-xs mb-1">response</div>
                              <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded whitespace-pre-wrap max-h-64 overflow-y-auto">
                                {trace.response}
                              </pre>
                            </div>
                          )}
                          {trace.parsed_output && (
                            <div>
                              <div className="text-text-tertiary text-xs mb-1">parsed output</div>
                              <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded overflow-x-auto">
                                {JSON.stringify(trace.parsed_output, null, 2)}
                              </pre>
                            </div>
                          )}
                          {trace.error && (
                            <div>
                              <div className="text-red-400 text-xs mb-1">error</div>
                              <pre className="text-red-300 text-xs bg-red-900/20 p-2 rounded whitespace-pre-wrap">
                                {trace.error}
                              </pre>
                            </div>
                          )}
                        </>
                      )}

                      {/* Activity details */}
                      {activity && activity.details && (
                        <div>
                          <div className="text-text-tertiary text-xs mb-1">details</div>
                          <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded overflow-x-auto">
                            {JSON.stringify(activity.details, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* World link */}
                      {(trace?.world_id || activity?.world_id) && (
                        <div className="pt-2">
                          <Link
                            href={`/world/${trace?.world_id || activity?.world_id}`}
                            className="text-xs text-neon-cyan hover:underline"
                          >
                            view world →
                          </Link>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>

      {/* Brief Detail Panel */}
      {selectedBrief && (
        <div className="w-96 border-l border-white/10 bg-bg-primary overflow-y-auto">
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <div className="text-text-primary text-xs">brief {selectedBrief.id.slice(0, 8)}</div>
            <button
              onClick={() => setSelectedBrief(null)}
              className="text-text-tertiary hover:text-text-primary text-xs"
            >
              close
            </button>
          </div>

          <div className="p-3 space-y-4">
            {/* Status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  selectedBrief.status === 'completed' ? 'bg-green-400' :
                  selectedBrief.status === 'pending' ? 'bg-yellow-400' : 'bg-gray-400'
                }`}
              />
              <span className="text-text-secondary text-xs">{selectedBrief.status}</span>
            </div>

            {/* Research */}
            {selectedBrief.research_data?.curator_research != null && (
              <div>
                <div className="text-text-tertiary text-xs mb-2">research</div>
                <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {formatResearch(selectedBrief.research_data.curator_research)}
                </pre>
              </div>
            )}

            {/* Recommendations */}
            <div>
              <div className="text-text-tertiary text-xs mb-2">
                recommendations ({selectedBrief.recommendations?.length || 0})
              </div>
              <div className="space-y-3">
                {selectedBrief.recommendations?.map((rec, index) => (
                  <div
                    key={index}
                    className={`p-2 rounded border ${
                      selectedBrief.selected_recommendation === index
                        ? 'border-green-500/50 bg-green-500/10'
                        : 'border-white/10'
                    }`}
                  >
                    <div className="text-text-primary text-xs font-medium mb-1">
                      {rec.theme}
                    </div>
                    <div className="text-text-secondary text-xs mb-2">
                      {rec.premise_sketch}
                    </div>
                    <div className="text-text-tertiary text-xs italic mb-2">
                      {rec.core_question}
                    </div>
                    {selectedBrief.status === 'pending' && (
                      <Button
                        onClick={() => approveBrief(selectedBrief.id, index)}
                        disabled={actionLoading === `approve-${selectedBrief.id}`}
                        className="text-xs py-1 px-2 bg-green-500/20 text-green-400 hover:bg-green-500/30"
                      >
                        {actionLoading === `approve-${selectedBrief.id}` ? 'building...' : 'build world'}
                      </Button>
                    )}
                    {selectedBrief.selected_recommendation === index && (
                      <div className="text-green-400 text-xs">selected</div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Resulting world */}
            {selectedBrief.resulting_world_id && (
              <div className="pt-2">
                <Link
                  href={`/world/${selectedBrief.resulting_world_id}`}
                  className="text-xs text-neon-cyan hover:underline"
                >
                  view world →
                </Link>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
