'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/Button'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api'

// Platform-wide agents
const AGENTS = {
  production: { name: 'Curator', color: '#60a5fa', shortDesc: 'trend research' },
  world_creator: { name: 'Architect', color: '#4ade80', shortDesc: 'world building' },
  editor: { name: 'Editor', color: '#facc15', shortDesc: 'quality review' },
} as const

// Agent name mapping for communications
const AGENT_NAMES: Record<string, { name: string; color: string }> = {
  curator: { name: 'Curator', color: '#60a5fa' },
  architect: { name: 'Architect', color: '#4ade80' },
  editor: { name: 'Editor', color: '#facc15' },
}

type AgentType = keyof typeof AGENTS

// Studio communication types
interface StudioCommunication {
  id: string
  timestamp: string
  from_agent: string
  to_agent: string | null
  message_type: 'feedback' | 'request' | 'clarification' | 'response' | 'approval'
  content: Record<string, unknown>
  content_id: string | null
  summary?: string
}

interface LettaAgentDetails {
  exists: boolean
  id?: string
  name?: string
  model?: string
  system_prompt?: string
  tags?: string[]
  tools?: { name: string; description: string }[]
  memory_blocks?: Record<string, unknown>
  message?: string
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
  const [agentDetails, setAgentDetails] = useState<LettaAgentDetails | null>(null)
  const [allTraces, setAllTraces] = useState<AgentTrace[]>([])
  const [allActivities, setAllActivities] = useState<AgentActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [expandedEntry, setExpandedEntry] = useState<string | null>(null)
  const [selectedBrief, setSelectedBrief] = useState<BriefDetail | null>(null)
  const [showAgentDetails, setShowAgentDetails] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  // Studio communications state
  const [communications, setCommunications] = useState<StudioCommunication[]>([])
  const [wsConnected, setWsConnected] = useState(false)
  const [viewMode, setViewMode] = useState<'activity' | 'communications'>('communications')
  const wsRef = useRef<WebSocket | null>(null)
  const commLogRef = useRef<HTMLDivElement>(null)

