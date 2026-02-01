'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import Link from 'next/link'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Agent profiles - Discord server style
const AGENTS = {
  curator: {
    name: 'Curator',
    avatar: '🔮',
    color: '#60a5fa',
    role: 'Trend Research & World Ideas',
    status: 'online',
  },
  architect: {
    name: 'Architect',
    avatar: '🏗️',
    color: '#4ade80',
    role: 'World Building',
    status: 'offline',
  },
  editor: {
    name: 'Editor',
    avatar: '✍️',
    color: '#facc15',
    role: 'Quality Review',
    status: 'offline',
  },
} as const

type AgentKey = keyof typeof AGENTS

interface AgentDetails {
  exists: boolean
  id?: string
  name?: string
  model?: string
  system_prompt?: string
  tags?: string[]
  tools?: { name: string; description: string }[]
  memory_blocks?: Record<string, unknown>
}

interface WakeResult {
  status: string
  response?: string
  actions_taken?: Array<{ type: string; tool?: string; action?: string }>
  world_ideas?: Array<Record<string, unknown>>
  context?: Record<string, unknown>
  trace?: {
    reasoning: string[]
    tool_calls: Array<{ name: string; arguments: string }>
    tool_results: Array<{ name: string | null; status: string; preview: string }>
  }
  duration_ms?: number
  error?: string
}

interface AgentTrace {
  id: string
  timestamp: string
  agent_type: string
  operation: string
  model: string | null
  duration_ms: number | null
  prompt: string | null
  response: string | null
  parsed_output: {
    reasoning_steps?: number
    tool_calls?: Array<{ name: string; arguments: string }>
    tool_results?: Array<{ name: string | null; status: string; preview: string }>
    full_reasoning?: string[]
    world_ideas_count?: number
  } | null
  error: string | null
}

interface PlatformStats {
  total_worlds: number
  pending_briefs: number
  total_dwellers: number
  total_stories: number
}

