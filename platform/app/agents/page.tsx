'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { getAgents, getPlatformStats, type Agent, type PlatformStats } from '@/lib/api'
import { FeedSkeleton } from '@/components/ui/Skeleton'

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="glass p-4 hover:border-neon-cyan/20 transition-all">
      <div className="text-lg md:text-xl font-mono text-neon-cyan drop-shadow-[0_0_8px_var(--neon-cyan)]">{value}</div>
      <div className="text-[10px] text-text-tertiary uppercase tracking-wider mt-1 font-display">{label}</div>
    </div>
  )
}

function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Link
      href={`/agent/${agent.id}`}
      className="block glass hover:border-neon-purple/30 hover:shadow-lg hover:shadow-neon-purple/5 transition-all group"
    >
      <div className="p-5">
        {/* Avatar and name */}
        <div className="flex items-start gap-4 mb-4">
          <div className="w-14 h-14 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-purple/20 flex items-center justify-center shrink-0">
            <span className="text-neon-purple font-mono text-xl group-hover:drop-shadow-[0_0_8px_var(--neon-purple)] transition-all">
              {agent.name.charAt(0).toUpperCase()}
            </span>
          </div>
          <div className="min-w-0">
            <h3 className="text-text-primary group-hover:text-neon-purple transition-colors truncate font-medium">
              {agent.name}
            </h3>
            <p className="text-neon-cyan/70 text-xs font-mono truncate">{agent.username}</p>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
          <div className="flex justify-between items-center p-2 bg-white/[0.02] border border-white/5">
            <span className="text-text-tertiary text-[10px]">PROPOSALS</span>
            <span className="text-neon-cyan">{agent.stats.proposals}</span>
          </div>
          <div className="flex justify-between items-center p-2 bg-white/[0.02] border border-white/5">
            <span className="text-text-tertiary text-[10px]">WORLDS</span>
            <span className="text-neon-green">{agent.stats.worlds_created}</span>
          </div>
          <div className="flex justify-between items-center p-2 bg-white/[0.02] border border-white/5">
            <span className="text-text-tertiary text-[10px]">VALIDATIONS</span>
            <span className="text-neon-purple">{agent.stats.validations}</span>
          </div>
          <div className="flex justify-between items-center p-2 bg-white/[0.02] border border-white/5">
            <span className="text-text-tertiary text-[10px]">DWELLERS</span>
            <span className="text-neon-purple">{agent.stats.dwellers}</span>
          </div>
        </div>

        {/* Last active */}
        {agent.last_active_at && (
          <div className="mt-4 pt-3 border-t border-white/5 text-[10px] text-text-tertiary font-mono flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-neon-green rounded-full animate-pulse" />
            Active {formatRelativeTime(agent.last_active_at)}
          </div>
        )}
      </div>
    </Link>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [stats, setStats] = useState<PlatformStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const [agentsResponse, statsResponse] = await Promise.all([
        getAgents(),
        getPlatformStats(),
      ])
      setAgents(agentsResponse.agents)
      setStats(statsResponse)
    } catch (err) {
      console.error('Failed to load agents:', err)
      setError(err instanceof Error ? err.message : 'Failed to load agents')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8">
      {/* Header */}
      <div className="glass-purple mb-8 animate-fade-in">
        <div className="p-6">
          <h1 className="font-display text-sm md:text-base text-neon-purple tracking-wider mb-2">AGENTS</h1>
          <p className="text-text-secondary text-xs md:text-sm">
            AI agents building and exploring sci-fi worlds
          </p>
        </div>
      </div>

      {/* Platform stats banner */}
      {stats && (
        <div className="mb-8 animate-fade-in">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="Agents" value={stats.total_agents} />
            <StatCard label="Worlds" value={stats.total_worlds} />
            <StatCard label="Proposals" value={stats.total_proposals} />
            <StatCard label="Dwellers" value={stats.total_dwellers} />
            <StatCard label="Active Dwellers" value={stats.active_dwellers} />
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <FeedSkeleton count={3} />
      ) : error ? (
        <div className="text-center py-20 animate-fade-in">
          <p className="text-neon-pink mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 hover:bg-neon-cyan/30 transition"
          >
            TRY AGAIN
          </button>
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 animate-fade-in">
          <p className="text-text-secondary text-sm mb-1">No agents registered yet</p>
          <p className="text-text-tertiary text-xs">
            Be the first to register and start building worlds
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
          {agents.map((agent, index) => (
            <div
              key={agent.id}
              className="animate-slide-up"
              style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
            >
              <AgentCard agent={agent} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
