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

export default function AgentsDashboard() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

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

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000) // Refresh every 5s
    return () => clearInterval(interval)
  }, [])

  const runProductionAgent = async () => {
    setActionLoading('production')
    try {
      const res = await fetch(`${API_BASE}/agents/production/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skip_trends: true }),
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
            {actionLoading === 'production' ? 'Running...' : 'Run Production Agent'}
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
              <div className="text-xs font-mono text-text-tertiary mb-2">RECENT BRIEFS</div>
              {status.production_agent.recent_briefs.map((brief) => (
                <div
                  key={brief.id}
                  className="flex items-center justify-between p-2 bg-bg-tertiary rounded text-sm"
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
                  </div>
                  {brief.world_id && (
                    <Link
                      href={`/world/${brief.world_id}`}
                      className="text-neon-cyan hover:underline text-xs"
                    >
                      View World →
                    </Link>
                  )}
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
    </div>
  )
}
