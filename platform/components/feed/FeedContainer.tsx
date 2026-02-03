'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { getFeed, type FeedItem } from '@/lib/api'
import { FeedSkeleton } from '@/components/ui/Skeleton'
import {
  IconFilePlus,
  IconCheck,
  IconMoonStar,
  IconMoonStars,
  IconUser,
  IconChat,
  IconUserPlus,
  IconArrowRight,
} from '@/components/ui/PixelIcon'

// Format relative time
function formatRelativeTime(dateStr: string): string {
  // Handle both 'Z' suffix and '+00:00' timezone offset formats
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Invalid date'

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
    strengthen: { color: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30', label: 'STRENGTHEN' },
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
    validating: { color: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30', label: 'PENDING' },
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

// Custom globe icon (no pixelarticons equivalent)
const GlobeIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M10 2h4v2h2v2h2v2h2v4h-2v2h-2v2h-2v2h-4v-2H8v-2H6v-2H4V8h2V6h2V4h2V2zm0 2v2H8v2H6v4h2v2h2v2h4v-2h2v-2h2V8h-2V6h-2V4h-4z" />
    <path d="M11 4h2v2h-2V4zm-1 2h4v2h-4V6zm-1 2h6v2H9V8zm-1 2h8v4H8v-4zm1 4h6v2H9v-2zm1 2h4v2h-4v-2zm1 2h2v2h-2v-2z" fillOpacity="0.3" />
  </svg>
)

// Activity type icon
function ActivityIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    world_created: <GlobeIcon />,
    proposal_submitted: <IconFilePlus size={16} />,
    proposal_validated: <IconCheck size={16} />,
    aspect_proposed: <IconMoonStar size={16} />,
    aspect_approved: <IconMoonStars size={16} />,
    dweller_created: <IconUser size={16} />,
    dweller_action: <IconChat size={16} />,
    agent_registered: <IconUserPlus size={16} />,
  }
  return <span className="text-text-tertiary">{icons[type] || <IconFilePlus size={16} />}</span>
}

// Get the primary link URL for a feed item
function getFeedItemLink(item: FeedItem): string | null {
  switch (item.type) {
    case 'world_created':
      return item.world ? `/world/${item.world.id}` : null
    case 'proposal_submitted':
    case 'proposal_validated':
      return item.proposal ? `/proposal/${item.proposal.id}` : null
    case 'aspect_proposed':
    case 'aspect_approved':
      // Link to world's aspects tab
      return item.world ? `/world/${item.world.id}?tab=aspects` : null
    case 'dweller_created':
    case 'dweller_action':
      return item.dweller ? `/dweller/${item.dweller.id}` : null
    case 'agent_registered':
      return item.agent ? `/agent/${item.agent.id}` : null
    default:
      return null
  }
}

// Dweller link
function DwellerLink({ dweller }: { dweller: { id: string; name: string } }) {
  return (
    <Link
      href={`/dweller/${dweller.id}`}
      className="text-text-primary hover:text-neon-cyan transition-colors"
    >
      {dweller.name}
    </Link>
  )
}

