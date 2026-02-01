'use client'

import { useEffect, useState, useRef, useCallback, ReactNode } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

// Pixel-style icons (8x8 grid based)
const Icons = {
  // Curator - crystal/eye orb
  curator: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="5" y="2" width="6" height="2" fill="currentColor" opacity="0.5"/>
      <rect x="3" y="4" width="10" height="2" fill="currentColor" opacity="0.7"/>
      <rect x="2" y="6" width="12" height="4" fill="currentColor"/>
      <rect x="6" y="7" width="4" height="2" fill="var(--bg-primary)"/>
      <rect x="3" y="10" width="10" height="2" fill="currentColor" opacity="0.7"/>
      <rect x="5" y="12" width="6" height="2" fill="currentColor" opacity="0.5"/>
    </svg>
  ),
  // Architect - building blocks
  architect: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="2" y="10" width="4" height="4" fill="currentColor"/>
      <rect x="6" y="6" width="4" height="8" fill="currentColor" opacity="0.8"/>
      <rect x="10" y="8" width="4" height="6" fill="currentColor" opacity="0.6"/>
      <rect x="4" y="2" width="4" height="4" fill="currentColor" opacity="0.7"/>
    </svg>
  ),
  // Editor - pencil
  editor: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="12" y="1" width="2" height="2" fill="currentColor"/>
      <rect x="10" y="3" width="2" height="2" fill="currentColor"/>
      <rect x="8" y="5" width="2" height="2" fill="currentColor"/>
      <rect x="6" y="7" width="2" height="2" fill="currentColor"/>
      <rect x="4" y="9" width="2" height="2" fill="currentColor"/>
      <rect x="2" y="11" width="2" height="2" fill="currentColor"/>
      <rect x="1" y="13" width="2" height="2" fill="currentColor" opacity="0.5"/>
    </svg>
  ),
  // Home - constellation/stars
  home: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="7" y="2" width="2" height="2" fill="currentColor"/>
      <rect x="3" y="5" width="2" height="2" fill="currentColor" opacity="0.7"/>
      <rect x="11" y="4" width="2" height="2" fill="currentColor" opacity="0.8"/>
      <rect x="5" y="9" width="2" height="2" fill="currentColor" opacity="0.6"/>
      <rect x="9" y="8" width="2" height="2" fill="currentColor"/>
      <rect x="12" y="11" width="2" height="2" fill="currentColor" opacity="0.5"/>
      <rect x="2" y="12" width="2" height="2" fill="currentColor" opacity="0.4"/>
    </svg>
  ),
  // Lightning bolt
  bolt: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="8" y="1" width="2" height="2" fill="currentColor"/>
      <rect x="6" y="3" width="4" height="2" fill="currentColor"/>
      <rect x="4" y="5" width="6" height="2" fill="currentColor"/>
      <rect x="6" y="7" width="4" height="2" fill="currentColor"/>
      <rect x="8" y="9" width="2" height="2" fill="currentColor"/>
      <rect x="6" y="11" width="2" height="2" fill="currentColor"/>
      <rect x="4" y="13" width="2" height="2" fill="currentColor"/>
    </svg>
  ),
  // Sparkle/new
  sparkle: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="7" y="1" width="2" height="4" fill="currentColor"/>
      <rect x="7" y="11" width="2" height="4" fill="currentColor"/>
      <rect x="1" y="7" width="4" height="2" fill="currentColor"/>
      <rect x="11" y="7" width="4" height="2" fill="currentColor"/>
      <rect x="3" y="3" width="2" height="2" fill="currentColor" opacity="0.5"/>
      <rect x="11" y="3" width="2" height="2" fill="currentColor" opacity="0.5"/>
      <rect x="3" y="11" width="2" height="2" fill="currentColor" opacity="0.5"/>
      <rect x="11" y="11" width="2" height="2" fill="currentColor" opacity="0.5"/>
    </svg>
  ),
  // Warning triangle
  warning: (
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="none">
      <rect x="7" y="2" width="2" height="2" fill="currentColor"/>
      <rect x="6" y="4" width="4" height="2" fill="currentColor"/>
      <rect x="5" y="6" width="6" height="2" fill="currentColor"/>
      <rect x="4" y="8" width="8" height="2" fill="currentColor"/>
      <rect x="3" y="10" width="10" height="2" fill="currentColor"/>
      <rect x="2" y="12" width="12" height="2" fill="currentColor"/>
      <rect x="7" y="6" width="2" height="4" fill="var(--bg-primary)"/>
      <rect x="7" y="11" width="2" height="1" fill="var(--bg-primary)"/>
    </svg>
  ),
  // Diamond/tool
  diamond: (
    <svg width="1em" height="1em" viewBox="0 0 8 8" fill="none">
      <rect x="3" y="1" width="2" height="2" fill="currentColor"/>
      <rect x="1" y="3" width="6" height="2" fill="currentColor"/>
      <rect x="3" y="5" width="2" height="2" fill="currentColor"/>
    </svg>
  ),
  // Checkmark
  check: (
    <svg width="1em" height="1em" viewBox="0 0 12 12" fill="none">
      <rect x="1" y="5" width="2" height="2" fill="currentColor"/>
      <rect x="3" y="7" width="2" height="2" fill="currentColor"/>
      <rect x="5" y="5" width="2" height="2" fill="currentColor"/>
      <rect x="7" y="3" width="2" height="2" fill="currentColor"/>
      <rect x="9" y="1" width="2" height="2" fill="currentColor"/>
    </svg>
  ),
  // X/cross
  cross: (
    <svg width="1em" height="1em" viewBox="0 0 12 12" fill="none">
      <rect x="1" y="1" width="2" height="2" fill="currentColor"/>
      <rect x="9" y="1" width="2" height="2" fill="currentColor"/>
      <rect x="3" y="3" width="2" height="2" fill="currentColor"/>
      <rect x="7" y="3" width="2" height="2" fill="currentColor"/>
      <rect x="5" y="5" width="2" height="2" fill="currentColor"/>
      <rect x="3" y="7" width="2" height="2" fill="currentColor"/>
      <rect x="7" y="7" width="2" height="2" fill="currentColor"/>
      <rect x="1" y="9" width="2" height="2" fill="currentColor"/>
      <rect x="9" y="9" width="2" height="2" fill="currentColor"/>
    </svg>
  ),
}

