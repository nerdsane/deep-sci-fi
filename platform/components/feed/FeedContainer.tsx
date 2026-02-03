'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { getFeed, type FeedItem } from '@/lib/api'
import { FeedSkeleton } from '@/components/ui/Skeleton'

// Format relative time
function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z')
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

// Verdict color/icon
function VerdictBadge({ verdict }: { verdict: string }) {
  const config = {
    approve: { color: 'text-neon-green bg-neon-green/10 border-neon-green/30', label: 'APPROVED' },
    strengthen: { color: 'text-neon-yellow bg-neon-yellow/10 border-neon-yellow/30', label: 'STRENGTHEN' },
    reject: { color: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30', label: 'REJECTED' },
  }[verdict] || { color: 'text-text-secondary bg-white/5 border-white/10', label: verdict.toUpperCase() }

  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${config.color}`}>
      {config.label}
    </span>
  )
}

// Status badge for proposals/aspects
function StatusBadge({ status }: { status: string }) {
  const config = {
    validating: { color: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30', label: 'VALIDATING' },
    approved: { color: 'text-neon-green bg-neon-green/10 border-neon-green/30', label: 'APPROVED' },
    rejected: { color: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30', label: 'REJECTED' },
    draft: { color: 'text-text-tertiary bg-white/5 border-white/10', label: 'DRAFT' },
  }[status] || { color: 'text-text-secondary bg-white/5 border-white/10', label: status.toUpperCase() }

  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${config.color}`}>
      {config.label}
    </span>
  )
}

// Agent link
function AgentLink({ agent }: { agent: { id: string; username: string; name: string } }) {
  return (
    <Link
      href={`/agent/${agent.id}`}
      className="text-neon-cyan hover:text-neon-cyan-bright transition-colors"
    >
      {agent.username}
    </Link>
  )
}

// World link
function WorldLink({ world }: { world: { id: string; name: string; year_setting: number } }) {
  return (
    <Link
      href={`/world/${world.id}`}
      className="text-text-primary hover:text-neon-cyan transition-colors"
    >
      {world.name}
      <span className="text-text-tertiary ml-1">({world.year_setting})</span>
    </Link>
  )
}

// Activity type icon
function ActivityIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    world_created: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
    ),
    proposal_submitted: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="12" y1="18" x2="12" y2="12" />
        <line x1="9" y1="15" x2="15" y2="15" />
      </svg>
    ),
    proposal_validated: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
    ),
    aspect_proposed: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
    aspect_approved: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
    dweller_created: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
    ),
    dweller_action: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    agent_registered: (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="8.5" cy="7" r="4" />
        <line x1="20" y1="8" x2="20" y2="14" />
        <line x1="23" y1="11" x2="17" y2="11" />
      </svg>
    ),
  }
  return <span className="text-text-tertiary">{icons[type] || icons.proposal_submitted}</span>
}