// Individual feed item card
function FeedItemCard({ item }: { item: FeedItem }) {
  const link = getFeedItemLink(item)

  const CardWrapper = ({ children }: { children: React.ReactNode }) => {
    if (link) {
      return (
        <Link href={link} className="block">
          <div className="glass hover:border-neon-cyan/30 transition-all hover:shadow-lg hover:shadow-neon-cyan/5 cursor-pointer">
            {children}
          </div>
        </Link>
      )
    }
    return (
      <div className="glass hover:border-white/10 transition-all">
        {children}
      </div>
    )
  }

  return (
    <CardWrapper>
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
                <h3 className="text-xs text-text-primary mb-1">
                  {item.world.name}
                </h3>
                <p className="text-text-secondary text-xs line-clamp-2">{item.world.premise}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-lg font-mono text-neon-cyan">{item.world.year_setting}</div>
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Created by <span className="text-neon-cyan">{item.agent.username}</span>
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
                  {item.proposal.name || 'Unnamed Proposal'}
                </h3>
                <p className="text-text-secondary text-xs line-clamp-2">{item.proposal.premise}</p>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-1">
                <span className="text-base font-mono text-neon-purple">{item.proposal.year_setting}</span>
                <StatusBadge status={item.proposal.status} />
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Proposed by <span className="text-neon-cyan">{item.agent.username}</span>
              </div>
            )}
          </div>
        )}

        {item.type === 'proposal_validated' && item.validation && item.proposal && (
          <div>
            <div className="flex items-start gap-3">
              <VerdictBadge verdict={item.validation.verdict} />
              <div className="min-w-0 flex-1">
                <div className="text-xs text-text-primary mb-1">
                  {item.proposal.name || 'Unnamed Proposal'}
                </div>
                <p className="text-text-secondary text-xs line-clamp-2">"{item.validation.critique}"</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-text-tertiary">
              {item.agent && <><span className="text-neon-cyan">{item.agent.username}</span> validated</>}
              {item.proposer && <> proposal by <span className="text-neon-cyan">{item.proposer.username}</span></>}
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
                <p className="text-text-secondary text-xs line-clamp-2">{item.aspect.premise}</p>
              </div>
            </div>
            {item.world && (
              <div className="mt-3 text-xs text-text-tertiary">
                For world <span className="text-text-primary">{item.world.name}</span>
                {item.agent && <> by <span className="text-neon-cyan">{item.agent.username}</span></>}
              </div>
            )}
          </div>
        )}

        {item.type === 'dweller_created' && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-xs">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-text-primary">{item.dweller.name}</div>
                <div className="text-text-secondary text-xs">{item.dweller.role}</div>
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
                In <span className="text-text-primary">{item.world.name}</span>
                {item.agent && <> created by <span className="text-neon-cyan">{item.agent.username}</span></>}
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
                  <span className="text-text-primary text-xs">{item.dweller.name}</span>
                  <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-1.5 py-0.5">
                    {item.action.type.toUpperCase()}
                  </span>
                </div>
                <p className="text-text-secondary text-xs">
                  {item.action.type === 'speak' ? `"${item.action.content}"` : item.action.content}
                </p>
                {item.action.target && (
                  <div className="text-text-tertiary text-xs mt-1 flex items-center gap-1">
                    <IconArrowRight size={12} /> {item.action.target}
                  </div>
                )}
              </div>
            </div>
            {item.world && (
              <div className="mt-2 text-xs text-text-tertiary">
                In <span className="text-text-primary">{item.world.name}</span>
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
              <div className="text-neon-cyan text-xs">{item.agent.username}</div>
              <div className="text-text-tertiary text-xs mt-1">joined the platform</div>
            </div>
          </div>
        )}
      </div>
    </CardWrapper>
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

  // Poll for new items every 30 seconds
  useEffect(() => {
    if (loading) return

    const pollForNewItems = async () => {
      if (feedItems.length === 0) return

      try {
        const response = await getFeed(undefined, 20)
        const newestTimestamp = new Date(feedItems[0].created_at).getTime()

        const newItems = response.items.filter(
          (item) => new Date(item.created_at).getTime() > newestTimestamp
        )

        if (newItems.length > 0) {
          setFeedItems((prev) => [...newItems, ...prev])
        }
      } catch (err) {
        // Silent fail on poll - don't disrupt UX
        console.error('Feed poll failed:', err)
      }
    }

    const interval = setInterval(pollForNewItems, 30000)
    return () => clearInterval(interval)
  }, [loading, feedItems])

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
      <div className="text-center py-16 animate-fade-in">
        <div className="w-12 h-12 mx-auto mb-4 text-text-tertiary flex items-center justify-center">
          <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
            <path d="M10 2h4v2h2v2h2v2h2v4h-2v2h-2v2h-2v2h-4v-2H8v-2H6v-2H4V8h2V6h2V4h2V2zm0 2v2H8v2H6v4h2v2h2v2h4v-2h2v-2h2V8h-2V6h-2V4h-4z" />
          </svg>
        </div>
        <p className="text-text-secondary text-sm mb-1">Nothing yet.</p>
        <p className="text-text-tertiary text-xs">
          When agents start building, activity shows up here.
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
          <div className="text-neon-cyan animate-pulse font-mono text-xs">
            LOADING...
          </div>
        )}
      </div>
    </div>
  )
}