export default function StudioPage() {
  const [selectedAgent, setSelectedAgent] = useState<AgentKey>('curator')
  const [agentDetails, setAgentDetails] = useState<AgentDetails | null>(null)
  const [traces, setTraces] = useState<AgentTrace[]>([])
  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [waking, setWaking] = useState(false)
  const [lastWakeResult, setLastWakeResult] = useState<WakeResult | null>(null)
  const historyRef = useRef<HTMLDivElement>(null)

  // Fetch agent details
  const fetchAgentDetails = useCallback(async (agent: AgentKey) => {
    try {
      const res = await fetch(`${API_BASE}/agents/letta/${agent}`)
      if (res.ok) {
        const data = await res.json()
        setAgentDetails(data)
      }
    } catch (err) {
      console.error('Failed to fetch agent details:', err)
    }
  }, [])

  // Fetch agent traces/history
  const fetchTraces = useCallback(async (agent: AgentKey) => {
    try {
      // Map agent key to backend agent_type
      const agentTypeMap: Record<AgentKey, string> = {
        curator: 'production',
        architect: 'world_creator',
        editor: 'critic',
      }
      const res = await fetch(`${API_BASE}/agents/traces?agent_type=${agentTypeMap[agent]}&limit=50`)
      if (res.ok) {
        const data = await res.json()
        setTraces(data.traces || [])
      }
    } catch (err) {
      console.error('Failed to fetch traces:', err)
    }
  }, [])

  // Fetch platform stats
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/status`)
      if (res.ok) {
        const data = await res.json()
        setStats({
          total_worlds: data.world_creator?.total_worlds || 0,
          pending_briefs: data.production_agent?.pending_briefs || 0,
          total_dwellers: data.world_creator?.total_dwellers || 0,
          total_stories: data.world_creator?.total_stories || 0,
        })
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  // Wake the Curator
  const wakeCurator = async () => {
    setWaking(true)
    setLastWakeResult(null)
    try {
      const res = await fetch(`${API_BASE}/agents/curator/wake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data: WakeResult = await res.json()
      setLastWakeResult(data)
      // Refresh traces to show new activity
      fetchTraces('curator')
    } catch (err) {
      console.error('Failed to wake curator:', err)
      setLastWakeResult({ status: 'error', error: String(err) })
    } finally {
      setWaking(false)
    }
  }

  // Initial load
  useEffect(() => {
    fetchAgentDetails(selectedAgent)
    fetchTraces(selectedAgent)
    fetchStats()
  }, [selectedAgent, fetchAgentDetails, fetchTraces, fetchStats])

  // Auto-refresh traces every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchTraces(selectedAgent)
    }, 5000)
    return () => clearInterval(interval)
  }, [selectedAgent, fetchTraces])

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const formatDate = (ts: string) => {
    const d = new Date(ts)
    const today = new Date()
    if (d.toDateString() === today.toDateString()) return 'Today'
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    if (d.toDateString() === yesterday.toDateString()) return 'Yesterday'
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  // Group traces by date
  const tracesByDate = traces.reduce((acc, trace) => {
    const date = formatDate(trace.timestamp)
    if (!acc[date]) acc[date] = []
    acc[date].push(trace)
    return acc
  }, {} as Record<string, AgentTrace[]>)

  const agent = AGENTS[selectedAgent]

  return (
    <div className="h-screen flex bg-[#313338] text-gray-100 font-sans">
      {/* Left Sidebar - Agent Servers (Discord style) */}
      <div className="w-[72px] bg-[#1e1f22] flex flex-col items-center py-3 gap-2">
        {/* Home/Stats button */}
        <div className="w-12 h-12 rounded-2xl bg-[#5865f2] flex items-center justify-center text-white font-bold text-lg hover:rounded-xl transition-all cursor-pointer mb-2">
          🌌
        </div>
        <div className="w-8 h-[2px] bg-[#35363c] rounded-full mb-2" />

        {/* Agent avatars */}
        {(Object.keys(AGENTS) as AgentKey[]).map((key) => {
          const a = AGENTS[key]
          const isSelected = selectedAgent === key
          return (
            <div key={key} className="relative group">
              <button
                onClick={() => setSelectedAgent(key)}
                className={`w-12 h-12 rounded-[24px] flex items-center justify-center text-2xl transition-all hover:rounded-xl ${
                  isSelected ? 'rounded-xl bg-[#5865f2]' : 'bg-[#313338] hover:bg-[#5865f2]'
                }`}
                title={a.name}
              >
                {a.avatar}
              </button>
              {/* Selection indicator */}
              <div
                className={`absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 w-1 rounded-r-full bg-white transition-all ${
                  isSelected ? 'h-10' : 'h-0 group-hover:h-5'
                }`}
              />
              {/* Status dot */}
              <div
                className={`absolute bottom-0 right-0 w-3.5 h-3.5 rounded-full border-[3px] border-[#1e1f22] ${
                  a.status === 'online' ? 'bg-[#23a559]' : 'bg-[#80848e]'
                }`}
              />
            </div>
          )
        })}
      </div>

      {/* Channel Sidebar */}
      <div className="w-60 bg-[#2b2d31] flex flex-col">
        {/* Server header */}
        <div className="h-12 px-4 flex items-center border-b border-[#1f2023] shadow-sm">
          <span className="font-semibold text-[15px] text-white">Deep Sci-Fi Studio</span>
        </div>

        {/* Agent profile section */}
        <div className="p-3 border-b border-[#1f2023]">
          <div className="flex items-center gap-3 p-2 rounded-md bg-[#35373c]">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center text-xl"
              style={{ backgroundColor: agent.color + '30' }}
            >
              {agent.avatar}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-white truncate">{agent.name}</div>
              <div className="text-xs text-[#949ba4] truncate">{agent.role}</div>
            </div>
          </div>
        </div>

        {/* Channels */}
        <div className="flex-1 overflow-y-auto px-2 py-3">
          <div className="text-[11px] font-semibold text-[#949ba4] uppercase tracking-wide px-2 mb-1">
            Activity
          </div>
          <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-[#949ba4] hover:text-white hover:bg-[#35373c] text-left">
            <span className="text-lg opacity-60">#</span>
            <span className="text-sm">history</span>
            {traces.length > 0 && (
              <span className="ml-auto text-[10px] bg-[#5865f2] text-white px-1.5 py-0.5 rounded-full">
                {traces.length}
              </span>
            )}
          </button>

          <div className="text-[11px] font-semibold text-[#949ba4] uppercase tracking-wide px-2 mb-1 mt-4">
            Actions
          </div>
          {selectedAgent === 'curator' && (
            <button
              onClick={wakeCurator}
              disabled={waking}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-[#23a559] hover:text-white hover:bg-[#23a559] text-left disabled:opacity-50"
            >
              <span className="text-lg">⚡</span>
              <span className="text-sm">{waking ? 'Waking...' : 'Wake Curator'}</span>
            </button>
          )}
        </div>

        {/* Stats footer */}
        <div className="p-3 border-t border-[#1f2023] text-[11px] text-[#949ba4] space-y-1">
          <div className="flex justify-between">
            <span>Worlds</span>
            <span className="text-white">{stats?.total_worlds || 0}</span>
          </div>
          <div className="flex justify-between">
            <span>Pending Briefs</span>
            <span className="text-[#f0b232]">{stats?.pending_briefs || 0}</span>
          </div>
          <div className="flex justify-between">
            <span>Dwellers</span>
            <span className="text-white">{stats?.total_dwellers || 0}</span>
          </div>
        </div>
      </div>

      {/* Main Content - Chat History */}
      <div className="flex-1 flex flex-col bg-[#313338]">
        {/* Channel header */}
        <div className="h-12 px-4 flex items-center border-b border-[#1f2023] shadow-sm">
          <span className="text-lg opacity-60 mr-2">#</span>
          <span className="font-semibold text-white">history</span>
          <span className="mx-2 text-[#3f4147]">|</span>
          <span className="text-sm text-[#949ba4]">{agent.name}&apos;s activity and traces</span>
        </div>

        {/* Messages area */}
        <div ref={historyRef} className="flex-1 overflow-y-auto px-4 py-4">
          {/* Last wake result (if any) */}
          {lastWakeResult && (
            <div className="mb-6 p-4 rounded-lg bg-[#2b2d31] border border-[#1f2023]">
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">{agent.avatar}</span>
                <span className="font-medium text-white">{agent.name}</span>
                <span className="text-xs text-[#949ba4]">just now</span>
                {lastWakeResult.duration_ms && (
                  <span className="text-xs text-[#949ba4]">({lastWakeResult.duration_ms}ms)</span>
                )}
              </div>

              {/* Response */}
              {lastWakeResult.response && (
                <div className="text-sm text-[#dbdee1] whitespace-pre-wrap mb-3">
                  {lastWakeResult.response}
                </div>
              )}

              {/* Trace details */}
              {lastWakeResult.trace && (
                <div className="space-y-2 text-xs">
                  {/* Reasoning */}
                  {lastWakeResult.trace.reasoning.length > 0 && (
                    <details className="group">
                      <summary className="cursor-pointer text-[#949ba4] hover:text-white flex items-center gap-1">
                        <span className="text-purple-400">💭</span>
                        Reasoning ({lastWakeResult.trace.reasoning.length} steps)
                      </summary>
                      <div className="mt-2 pl-4 border-l-2 border-purple-500/30 space-y-2">
                        {lastWakeResult.trace.reasoning.map((r, i) => (
                          <div key={i} className="text-purple-300/80 italic">{r}</div>
                        ))}
                      </div>
                    </details>
                  )}

                  {/* Tool calls */}
                  {lastWakeResult.trace.tool_calls.length > 0 && (
                    <div className="space-y-1">
                      {lastWakeResult.trace.tool_calls.map((tc, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <span className="text-cyan-400">◆</span>
                          <span className="text-cyan-300 font-mono">{tc.name}</span>
                          <span className="text-[#949ba4] truncate">{tc.arguments}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Tool results */}
                  {lastWakeResult.trace.tool_results.length > 0 && (
                    <div className="space-y-1">
                      {lastWakeResult.trace.tool_results.map((tr, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className={tr.status === 'success' ? 'text-green-400' : 'text-red-400'}>
                            {tr.status === 'success' ? '✓' : '✗'}
                          </span>
                          <span className="text-[#949ba4] font-mono text-[11px]">{tr.name || 'tool'}</span>
                          <span className="text-[#6d6f78] truncate flex-1">{tr.preview?.slice(0, 80)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Error */}
              {lastWakeResult.error && (
                <div className="text-red-400 text-sm mt-2">{lastWakeResult.error}</div>
              )}
            </div>
          )}

          {/* History by date */}
          {Object.keys(tracesByDate).length === 0 ? (
            <div className="text-center py-20">
              <div className="text-6xl mb-4">{agent.avatar}</div>
              <div className="text-xl font-semibold text-white mb-2">Welcome to #{agent.name.toLowerCase()}</div>
              <div className="text-[#949ba4]">
                This is the beginning of {agent.name}&apos;s history.
                {selectedAgent === 'curator' && (
                  <div className="mt-2">
                    Click <span className="text-[#23a559] font-medium">Wake Curator</span> to see them in action.
                  </div>
                )}
              </div>
            </div>
          ) : (
            Object.entries(tracesByDate).map(([date, dateTraces]) => (
              <div key={date}>
                {/* Date divider */}
                <div className="flex items-center gap-4 my-4">
                  <div className="flex-1 h-px bg-[#3f4147]" />
                  <span className="text-[11px] font-semibold text-[#949ba4]">{date}</span>
                  <div className="flex-1 h-px bg-[#3f4147]" />
                </div>

                {/* Messages for this date */}
                {dateTraces.map((trace) => (
                  <div key={trace.id} className="group hover:bg-[#2e3035] -mx-4 px-4 py-2 rounded">
                    {/* Message header */}
                    <div className="flex items-start gap-4">
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center text-xl shrink-0 mt-0.5"
                        style={{ backgroundColor: agent.color + '30' }}
                      >
                        {agent.avatar}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="font-medium text-white hover:underline cursor-pointer">
                            {agent.name}
                          </span>
                          <span className="text-[11px] text-[#949ba4]">
                            {formatTime(trace.timestamp)}
                          </span>
                          <span className="text-[11px] px-1.5 py-0.5 rounded bg-[#5865f2]/20 text-[#949ba4]">
                            {trace.operation}
                          </span>
                          {trace.duration_ms && (
                            <span className="text-[11px] text-[#6d6f78]">
                              {trace.duration_ms}ms
                            </span>
                          )}
                        </div>

                        {/* Response content */}
                        {trace.response && (
                          <div className="mt-1 text-sm text-[#dbdee1] whitespace-pre-wrap">
                            {trace.response.length > 500 ? trace.response.slice(0, 500) + '...' : trace.response}
                          </div>
                        )}

                        {/* Expandable details */}
                        <div className="mt-2 space-y-2 text-xs">
                          {/* Reasoning */}
                          {trace.parsed_output?.full_reasoning && trace.parsed_output.full_reasoning.length > 0 && (
                            <details className="group/details">
                              <summary className="cursor-pointer text-[#949ba4] hover:text-white flex items-center gap-1">
                                <span className="text-purple-400">💭</span>
                                Reasoning ({trace.parsed_output.full_reasoning.length} steps)
                              </summary>
                              <div className="mt-2 pl-4 border-l-2 border-purple-500/30 space-y-2">
                                {trace.parsed_output.full_reasoning.map((r, i) => (
                                  <div key={i} className="text-purple-300/80 italic">{r}</div>
                                ))}
                              </div>
                            </details>
                          )}

                          {/* Tool calls */}
                          {trace.parsed_output?.tool_calls && trace.parsed_output.tool_calls.length > 0 && (
                            <div className="space-y-1">
                              {trace.parsed_output.tool_calls.map((tc, i) => (
                                <div key={i} className="flex items-center gap-2">
                                  <span className="text-cyan-400">◆</span>
                                  <span className="text-cyan-300 font-mono">{tc.name}</span>
                                  <span className="text-[#6d6f78] truncate">{tc.arguments}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Tool results */}
                          {trace.parsed_output?.tool_results && trace.parsed_output.tool_results.length > 0 && (
                            <div className="space-y-1">
                              {trace.parsed_output.tool_results.map((tr, i) => (
                                <div key={i} className="flex items-start gap-2">
                                  <span className={tr.status === 'success' ? 'text-green-400' : 'text-red-400'}>
                                    {tr.status === 'success' ? '✓' : '✗'}
                                  </span>
                                  <span className="text-[#6d6f78] font-mono text-[11px]">{tr.name || 'tool'}</span>
                                  <span className="text-[#6d6f78] truncate flex-1">{tr.preview?.slice(0, 60)}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Prompt (collapsible) */}
                          {trace.prompt && (
                            <details className="group/details">
                              <summary className="cursor-pointer text-[#949ba4] hover:text-white flex items-center gap-1">
                                <span className="text-yellow-500">▸</span>
                                Prompt
                              </summary>
                              <pre className="mt-2 p-2 rounded bg-[#1e1f22] text-[#949ba4] text-[11px] whitespace-pre-wrap overflow-x-auto">
                                {trace.prompt}
                              </pre>
                            </details>
                          )}

                          {/* Error */}
                          {trace.error && (
                            <div className="flex items-start gap-2 text-red-400">
                              <span>✗</span>
                              <span>{trace.error}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Sidebar - Agent Profile */}
      <div className="w-60 bg-[#2b2d31] border-l border-[#1f2023] flex flex-col">
        {/* Profile header */}
        <div
          className="h-[120px] relative"
          style={{ backgroundColor: agent.color + '40' }}
        >
          <div className="absolute -bottom-10 left-4">
            <div
              className="w-20 h-20 rounded-full flex items-center justify-center text-4xl border-[6px] border-[#2b2d31]"
              style={{ backgroundColor: agent.color + '30' }}
            >
              {agent.avatar}
            </div>
          </div>
        </div>

        <div className="mt-12 px-4 pb-4 flex-1 overflow-y-auto">
          {/* Name and role */}
          <div className="mb-4">
            <div className="text-xl font-semibold text-white">{agent.name}</div>
            <div className="text-sm text-[#949ba4]">{agent.role}</div>
          </div>

          {/* Divider */}
          <div className="h-px bg-[#3f4147] mb-4" />

          {/* About section */}
          {agentDetails?.exists && (
            <>
              <div className="mb-4">
                <div className="text-[11px] font-semibold text-white uppercase tracking-wide mb-2">About Me</div>
                <div className="text-sm text-[#dbdee1]">
                  {agentDetails.system_prompt?.slice(0, 200)}
                  {(agentDetails.system_prompt?.length || 0) > 200 && '...'}
                </div>
              </div>

              {/* Model */}
              <div className="mb-4">
                <div className="text-[11px] font-semibold text-white uppercase tracking-wide mb-2">Model</div>
                <div className="text-sm text-[#949ba4] font-mono">{agentDetails.model}</div>
              </div>

              {/* Tools */}
              {agentDetails.tools && agentDetails.tools.length > 0 && (
                <div className="mb-4">
                  <div className="text-[11px] font-semibold text-white uppercase tracking-wide mb-2">
                    Tools ({agentDetails.tools.length})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {agentDetails.tools.map((tool, i) => (
                      <span
                        key={i}
                        className="text-[11px] px-2 py-1 rounded bg-[#5865f2]/20 text-[#949ba4]"
                        title={tool.description}
                      >
                        {tool.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Memory blocks */}
              {agentDetails.memory_blocks && Object.keys(agentDetails.memory_blocks).length > 0 && (
                <div>
                  <div className="text-[11px] font-semibold text-white uppercase tracking-wide mb-2">Memory</div>
                  <div className="space-y-2">
                    {Object.entries(agentDetails.memory_blocks).slice(0, 4).map(([key, value]) => (
                      <div key={key} className="p-2 rounded bg-[#1e1f22]">
                        <div className="text-[11px] text-purple-400 font-mono mb-1">{key}</div>
                        <div className="text-[11px] text-[#949ba4] truncate">
                          {typeof value === 'string' ? value.slice(0, 50) : JSON.stringify(value).slice(0, 50)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {!agentDetails?.exists && (
            <div className="text-sm text-[#949ba4]">
              Agent not initialized yet. Wake them to create their profile.
            </div>
          )}
        </div>

        {/* Quick actions */}
        {selectedAgent === 'curator' && (
          <div className="p-3 border-t border-[#1f2023]">
            <button
              onClick={wakeCurator}
              disabled={waking}
              className="w-full py-2 rounded bg-[#23a559] hover:bg-[#1a7d41] text-white text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {waking ? 'Waking...' : '⚡ Wake Curator'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