// Individual feed item card
function FeedItemCard({ item }: { item: FeedItem }) {
  return (
    <div className="bg-bg-tertiary border border-white/5 hover:border-white/10 transition-colors">
      <div className="p-4">
        {/* Header: icon + type + time */}
        <div className="flex items-center gap-2 mb-3">
          <ActivityIcon type={item.type} />
          <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            {item.type.replace(/_/g, ' ')}
          </span>
          <span className="text-text-tertiary text-[10px]">•</span>
          <span className="text-text-tertiary text-xs">
            {formatRelativeTime(item.created_at)}
          </span>
        </div>

        {/* Content based on type */}
        {item.type === 'world_created' && item.world && (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-lg text-text-primary mb-1">
                  <WorldLink world={item.world} />
                </h3>
                <p className="text-text-secondary text-sm line-clamp-2">{item.world.premise}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-2xl font-mono text-neon-cyan">{item.world.year_setting}</div>
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Created by <AgentLink agent={item.agent} />
              </div>
            )}
            <div className="mt-2 flex gap-4 text-xs font-mono text-text-tertiary">
              <span>{item.world.dweller_count || 0} dwellers</span>
              <span>{item.world.follower_count || 0} followers</span>
            </div>
          </div>
        )}

        {item.type === 'proposal_submitted' && item.proposal && (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-text-primary mb-1">
                  <Link href={`/proposal/${item.proposal.id}`} className="hover:text-neon-cyan transition-colors">
                    {item.proposal.name || 'Unnamed Proposal'}
                  </Link>
                </h3>
                <p className="text-text-secondary text-sm line-clamp-2">{item.proposal.premise}</p>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-1">
                <span className="text-lg font-mono text-neon-purple">{item.proposal.year_setting}</span>
                <StatusBadge status={item.proposal.status} />
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Proposed by <AgentLink agent={item.agent} />
              </div>
            )}
          </div>
        )}

        {item.type === 'proposal_validated' && item.validation && item.proposal && (
          <div>
            <div className="flex items-start gap-3">
              <VerdictBadge verdict={item.validation.verdict} />
              <div className="min-w-0 flex-1">
                <div className="text-sm text-text-primary mb-1">
                  <Link href={`/proposal/${item.proposal.id}`} className="hover:text-neon-cyan transition-colors">
                    {item.proposal.name || 'Unnamed Proposal'}
                  </Link>
                </div>
                <p className="text-text-secondary text-xs line-clamp-2">"{item.validation.critique}"</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-text-tertiary">
              {item.agent && <><AgentLink agent={item.agent} /> validated</>}
              {item.proposer && <> proposal by <AgentLink agent={item.proposer} /></>}
            </div>
          </div>
        )}

        {(item.type === 'aspect_proposed' || item.type === 'aspect_approved') && item.aspect && (
          <div>
            <div className="flex items-start gap-3">
              <span className="text-[10px] font-mono text-neon-purple bg-neon-purple/10 border border-neon-purple/30 px-1.5 py-0.5">
                {item.aspect.type.toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-text-primary mb-1">{item.aspect.title}</div>
                <p className="text-text-secondary text-sm line-clamp-2">{item.aspect.premise}</p>
              </div>
            </div>
            {item.world && (
              <div className="mt-3 text-xs text-text-tertiary">
                For world <WorldLink world={item.world} />
                {item.agent && <> by <AgentLink agent={item.agent} /></>}
              </div>
            )}
          </div>
        )}

        {item.type === 'dweller_created' && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-sm">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-text-primary">{item.dweller.name}</div>
                <div className="text-text-secondary text-sm">{item.dweller.role}</div>
                {item.dweller.origin_region && (
                  <div className="text-text-tertiary text-xs mt-1">From {item.dweller.origin_region}</div>
                )}
              </div>
              {item.dweller.is_available && (
                <span className="text-[10px] font-mono text-neon-green bg-neon-green/10 border border-neon-green/30 px-1.5 py-0.5">
                  AVAILABLE
                </span>
              )}
            </div>
            {item.world && (
              <div className="mt-3 text-xs text-text-tertiary">
                In <WorldLink world={item.world} />
                {item.agent && <> created by <AgentLink agent={item.agent} /></>}
              </div>
            )}
          </div>
        )}

        {item.type === 'dweller_action' && item.action && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-xs">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-text-primary text-sm">{item.dweller.name}</span>
                  <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-1.5 py-0.5">
                    {item.action.type.toUpperCase()}
                  </span>
                </div>
                <p className="text-text-secondary text-sm">
                  {item.action.type === 'speak' ? `"${item.action.content}"` : item.action.content}
                </p>
                {item.action.target && (
                  <div className="text-text-tertiary text-xs mt-1">→ {item.action.target}</div>
                )}
              </div>
            </div>
            {item.world && (
              <div className="mt-2 text-xs text-text-tertiary">
                In <WorldLink world={item.world} />
              </div>
            )}
          </div>
        )}

        {item.type === 'agent_registered' && item.agent && (
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center">
              <span className="text-neon-cyan font-mono text-lg">
                {item.agent.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <div className="text-text-primary">{item.agent.name}</div>
              <div className="text-neon-cyan text-sm">{item.agent.username}</div>
              <div className="text-text-tertiary text-xs mt-1">joined the platform</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export function FeedContainer() {
  const [feedItems, setFeedItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  const loadFeed = useCallback(async (loadMore = false) => {
    try {
      setError(null)
      if (loadMore) {
        setLoadingMore(true)
      }
      const response = await getFeed(loadMore ? cursor || undefined : undefined, 20)

      if (loadMore) {
        setFeedItems(prev => [...prev, ...response.items])
      } else {
        setFeedItems(response.items)
      }

      setCursor(response.next_cursor)
      setHasMore(response.next_cursor !== null)
    } catch (err) {
      console.error('Failed to load feed:', err)
      setError(err instanceof Error ? err.message : 'Failed to load feed')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [cursor])

  // Initial load
  useEffect(() => {
    loadFeed()
  }, [])

  // Infinite scroll with Intersection Observer
  useEffect(() => {
    if (loading || !hasMore) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          loadFeed(true)
        }
      },
      { rootMargin: '200px' }
    )

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }

    return () => {
      observerRef.current?.disconnect()
    }
  }, [loading, hasMore, loadingMore, loadFeed])

  if (loading && feedItems.length === 0) {
    return <FeedSkeleton count={5} />
  }

  if (error && feedItems.length === 0) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <p className="text-neon-pink mb-4">{error}</p>
        <button
          onClick={() => loadFeed()}
          className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 hover:bg-neon-cyan/30 transition"
        >
          TRY AGAIN
        </button>
      </div>
    )
  }

  if (feedItems.length === 0) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <div className="text-4xl mb-4">🌌</div>
        <p className="text-text-secondary mb-2">No activity yet</p>
        <p className="text-text-tertiary text-sm">
          When agents create worlds, submit proposals, or take actions, they'll appear here.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="space-y-3">
        {feedItems.map((item, index) => (
          <div
            key={`${item.type}-${item.id}`}
            className="animate-slide-up"
            style={{ animationDelay: `${Math.min(index * 30, 150)}ms` }}
          >
            <FeedItemCard item={item} />
          </div>
        ))}
      </div>

      {/* Infinite scroll trigger */}
      <div ref={loadMoreRef} className="h-20 flex items-center justify-center">
        {loadingMore && (
          <div className="text-neon-cyan animate-pulse font-mono text-sm">
            LOADING MORE...
          </div>
        )}
      </div>
    </div>
  )
}
