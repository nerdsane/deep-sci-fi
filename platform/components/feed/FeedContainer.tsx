'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import type { FeedItem } from '@/types'
import { StoryCard } from './StoryCard'
import { ConversationCard } from './ConversationCard'
import { WorldCreatedCard } from './WorldCreatedCard'
import { getFeed, type FeedItem as ApiFeedItem } from '@/lib/api'
import { FeedSkeleton } from '@/components/ui/Skeleton'

// Transform API response to frontend types
function transformFeedItem(apiItem: ApiFeedItem): FeedItem | null {
  switch (apiItem.type) {
    case 'story':
      return {
        type: 'story',
        data: {
          id: apiItem.id,
          worldId: apiItem.world_id || '',
          type: 'short',
          title: apiItem.title || '',
          description: apiItem.description || '',
          videoUrl: apiItem.video_url,
          thumbnailUrl: apiItem.thumbnail_url,
          durationSeconds: apiItem.duration_seconds || 0,
          createdAt: new Date(apiItem.created_at || Date.now()),
          createdBy: '',
          viewCount: apiItem.view_count || 0,
          reactionCounts: {
            fire: apiItem.reaction_counts?.fire ?? 0,
            mind: apiItem.reaction_counts?.mind ?? 0,
            heart: apiItem.reaction_counts?.heart ?? 0,
            thinking: apiItem.reaction_counts?.thinking ?? 0,
          },
        },
        world: apiItem.world ? {
          id: apiItem.world.id,
          name: apiItem.world.name,
          premise: '',
          yearSetting: apiItem.world.year_setting,
          causalChain: [],
          createdAt: new Date(),
          createdBy: '',
          dwellerCount: 0,
          storyCount: 0,
          followerCount: 0,
        } : undefined,
      }
    case 'conversation':
      return {
        type: 'conversation',
        data: {
          id: apiItem.id,
          worldId: apiItem.world_id || '',
          participants: apiItem.participants || [],
          messages: (apiItem.messages || []).map(m => ({
            id: m.id,
            dwellerId: m.dweller_id,
            content: m.content,
            timestamp: new Date(m.timestamp),
          })),
          startedAt: new Date(),
          updatedAt: new Date(apiItem.updated_at || Date.now()),
        },
        world: apiItem.world ? {
          id: apiItem.world.id,
          name: apiItem.world.name,
          premise: '',
          yearSetting: apiItem.world.year_setting,
          causalChain: [],
          createdAt: new Date(),
          createdBy: '',
          dwellerCount: 0,
          storyCount: 0,
          followerCount: 0,
        } : undefined,
        dwellers: apiItem.dwellers?.map(d => ({
          id: d.id,
          worldId: apiItem.world_id || '',
          agentId: '',
          persona: d.persona,
          joinedAt: new Date(),
        })),
      }
    case 'world_created':
      return {
        type: 'world_created',
        data: {
          id: apiItem.id,
          name: apiItem.name || '',
          premise: apiItem.premise || '',
          yearSetting: apiItem.year_setting || 2089,
          causalChain: apiItem.causal_chain || [],
          createdAt: new Date(apiItem.created_at || Date.now()),
          createdBy: '',
          dwellerCount: apiItem.dweller_count || 0,
          storyCount: 0,
          followerCount: apiItem.follower_count || 0,
        },
      }
    default:
      return null
  }
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

      const transformed = response.items
        .map(transformFeedItem)
        .filter((item): item is FeedItem => item !== null)

      if (loadMore) {
        setFeedItems(prev => [...prev, ...transformed])
      } else {
        setFeedItems(transformed)
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
    return <FeedSkeleton count={3} />
  }

  if (error && feedItems.length === 0) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <p className="text-red-400 mb-4">{error}</p>
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
        <p className="text-text-secondary">No activity yet. Check back soon.</p>
      </div>
    )
  }

  return (
    <div>
      {/* Responsive grid: 1 col mobile, 2 col tablet, 3 col desktop for stories */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 md:gap-6">
        {feedItems.map((item, index) => {
          // Conversations span full width
          const isConversation = item.type === 'conversation'
          const className = isConversation ? 'md:col-span-2 xl:col-span-3' : ''

          return (
            <div
              key={`${item.type}-${item.data.id}`}
              className={`animate-slide-up ${className}`}
              style={{ animationDelay: `${Math.min(index * 50, 300)}ms` }}
            >
              {item.type === 'story' && (
                <StoryCard story={item.data} world={item.world} />
              )}
              {item.type === 'conversation' && (
                <ConversationCard
                  conversation={item.data}
                  world={item.world}
                  dwellers={item.dwellers}
                />
              )}
              {item.type === 'world_created' && (
                <WorldCreatedCard world={item.data} />
              )}
            </div>
          )
        })}
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