  // Fetch initial communications
  const fetchCommunications = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/studio/communications?limit=50`)
      if (res.ok) {
        const data = await res.json()
        setCommunications(data.communications || [])
      }
    } catch (err) {
      console.error('Failed to fetch communications:', err)
    }
  }, [])

  // WebSocket connection for real-time communications
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket(`${WS_BASE}/agents/studio/communications/stream`)

      ws.onopen = () => {
        console.log('Studio WebSocket connected')
        setWsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'studio_communication') {
            setCommunications(prev => [message, ...prev].slice(0, 100))
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onclose = () => {
        console.log('Studio WebSocket disconnected')
        setWsConnected(false)
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000)
      }

      ws.onerror = (error) => {
        console.error('Studio WebSocket error:', error)
      }

      wsRef.current = ws
    }

    connectWebSocket()
    fetchCommunications()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [fetchCommunications])

  // Run studio workflow
  const runStudio = async () => {
    setActionLoading('studio')
    try {
      const res = await fetch(`${API_BASE}/agents/studio/run`, { method: 'POST' })
      const data = await res.json()
      console.log('Studio run result:', data)
      fetchCommunications()
    } catch (err) {
      console.error('Failed to run studio')
    } finally {
      setActionLoading(null)
    }
  }

  // Wake a specific agent
  const wakeAgent = async (agentName: string) => {
    setActionLoading(`wake-${agentName}`)
    try {
      const res = await fetch(`${API_BASE}/agents/studio/agents/${agentName}/wake`, { method: 'POST' })
      const data = await res.json()
      console.log(`Wake ${agentName} result:`, data)
    } catch (err) {
      console.error(`Failed to wake ${agentName}`)
    } finally {
      setActionLoading(null)
    }
  }

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

  const fetchAgentDetails = async (agentType: AgentType) => {
    try {
      const res = await fetch(`${API_BASE}/agents/letta/${agentType}`)
      if (res.ok) {
        const data = await res.json()
        setAgentDetails(data)
        setShowAgentDetails(true)
      }
    } catch (err) {
      console.error('Failed to fetch agent details:', err)
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

  const runCollaborative = async () => {
    setActionLoading('collaborate')
    try {
      const res = await fetch(`${API_BASE}/agents/production/collaborate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      const data = await res.json()
      console.log('Collaborative result:', data)
      fetchStatus()
      fetchAllData()
    } catch (err) {
      console.error('Failed to run collaborative production')
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
      <div className="h-full flex items-center justify-center font-mono text-text-secondary">
        loading...
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center font-mono">
        <div className="text-red-400 mb-4">error: {error}</div>
        <button onClick={fetchStatus} className="text-text-secondary hover:text-text-primary">
          retry
        </button>
      </div>
    )
  }

  return (
    <div className="h-full flex font-mono text-sm">
      {/* Left Sidebar - Agents */}
      <div className="w-48 border-r border-white/10 flex flex-col bg-bg-primary">
        {/* Header */}
        <div className="p-3 border-b border-white/10">
          <div className="text-text-primary text-xs uppercase tracking-wider">studio</div>
          <div className="text-text-tertiary text-xs mt-0.5">Watch the agents cook</div>
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
              <div key={agentType} className="border-b border-white/5">
                <button
                  onClick={() => {
                    setSelectedAgent(isSelected ? null : agentType)
                    if (!isSelected) {
                      fetchAgentData(agentType)
                      fetchAgentDetails(agentType)
                    } else {
                      setShowAgentDetails(false)
                    }
                  }}
                  className={`w-full text-left p-3 transition-colors ${
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
                {/* Info button */}
                {isSelected && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setShowAgentDetails(!showAgentDetails)
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-text-tertiary hover:text-text-secondary bg-white/5"
                  >
                    {showAgentDetails ? '▾ hide details' : '▸ show details'}
                  </button>
                )}
              </div>
            )
          })}
        </div>

        {/* Studio Actions (Maximum Agency) */}
        <div className="p-3 border-t border-white/10 space-y-2">
          <div className="text-text-tertiary text-xs mb-2 font-medium">Studio</div>
          <button
            onClick={runStudio}
            disabled={actionLoading === 'studio'}
            className="w-full text-left text-xs px-2 py-1.5 bg-neon-cyan/20 text-neon-cyan hover:bg-neon-cyan/30 rounded disabled:opacity-50"
          >
            {actionLoading === 'studio' ? 'waking agents...' : '▶ Run Studio'}
          </button>
          <div className="flex gap-1">
            <button
              onClick={() => wakeAgent('curator')}
              disabled={actionLoading?.startsWith('wake')}
              className="flex-1 text-center text-xs px-1 py-1 text-blue-400 hover:bg-blue-500/10 rounded disabled:opacity-50"
              title="Wake Curator"
            >
              C
            </button>
            <button
              onClick={() => wakeAgent('architect')}
              disabled={actionLoading?.startsWith('wake')}
              className="flex-1 text-center text-xs px-1 py-1 text-green-400 hover:bg-green-500/10 rounded disabled:opacity-50"
              title="Wake Architect"
            >
              A
            </button>
            <button
              onClick={() => wakeAgent('editor')}
              disabled={actionLoading?.startsWith('wake')}
              className="flex-1 text-center text-xs px-1 py-1 text-yellow-400 hover:bg-yellow-500/10 rounded disabled:opacity-50"
              title="Wake Editor"
            >
              E
            </button>
          </div>
        </div>

        {/* Legacy Actions */}
        <div className="p-3 border-t border-white/10 space-y-2">
          <div className="text-text-tertiary text-xs mb-2 font-medium">Legacy</div>
          <button
            onClick={runProductionAgent}
            disabled={actionLoading === 'production'}
            className="w-full text-left text-xs px-2 py-1.5 bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 rounded disabled:opacity-50"
          >
            {actionLoading === 'production' ? 'running...' : 'run curator (solo)'}
          </button>
          <button
            onClick={runCollaborative}
            disabled={actionLoading === 'collaborate'}
            className="w-full text-left text-xs px-2 py-1.5 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded disabled:opacity-50"
          >
            {actionLoading === 'collaborate' ? 'collaborating...' : 'run collaborative'}
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
        {/* Log Header with View Mode Toggle */}
        <div className="p-3 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* View Mode Toggle */}
            <div className="flex items-center gap-1 bg-bg-primary rounded-md p-0.5">
              <button
                onClick={() => setViewMode('communications')}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  viewMode === 'communications'
                    ? 'bg-bg-tertiary text-text-primary'
                    : 'text-text-tertiary hover:text-text-secondary'
                }`}
              >
                💬 Studio
              </button>
              <button
                onClick={() => setViewMode('activity')}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  viewMode === 'activity'
                    ? 'bg-bg-tertiary text-text-primary'
                    : 'text-text-tertiary hover:text-text-secondary'
                }`}
              >
                📊 Activity
              </button>
            </div>

            <div className="text-text-secondary text-xs">
              {viewMode === 'communications' ? (
                <>
                  <span className="text-neon-cyan">communications</span>
                  <span className="text-text-tertiary"> | {communications.length} messages</span>
                </>
              ) : selectedAgent ? (
                <>
                  <span style={{ color: AGENTS[selectedAgent].color }}>
                    {AGENTS[selectedAgent].name}
                  </span>
                  <span className="text-text-tertiary"> | {log.length} entries</span>
                </>
              ) : (
                <>
                  all agents
                  <span className="text-text-tertiary"> | {log.length} entries</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {viewMode === 'communications' && (
              <span className={`text-xs ${wsConnected ? 'text-green-400' : 'text-red-400'}`}>
                {wsConnected ? '● live' : '○ connecting...'}
              </span>
            )}
            <div className="text-text-tertiary text-xs">
              {viewMode === 'activity' ? 'auto-refresh 3s' : 'real-time'}
            </div>
          </div>
        </div>

        {/* Communications Feed (Studio View) */}
        {viewMode === 'communications' && (
          <div ref={commLogRef} className="flex-1 overflow-y-auto p-3 space-y-2">
            {communications.length === 0 ? (
              <div className="text-text-tertiary text-sm">
                <div className="mb-2">$ waiting for studio communications...</div>
                <div className="text-text-quaternary text-xs">
                  Click "Run Studio" to wake agents, or wait for autonomous activity.
                </div>
              </div>
            ) : (
              communications.map((comm) => {
                const fromInfo = AGENT_NAMES[comm.from_agent] || { name: comm.from_agent, color: '#888' }
                const toInfo = comm.to_agent ? AGENT_NAMES[comm.to_agent] : null

                // Message type styling
                const typeStyles: Record<string, { icon: string; color: string }> = {
                  feedback: { icon: '◆', color: '#facc15' },
                  request: { icon: '▸', color: '#60a5fa' },
                  clarification: { icon: '?', color: '#c084fc' },
                  response: { icon: '↩', color: '#4ade80' },
                  approval: { icon: '✓', color: '#22c55e' },
                }
                const typeStyle = typeStyles[comm.message_type] || { icon: '●', color: '#888' }

                // Format content preview
                const contentPreview = () => {
                  const content = comm.content
                  if (comm.message_type === 'feedback') {
                    const verdict = (content.verdict as string) || 'unknown'
                    const points = (content.feedback_points as string[]) || []
                    return (
                      <div className="space-y-1">
                        <span className={`font-medium ${
                          verdict === 'approve' ? 'text-green-400' :
                          verdict === 'reject' ? 'text-red-400' :
                          'text-yellow-400'
                        }`}>
                          {verdict.toUpperCase()}
                        </span>
                        {points.length > 0 && (
                          <ul className="text-text-tertiary text-xs list-disc list-inside">
                            {points.slice(0, 3).map((p, i) => (
                              <li key={i}>{typeof p === 'string' ? p.slice(0, 60) : String(p)}...</li>
                            ))}
                            {points.length > 3 && <li>...and {points.length - 3} more</li>}
                          </ul>
                        )}
                      </div>
                    )
                  } else if (comm.message_type === 'request') {
                    const summary = (content.summary as string) || (content.content_summary as string) || ''
                    return <span className="text-text-secondary">{summary.slice(0, 100)}{summary.length > 100 ? '...' : ''}</span>
                  } else if (comm.message_type === 'clarification') {
                    const questions = (content.questions as string[]) || []
                    return (
                      <ul className="text-text-secondary text-xs list-disc list-inside">
                        {questions.slice(0, 2).map((q, i) => (
                          <li key={i}>{typeof q === 'string' ? q : String(q)}</li>
                        ))}
                      </ul>
                    )
                  } else if (comm.message_type === 'approval') {
                    const score = (content.quality_score as number) || 0
                    return <span className="text-green-400">Quality score: {(score * 10).toFixed(1)}/10</span>
                  } else if (comm.message_type === 'response') {
                    const addressed = (content.addressed_points as string[]) || []
                    return <span className="text-text-secondary">Addressed {addressed.length} point(s)</span>
                  }
                  return <span className="text-text-tertiary">{comm.summary || JSON.stringify(content).slice(0, 50)}</span>
                }

                return (
                  <div key={comm.id} className="group">
                    {/* Message header */}
                    <div className="flex items-start gap-2">
                      <span className="text-text-tertiary text-xs shrink-0 w-14">
                        {new Date(comm.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span style={{ color: fromInfo.color }} className="text-xs font-medium">
                        {fromInfo.name}
                      </span>
                      <span className="text-text-quaternary">→</span>
                      <span style={{ color: toInfo?.color || '#888' }} className="text-xs font-medium">
                        {toInfo?.name || 'All'}
                      </span>
                      <span style={{ color: typeStyle.color }} className="text-xs">
                        {typeStyle.icon} {comm.message_type}
                      </span>
                      {comm.content_id && (
                        <span className="text-text-quaternary text-xs">
                          re:{comm.content_id.slice(0, 8)}
                        </span>
                      )}
                    </div>

                    {/* Message content */}
                    <div className="ml-16 mt-1 text-xs">
                      {contentPreview()}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}

        {/* Activity Feed (Legacy View) */}
        {viewMode === 'activity' && (
        <div ref={logRef} className="flex-1 overflow-y-auto p-3 space-y-1">
          {log.length === 0 ? (
            <div className="text-text-tertiary">$ waiting for activity...</div>
          ) : (
            log.map((entry) => {
              const trace = entry.type === 'trace' ? (entry.data as AgentTrace) : null
              const activity = entry.type === 'activity' ? (entry.data as AgentActivity) : null
              const agentName = AGENTS[entry.agentType as AgentType]?.name || entry.agentType
              const color = getAgentColor(entry.agentType)

              return (
                <div key={entry.id} className="space-y-1">
                  {/* Operation line */}
                  <div className="flex items-start gap-2">
                    <span className="text-text-tertiary text-xs shrink-0 w-14">
                      {formatTime(entry.timestamp)}
                    </span>
                    <span className="text-text-tertiary">$</span>
                    <span style={{ color }} className="text-xs">{agentName}</span>
                    <span className="text-text-primary text-xs">{entry.operation}</span>
                    {entry.duration && (
                      <span className="text-text-tertiary text-xs">({entry.duration}ms)</span>
                    )}
                  </div>

                  {/* Trace: Claude Code style - thinking, tool calls, response */}
                  {trace && (
                    <>
                      {/* Thinking/Reasoning (collapsible) */}
                      {trace.parsed_output?.full_reasoning && Array.isArray(trace.parsed_output.full_reasoning) && trace.parsed_output.full_reasoning.length > 0 && (
                        <details className="ml-16 group">
                          <summary className="flex items-center gap-2 cursor-pointer text-text-tertiary hover:text-text-secondary">
                            <span className="text-purple-400 text-xs">⟡</span>
                            <span className="text-xs">thinking ({(trace.parsed_output.full_reasoning as string[]).length} steps)</span>
                          </summary>
                          <div className="mt-1 pl-4 border-l border-purple-400/30 space-y-2">
                            {(trace.parsed_output.full_reasoning as string[]).map((thought, i) => (
                              <pre key={i} className="text-purple-300/70 text-xs whitespace-pre-wrap italic">
                                {thought}
                              </pre>
                            ))}
                          </div>
                        </details>
                      )}

                      {/* Tool Calls - Claude Code style */}
                      {trace.parsed_output?.tool_calls && Array.isArray(trace.parsed_output.tool_calls) && (trace.parsed_output.tool_calls as Array<{name: string, arguments: Record<string, unknown>}>).map((call, i) => (
                        <div key={i} className="ml-16 flex items-start gap-2">
                          <span className="text-cyan-400 shrink-0">◆</span>
                          <span className="text-cyan-400 text-xs font-medium">{call.name}</span>
                          <span className="text-text-tertiary text-xs">
                            {typeof call.arguments === 'string'
                              ? call.arguments
                              : JSON.stringify(call.arguments)}
                          </span>
                        </div>
                      ))}

                      {/* Tool results */}
                      {trace.parsed_output?.tool_results && Array.isArray(trace.parsed_output.tool_results) && (trace.parsed_output.tool_results as Array<{name: string, status: string, preview: string}>).map((result, i) => (
                        <div key={i} className="ml-16 flex items-start gap-2">
                          <span className={`shrink-0 ${result.status === 'success' ? 'text-green-400' : 'text-red-400'}`}>
                            {result.status === 'success' ? '✓' : '✗'}
                          </span>
                          <span className="text-green-400/70 text-xs font-medium">{result.name}</span>
                          <span className="text-text-tertiary text-xs truncate max-w-md">
                            {result.preview?.slice(0, 100)}...
                          </span>
                        </div>
                      ))}

                      {/* Prompt (input) */}
                      {trace.prompt && (
                        <details className="ml-16 group">
                          <summary className="flex items-center gap-2 cursor-pointer text-text-tertiary hover:text-text-secondary">
                            <span className="text-yellow-500 text-xs">▸</span>
                            <span className="text-xs">prompt</span>
                          </summary>
                          <pre className="mt-1 pl-4 text-text-tertiary text-xs whitespace-pre-wrap break-all border-l border-yellow-500/30">
                            {trace.prompt}
                          </pre>
                        </details>
                      )}

                      {/* Response (output) */}
                      {trace.response && (
                        <div className="ml-16 flex items-start gap-2">
                          <span className="text-green-500 shrink-0">→</span>
                          <pre className="text-text-secondary text-xs whitespace-pre-wrap break-all flex-1">
                            {trace.response.length > 600 ? trace.response.slice(0, 600) + '...' : trace.response}
                          </pre>
                        </div>
                      )}

                      {/* Error */}
                      {trace.error && (
                        <div className="ml-16 flex items-start gap-2">
                          <span className="text-red-500 shrink-0">✗</span>
                          <pre className="text-red-400 text-xs whitespace-pre-wrap break-all flex-1">
                            {trace.error}
                          </pre>
                        </div>
                      )}

                      {/* World link */}
                      {trace.world_id && (
                        <div className="ml-16 flex items-center gap-2">
                          <span className="text-text-tertiary shrink-0">@</span>
                          <Link href={`/world/${trace.world_id}`} className="text-neon-cyan text-xs hover:underline">
                            world/{trace.world_id.slice(0, 8)}
                          </Link>
                        </div>
                      )}
                    </>
                  )}

                  {/* Activity: show details inline */}
                  {activity && (
                    <>
                      {activity.details && (
                        <div className="flex items-start gap-2 ml-16">
                          <span className="text-purple-400 shrink-0">*</span>
                          <pre className="text-text-secondary text-xs whitespace-pre-wrap break-all flex-1">
                            {JSON.stringify(activity.details, null, 2)}
                          </pre>
                        </div>
                      )}
                      {activity.world_id && (
                        <div className="flex items-start gap-2 ml-16">
                          <span className="text-text-tertiary shrink-0">@</span>
                          <Link href={`/world/${activity.world_id}`} className="text-neon-cyan text-xs hover:underline">
                            world/{activity.world_id.slice(0, 8)}
                          </Link>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )
            })
          )}
        </div>
        )}
      </div>

      {/* Agent Details Panel */}
      {showAgentDetails && selectedAgent && agentDetails && (
        <div className="w-80 border-l border-white/10 bg-bg-primary overflow-y-auto">
          <div className="p-3 border-b border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: AGENTS[selectedAgent].color }}
              />
              <span className="text-text-primary text-xs">{AGENTS[selectedAgent].name}</span>
            </div>
            <button
              onClick={() => setShowAgentDetails(false)}
              className="text-text-tertiary hover:text-text-primary text-xs"
            >
              close
            </button>
          </div>

          <div className="p-3 space-y-4">
            {!agentDetails.exists ? (
              <div className="text-text-tertiary text-xs">
                {agentDetails.message || 'Agent not created yet'}
              </div>
            ) : (
              <>
                {/* Model */}
                <div>
                  <div className="text-text-tertiary text-xs mb-1">model</div>
                  <div className="text-text-secondary text-xs font-mono">{agentDetails.model}</div>
                </div>

                {/* Tools */}
                {agentDetails.tools && agentDetails.tools.length > 0 && (
                  <div>
                    <div className="text-text-tertiary text-xs mb-1">tools ({agentDetails.tools.length})</div>
                    <div className="space-y-1">
                      {agentDetails.tools.map((tool, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-cyan-400 text-xs">◆</span>
                          <span className="text-text-secondary text-xs">{tool.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Tags */}
                {agentDetails.tags && agentDetails.tags.length > 0 && (
                  <div>
                    <div className="text-text-tertiary text-xs mb-1">tags</div>
                    <div className="flex flex-wrap gap-1">
                      {agentDetails.tags.map((tag, i) => (
                        <span key={i} className="text-xs px-1.5 py-0.5 bg-white/10 rounded text-text-secondary">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* System Prompt */}
                {agentDetails.system_prompt && (
                  <div>
                    <div className="text-text-tertiary text-xs mb-1">personality</div>
                    <pre className="text-text-secondary text-xs bg-black/30 p-2 rounded whitespace-pre-wrap max-h-64 overflow-y-auto">
                      {agentDetails.system_prompt}
                    </pre>
                  </div>
                )}

                {/* Memory Blocks */}
                {agentDetails.memory_blocks && Object.keys(agentDetails.memory_blocks).length > 0 && (
                  <div>
                    <div className="text-text-tertiary text-xs mb-1">memory</div>
                    <div className="space-y-2">
                      {Object.entries(agentDetails.memory_blocks).map(([key, value]) => (
                        <div key={key} className="bg-black/30 p-2 rounded">
                          <div className="text-purple-400 text-xs font-mono mb-1">{key}</div>
                          <pre className="text-text-tertiary text-xs whitespace-pre-wrap">
                            {typeof value === 'string' ? value.slice(0, 200) : JSON.stringify(value, null, 2).slice(0, 200)}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

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