// Agent profiles
const AGENTS: Record<string, { name: string; avatar: ReactNode; role: string; status: string }> = {
  curator: {
    name: 'Curator',
    avatar: Icons.curator,
    role: 'Trend Research & World Ideas',
    status: 'online',
  },
  architect: {
    name: 'Architect',
    avatar: Icons.architect,
    role: 'World Building',
    status: 'offline',
  },
  editor: {
    name: 'Editor',
    avatar: Icons.editor,
    role: 'Quality Review',
    status: 'offline',
  },
}

type AgentKey = 'curator' | 'architect' | 'editor'

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
  agent_created?: boolean
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

  const fetchTraces = useCallback(async (agent: AgentKey) => {
    try {
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
      fetchTraces('curator')
    } catch (err) {
      console.error('Failed to wake curator:', err)
      setLastWakeResult({ status: 'error', error: String(err) })
    } finally {
      setWaking(false)
    }
  }

  useEffect(() => {
    // Clear previous agent's data when switching
    setTraces([])
    setLastWakeResult(null)
    setAgentDetails(null)

    fetchAgentDetails(selectedAgent)
    fetchTraces(selectedAgent)
    fetchStats()
  }, [selectedAgent, fetchAgentDetails, fetchTraces, fetchStats])

  useEffect(() => {
    const interval = setInterval(() => {
      fetchTraces(selectedAgent)
    }, 5000)
    return () => clearInterval(interval)
  }, [selectedAgent, fetchTraces])

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffSec = Math.floor(diffMs / 1000)
    const diffMin = Math.floor(diffSec / 60)
    const diffHour = Math.floor(diffMin / 60)

    // Handle future timestamps or negative values (time sync issues)
    if (diffSec < 0) return 'just now'

    // Show relative time for recent events
    if (diffSec < 60) return diffSec === 0 ? 'just now' : `${diffSec}s ago`
    if (diffMin < 60) return `${diffMin}m ago`
    if (diffHour < 24) return `${diffHour}h ago`

    // Fall back to absolute time for older events
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })
  }

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
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

  const tracesByDate = traces.reduce((acc, trace) => {
    const date = formatDate(trace.timestamp)
    if (!acc[date]) acc[date] = []
    acc[date].push(trace)
    return acc
  }, {} as Record<string, AgentTrace[]>)

  const agent = AGENTS[selectedAgent]

  return (
    <div className="studio-layout">
      {/* Left Sidebar - Agent list */}
      <nav className="studio-nav">
        <div className="studio-nav__home">{Icons.home}</div>
        <div className="studio-nav__divider" />
        {(Object.keys(AGENTS) as AgentKey[]).map((key) => {
          const a = AGENTS[key]
          const isSelected = selectedAgent === key
          return (
            <button
              key={key}
              onClick={() => setSelectedAgent(key)}
              className={`studio-nav__agent ${isSelected ? 'studio-nav__agent--active' : ''}`}
              title={a.name}
            >
              <span className="studio-nav__avatar">{a.avatar}</span>
              <span className={`studio-nav__status ${a.status === 'online' ? 'studio-nav__status--online' : ''}`} />
              {isSelected && <span className="studio-nav__indicator" />}
            </button>
          )
        })}
      </nav>

      {/* Channel Sidebar */}
      <aside className="studio-sidebar">
        <header className="studio-sidebar__header">
          <span className="studio-sidebar__title">Deep Sci-Fi Studio</span>
        </header>

        <div className="studio-sidebar__profile">
          <div className="studio-sidebar__avatar">{agent.avatar}</div>
          <div className="studio-sidebar__info">
            <div className="studio-sidebar__name">{agent.name}</div>
            <div className="studio-sidebar__role">{agent.role}</div>
          </div>
        </div>

        <div className="studio-sidebar__channels">
          <div className="studio-sidebar__section">Activity</div>
          <button className="studio-sidebar__channel studio-sidebar__channel--active">
            <span className="studio-sidebar__hash">#</span>
            <span>history</span>
            {traces.length > 0 && <span className="studio-sidebar__badge">{traces.length}</span>}
          </button>

          <div className="studio-sidebar__section">Actions</div>
          {selectedAgent === 'curator' && (
            <button
              onClick={wakeCurator}
              disabled={waking}
              className="studio-sidebar__action"
            >
              <span>{Icons.bolt}</span>
              <span>{waking ? 'Waking...' : 'Wake Curator'}</span>
            </button>
          )}
        </div>

        <footer className="studio-sidebar__stats">
          <div className="studio-sidebar__stat">
            <span>Worlds</span>
            <span>{stats?.total_worlds || 0}</span>
          </div>
          <div className="studio-sidebar__stat">
            <span>Briefs</span>
            <span className="studio-sidebar__stat--pending">{stats?.pending_briefs || 0}</span>
          </div>
        </footer>
      </aside>

      {/* Main Content */}
      <main className="studio-main">
        <header className="studio-main__header">
          <span className="studio-main__hash">#</span>
          <span className="studio-main__channel">history</span>
          <span className="studio-main__sep">|</span>
          <span className="studio-main__desc">{agent.name}&apos;s activity</span>
        </header>

        <div ref={historyRef} className="studio-main__content">
          {/* Loading state while waking */}
          {waking && (
            <article className="studio-message studio-message--loading">
              <div className="studio-message__header">
                <span className="studio-message__avatar">{agent.avatar}</span>
                <span className="studio-message__name">{agent.name}</span>
                <span className="studio-message__time">waking up...</span>
              </div>
              <div className="studio-message__loading">
                <span className="studio-loading__dot" />
                <span className="studio-loading__dot" />
                <span className="studio-loading__dot" />
                <span className="studio-loading__text">Thinking...</span>
              </div>
            </article>
          )}

          {/* Latest wake result */}
          {!waking && lastWakeResult && (
            <article className="studio-message studio-message--highlight">
              <div className="studio-message__header">
                <span className="studio-message__avatar">{agent.avatar}</span>
                <span className="studio-message__name">{agent.name}</span>
                <span className="studio-message__time">just now</span>
                {lastWakeResult.duration_ms && (
                  <span className="studio-message__duration">{formatDuration(lastWakeResult.duration_ms)}</span>
                )}
              </div>

              {/* Show if agent was newly created */}
              {lastWakeResult.agent_created && (
                <div className="studio-message__notice studio-message__notice--created">
                  {Icons.sparkle} Agent created - this is their first wake
                </div>
              )}

              {lastWakeResult.response && (
                <div className="studio-message__text">{lastWakeResult.response}</div>
              )}

              {lastWakeResult.trace && (
                <div className="studio-message__trace">
                  {lastWakeResult.trace.tool_results.length > 0 && (
                    <div className="studio-trace__results">
                      {lastWakeResult.trace.tool_results.map((tr, i) => (
                        <div key={i} className={`studio-trace__result ${tr.status === 'success' ? 'studio-trace__result--success' : 'studio-trace__result--error'}`}>
                          <span>{tr.status === 'success' ? Icons.check : Icons.cross}</span>
                          <span className="studio-trace__result-name">{tr.name || 'unknown'}</span>
                          <span className="studio-trace__result-preview">{tr.preview?.slice(0, 80)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {lastWakeResult.trace.reasoning.length > 0 && (
                    <details className="studio-trace__reasoning">
                      <summary>Reasoning ({lastWakeResult.trace.reasoning.length} steps)</summary>
                      <div className="studio-trace__reasoning-content">
                        {lastWakeResult.trace.reasoning.map((r, i) => (
                          <p key={i}>{r}</p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              )}

              {lastWakeResult.error && (
                <div className="studio-message__error">
                  <span className="studio-message__error-icon">{Icons.warning}</span>
                  <span>{lastWakeResult.error}</span>
                </div>
              )}
            </article>
          )}

          {/* History */}
          {Object.keys(tracesByDate).length === 0 ? (
            <div className="studio-empty">
              <div className="studio-empty__avatar">{agent.avatar}</div>
              <div className="studio-empty__title">Welcome to #{agent.name.toLowerCase()}</div>
              <div className="studio-empty__text">
                This is the beginning of {agent.name}&apos;s history.
                {selectedAgent === 'curator' && ' Click Wake Curator to see them in action.'}
              </div>
            </div>
          ) : (
            Object.entries(tracesByDate).map(([date, dateTraces]) => (
              <div key={date}>
                <div className="studio-divider">
                  <span>{date}</span>
                </div>

                {dateTraces.map((trace) => (
                  <article key={trace.id} className="studio-message">
                    <div className="studio-message__header">
                      <span className="studio-message__avatar">{agent.avatar}</span>
                      <span className="studio-message__name">{agent.name}</span>
                      <span className="studio-message__time">{formatTime(trace.timestamp)}</span>
                      <span className="studio-message__op">{trace.operation}</span>
                      {trace.duration_ms && (
                        <span className="studio-message__duration">{formatDuration(trace.duration_ms)}</span>
                      )}
                    </div>

                    {trace.response && (
                      <div className="studio-message__text">
                        {trace.response.length > 500 ? trace.response.slice(0, 500) + '...' : trace.response}
                      </div>
                    )}

                    {trace.parsed_output?.tool_results && trace.parsed_output.tool_results.length > 0 && (
                      <div className="studio-message__trace">
                        <div className="studio-trace__results">
                          {trace.parsed_output.tool_results.map((tr, i) => (
                            <div key={i} className={`studio-trace__result ${tr.status === 'success' ? 'studio-trace__result--success' : 'studio-trace__result--error'}`}>
                              <span>{tr.status === 'success' ? Icons.check : Icons.cross}</span>
                              <span className="studio-trace__result-name">{tr.name || 'unknown'}</span>
                              <span className="studio-trace__result-preview">{tr.preview?.slice(0, 60)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {trace.error && (
                      <div className="studio-message__error">{trace.error}</div>
                    )}
                  </article>
                ))}
              </div>
            ))
          )}
        </div>
      </main>

      {/* Right Sidebar - Profile */}
      <aside className="studio-profile">
        <div className="studio-profile__banner" />
        <div className="studio-profile__avatar-wrap">
          <div className="studio-profile__avatar">{agent.avatar}</div>
        </div>

        <div className="studio-profile__content">
          <div className="studio-profile__name">{agent.name}</div>
          <div className="studio-profile__role">{agent.role}</div>

          <div className="studio-profile__divider" />

          {agentDetails?.exists ? (
            <>
              <div className="studio-profile__section">
                <div className="studio-profile__label">Model</div>
                <div className="studio-profile__value studio-profile__value--mono">{agentDetails.model}</div>
              </div>

              {agentDetails.tools && agentDetails.tools.length > 0 && (
                <div className="studio-profile__section">
                  <div className="studio-profile__label">Tools ({agentDetails.tools.length})</div>
                  <div className="studio-profile__tools">
                    {agentDetails.tools.map((tool, i) => (
                      <span key={i} className="studio-profile__tool" title={tool.description}>
                        {tool.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {agentDetails.memory_blocks && Object.keys(agentDetails.memory_blocks).length > 0 && (
                <div className="studio-profile__section">
                  <div className="studio-profile__label">Memory</div>
                  <div className="studio-profile__memory">
                    {Object.entries(agentDetails.memory_blocks).slice(0, 4).map(([key, value]) => (
                      <div key={key} className="studio-profile__memory-block">
                        <div className="studio-profile__memory-key">{key}</div>
                        <div className="studio-profile__memory-val">
                          {typeof value === 'string' ? value.slice(0, 50) : JSON.stringify(value).slice(0, 50)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="studio-profile__empty">Agent not initialized. Wake them to create profile.</div>
          )}
        </div>

        {selectedAgent === 'curator' && (
          <div className="studio-profile__actions">
            <button onClick={wakeCurator} disabled={waking} className="studio-profile__wake">
              {waking ? 'Waking...' : <>{Icons.bolt} Wake Curator</>}
            </button>
          </div>
        )}
      </aside>

      <style jsx>{`
        /* CSS Variables - Deep Sci-Fi brand from v0 */
        .studio-layout {
          --bg-primary: #000000;
          --bg-secondary: #0a0a0a;
          --bg-tertiary: #0f0f0f;
          --bg-hover: #151515;
          --text-primary: #c8c8c8;
          --text-secondary: #8a8a8a;
          --text-tertiary: #5a5a5a;
          --text-muted: #3a3a3a;
          --neon-cyan: #00ffcc;
          --neon-purple: #aa00ff;
          --border-subtle: rgba(255, 255, 255, 0.06);
          --border-medium: rgba(255, 255, 255, 0.12);
          --border-accent: rgba(0, 255, 204, 0.3);
          --font-mono: 'Berkeley Mono', 'SF Mono', 'JetBrains Mono', monospace;
          --font-sans: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
        }

        /* Layout - fill container, no overflow */
        .studio-layout {
          display: flex;
          height: 100%;
          width: 100%;
          overflow: hidden;
          background: var(--bg-primary);
          color: var(--text-primary);
          font-family: var(--font-sans);
          font-size: 12px;
        }

        /* Left Nav */
        .studio-nav {
          width: 60px;
          min-width: 60px;
          height: 100%;
          background: var(--bg-secondary);
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 12px 0;
          gap: 8px;
          border-right: 1px solid var(--border-subtle);
          overflow-y: auto;
        }

        .studio-nav__home {
          width: 40px;
          height: 40px;
          border-radius: 12px;
          background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          margin-bottom: 8px;
        }

        .studio-nav__divider {
          width: 24px;
          height: 1px;
          background: var(--border-subtle);
          margin-bottom: 8px;
        }

        .studio-nav__agent {
          position: relative;
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: var(--bg-tertiary);
          border: none;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .studio-nav__agent:hover,
        .studio-nav__agent--active {
          border-radius: 12px;
          background: var(--bg-hover);
        }

        .studio-nav__agent--active {
          box-shadow: 0 0 0 1px var(--neon-cyan);
        }

        .studio-nav__avatar {
          font-size: 18px;
        }

        .studio-nav__status {
          position: absolute;
          bottom: 0;
          right: 0;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--text-muted);
          border: 2px solid var(--bg-secondary);
        }

        .studio-nav__status--online {
          background: var(--neon-cyan);
          box-shadow: 0 0 6px var(--neon-cyan);
        }

        .studio-nav__indicator {
          position: absolute;
          left: -8px;
          width: 3px;
          height: 24px;
          background: var(--neon-cyan);
          border-radius: 0 3px 3px 0;
        }

        /* Sidebar */
        .studio-sidebar {
          width: 200px;
          min-width: 200px;
          height: 100%;
          background: var(--bg-secondary);
          display: flex;
          flex-direction: column;
          border-right: 1px solid var(--border-subtle);
          overflow: hidden;
        }

        .studio-sidebar__header {
          height: 44px;
          padding: 0 12px;
          display: flex;
          align-items: center;
          border-bottom: 1px solid var(--border-subtle);
        }

        .studio-sidebar__title {
          font-family: var(--font-mono);
          font-size: 11px;
          color: var(--neon-cyan);
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }

        .studio-sidebar__profile {
          padding: 12px;
          border-bottom: 1px solid var(--border-subtle);
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .studio-sidebar__avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background: var(--bg-tertiary);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 16px;
        }

        .studio-sidebar__info {
          flex: 1;
          min-width: 0;
        }

        .studio-sidebar__name {
          font-size: 13px;
          font-weight: 500;
          color: var(--text-primary);
        }

        .studio-sidebar__role {
          font-size: 10px;
          color: var(--text-tertiary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .studio-sidebar__channels {
          flex: 1;
          min-height: 0;
          padding: 12px 8px;
          overflow-y: auto;
        }

        .studio-sidebar__section {
          font-size: 10px;
          font-weight: 600;
          color: var(--text-tertiary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 8px 8px 4px;
        }

        .studio-sidebar__channel {
          display: flex;
          align-items: center;
          gap: 6px;
          width: 100%;
          padding: 6px 8px;
          border: none;
          background: transparent;
          color: var(--text-secondary);
          font-size: 12px;
          border-radius: 4px;
          cursor: pointer;
          text-align: left;
        }

        .studio-sidebar__channel:hover,
        .studio-sidebar__channel--active {
          background: var(--bg-hover);
          color: var(--text-primary);
        }

        .studio-sidebar__hash {
          color: var(--text-muted);
          font-size: 14px;
        }

        .studio-sidebar__badge {
          margin-left: auto;
          font-size: 10px;
          background: var(--neon-cyan);
          color: var(--bg-primary);
          padding: 1px 5px;
          border-radius: 8px;
        }

        .studio-sidebar__action {
          display: flex;
          align-items: center;
          gap: 6px;
          width: 100%;
          padding: 6px 8px;
          border: none;
          background: transparent;
          color: var(--neon-cyan);
          font-size: 12px;
          border-radius: 4px;
          cursor: pointer;
          text-align: left;
        }

        .studio-sidebar__action:hover:not(:disabled) {
          background: rgba(0, 255, 204, 0.1);
        }

        .studio-sidebar__action:disabled {
          opacity: 0.5;
        }

        .studio-sidebar__stats {
          padding: 12px;
          border-top: 1px solid var(--border-subtle);
          font-size: 10px;
        }

        .studio-sidebar__stat {
          display: flex;
          justify-content: space-between;
          padding: 3px 0;
          color: var(--text-tertiary);
        }

        .studio-sidebar__stat--pending {
          color: var(--neon-purple);
        }

        /* Main Content */
        .studio-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
          min-height: 0;
          height: 100%;
          background: var(--bg-primary);
          overflow: hidden;
        }

        .studio-main__header {
          height: 44px;
          min-height: 44px;
          padding: 0 16px;
          display: flex;
          align-items: center;
          gap: 8px;
          border-bottom: 1px solid var(--border-subtle);
        }

        .studio-main__hash {
          color: var(--text-muted);
          font-size: 16px;
        }

        .studio-main__channel {
          font-weight: 500;
          color: var(--text-primary);
        }

        .studio-main__sep {
          color: var(--text-muted);
        }

        .studio-main__desc {
          color: var(--text-tertiary);
          font-size: 11px;
        }

        .studio-main__content {
          flex: 1;
          min-height: 0;
          overflow-y: auto;
          overflow-x: hidden;
          padding: 16px;
        }

        /* Messages */
        .studio-message {
          padding: 12px;
          border-radius: 4px;
          margin-bottom: 8px;
        }

        .studio-message:hover {
          background: var(--bg-secondary);
        }

        .studio-message--highlight {
          background: var(--bg-secondary);
          border: 1px solid var(--border-accent);
        }

        .studio-message--loading {
          background: var(--bg-secondary);
          border: 1px solid var(--neon-cyan);
          animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        .studio-message__loading {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 8px 0;
        }

        .studio-loading__dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--neon-cyan);
          animation: bounce 1.4s ease-in-out infinite;
        }

        .studio-loading__dot:nth-child(1) { animation-delay: 0s; }
        .studio-loading__dot:nth-child(2) { animation-delay: 0.2s; }
        .studio-loading__dot:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }

        .studio-loading__text {
          margin-left: 8px;
          color: var(--text-secondary);
          font-size: 12px;
        }

        .studio-message__header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 6px;
          flex-wrap: wrap;
        }

        .studio-message__avatar {
          font-size: 16px;
        }

        .studio-message__name {
          font-weight: 500;
          color: var(--text-primary);
        }

        .studio-message__time {
          font-size: 10px;
          color: var(--text-muted);
        }

        .studio-message__op {
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 3px;
          background: var(--bg-tertiary);
          color: var(--text-tertiary);
        }

        .studio-message__duration {
          font-size: 10px;
          color: var(--text-muted);
          font-family: var(--font-mono);
        }

        .studio-message__text {
          color: var(--text-primary);
          line-height: 1.5;
          word-wrap: break-word;
          overflow-wrap: break-word;
          white-space: pre-wrap;
        }

        .studio-message__notice {
          font-size: 11px;
          margin: 8px 0;
          padding: 6px 10px;
          border-radius: 4px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .studio-message__notice--created {
          background: rgba(0, 255, 204, 0.1);
          border: 1px solid rgba(0, 255, 204, 0.3);
          color: var(--neon-cyan);
        }

        .studio-message__error {
          color: #ff6b6b;
          font-size: 12px;
          margin-top: 8px;
          padding: 10px 12px;
          background: rgba(255, 107, 107, 0.1);
          border: 1px solid rgba(255, 107, 107, 0.3);
          border-radius: 4px;
          display: flex;
          align-items: flex-start;
          gap: 8px;
        }

        .studio-message__error-icon {
          flex-shrink: 0;
        }

        .studio-message__trace {
          margin-top: 10px;
          font-size: 11px;
        }

        /* Trace styling */
        .studio-trace__results {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .studio-trace__result {
          display: flex;
          align-items: flex-start;
          gap: 6px;
        }

        .studio-trace__result--success {
          color: var(--neon-cyan);
        }

        .studio-trace__result--error {
          color: #ff6b6b;
        }

        .studio-trace__result-name {
          font-family: var(--font-mono);
          color: var(--text-tertiary);
        }

        .studio-trace__result-preview {
          color: var(--text-muted);
          word-break: break-all;
          flex: 1;
          min-width: 0;
        }

        .studio-trace__reasoning {
          margin-top: 8px;
        }

        .studio-trace__reasoning summary {
          cursor: pointer;
          color: var(--neon-purple);
          font-size: 11px;
        }

        .studio-trace__reasoning-content {
          margin-top: 8px;
          padding-left: 12px;
          border-left: 2px solid var(--neon-purple);
          color: var(--text-secondary);
          font-style: italic;
        }

        .studio-trace__reasoning-content p {
          margin-bottom: 8px;
          word-wrap: break-word;
        }

        /* Divider */
        .studio-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 16px 0 12px 0;
        }

        /* Remove top margin from first divider */
        .studio-main__content > div:first-child .studio-divider,
        .studio-main__content > article:first-child + div .studio-divider {
          margin-top: 0;
        }

        .studio-divider::before,
        .studio-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: var(--border-subtle);
        }

        .studio-divider span {
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        /* Empty state */
        .studio-empty {
          text-align: center;
          padding: 60px 20px;
        }

        .studio-empty__avatar {
          font-size: 48px;
          margin-bottom: 16px;
        }

        .studio-empty__title {
          font-size: 18px;
          font-weight: 500;
          color: var(--text-primary);
          margin-bottom: 8px;
        }

        .studio-empty__text {
          color: var(--text-tertiary);
          font-size: 13px;
        }

        /* Right Profile */
        .studio-profile {
          width: 200px;
          min-width: 200px;
          height: 100%;
          background: var(--bg-secondary);
          display: flex;
          flex-direction: column;
          border-left: 1px solid var(--border-subtle);
          overflow: hidden;
        }

        .studio-profile__banner {
          height: 80px;
          background: linear-gradient(135deg, var(--neon-cyan), var(--neon-purple));
          opacity: 0.3;
        }

        .studio-profile__avatar-wrap {
          margin-top: -30px;
          padding: 0 16px;
        }

        .studio-profile__avatar {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: var(--bg-secondary);
          border: 4px solid var(--bg-secondary);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 28px;
        }

        .studio-profile__content {
          flex: 1;
          min-height: 0;
          padding: 12px 16px;
          overflow-y: auto;
        }

        .studio-profile__name {
          font-size: 16px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .studio-profile__role {
          font-size: 11px;
          color: var(--text-tertiary);
          margin-bottom: 12px;
        }

        .studio-profile__divider {
          height: 1px;
          background: var(--border-subtle);
          margin: 12px 0;
        }

        .studio-profile__section {
          margin-bottom: 16px;
        }

        .studio-profile__label {
          font-size: 10px;
          font-weight: 600;
          color: var(--text-primary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 6px;
        }

        .studio-profile__value {
          font-size: 11px;
          color: var(--text-secondary);
        }

        .studio-profile__value--mono {
          font-family: var(--font-mono);
          word-break: break-all;
        }

        .studio-profile__tools {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .studio-profile__tool {
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 3px;
          background: var(--bg-tertiary);
          color: var(--text-tertiary);
        }

        .studio-profile__memory {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .studio-profile__memory-block {
          padding: 6px;
          border-radius: 4px;
          background: var(--bg-tertiary);
        }

        .studio-profile__memory-key {
          font-size: 10px;
          font-family: var(--font-mono);
          color: var(--neon-purple);
          margin-bottom: 2px;
        }

        .studio-profile__memory-val {
          font-size: 10px;
          color: var(--text-muted);
          word-break: break-all;
        }

        .studio-profile__empty {
          font-size: 11px;
          color: var(--text-muted);
        }

        .studio-profile__actions {
          padding: 12px;
          border-top: 1px solid var(--border-subtle);
        }

        .studio-profile__wake {
          width: 100%;
          padding: 8px;
          border: none;
          border-radius: 4px;
          background: var(--neon-cyan);
          color: var(--bg-primary);
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .studio-profile__wake:hover:not(:disabled) {
          filter: brightness(1.1);
          box-shadow: 0 0 12px var(--neon-cyan);
        }

        .studio-profile__wake:disabled {
          opacity: 0.5;
        }

        /* Scrollbar styling */
        .studio-main__content::-webkit-scrollbar,
        .studio-sidebar__channels::-webkit-scrollbar,
        .studio-profile__content::-webkit-scrollbar {
          width: 6px;
        }

        .studio-main__content::-webkit-scrollbar-track,
        .studio-sidebar__channels::-webkit-scrollbar-track,
        .studio-profile__content::-webkit-scrollbar-track {
          background: transparent;
        }

        .studio-main__content::-webkit-scrollbar-thumb,
        .studio-sidebar__channels::-webkit-scrollbar-thumb,
        .studio-profile__content::-webkit-scrollbar-thumb {
          background: var(--border-medium);
          border-radius: 3px;
        }

        .studio-main__content::-webkit-scrollbar-thumb:hover,
        .studio-sidebar__channels::-webkit-scrollbar-thumb:hover,
        .studio-profile__content::-webkit-scrollbar-thumb:hover {
          background: var(--text-muted);
        }
      `}</style>
    </div>
  )
}
