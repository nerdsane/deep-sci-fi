'use client'

import Link from 'next/link'
import type { StoryListItem } from '@/lib/api'
import { IconPlay } from '@/components/ui/PixelIcon'
import { formatRelativeTime } from '@/lib/utils'

interface StoryCardProps {
  story: StoryListItem
  variant?: 'default' | 'compact'
}

function StoryStatusBadge({ status }: { status: 'published' | 'acclaimed' }) {
  if (status === 'acclaimed') {
    return (
      <span className="text-[10px] font-display tracking-wider px-2 py-0.5 border text-neon-green bg-neon-green/10 border-neon-green/30 badge-pulse-acclaimed">
        ACCLAIMED
      </span>
    )
  }
  return (
    <span className="text-[10px] font-display tracking-wider px-2 py-0.5 border text-text-tertiary bg-white/5 border-white/10">
      PUBLISHED
    </span>
  )
}

function PerspectiveBadge({ perspective }: { perspective: string }) {
  const labels: Record<string, string> = {
    first_person_agent: '1P AGENT',
    first_person_dweller: '1P DWELLER',
    third_person_limited: '3P LIMITED',
    third_person_omniscient: '3P OMNI',
  }
  return (
    <span className="text-[10px] font-mono text-text-tertiary">
      {labels[perspective] || perspective}
    </span>
  )
}

export function StoryCard({ story, variant = 'default' }: StoryCardProps) {
  if (variant === 'compact') {
    return (
      <Link
        href={`/stories/${story.id}`}
        className="block glass hover:border-neon-cyan/30 transition-all p-3 group card-spring"
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <StoryStatusBadge status={story.status} />
          <PerspectiveBadge perspective={story.perspective} />
        </div>
        <h3 className="text-sm font-display text-text-primary group-hover:text-neon-cyan transition-colors line-clamp-2 mb-2">
          {story.title}
        </h3>
        <div className="flex items-center gap-2 text-xs text-text-tertiary">
          <span>{story.author_username}</span>
          <span className="text-text-muted">•</span>
          <span className="truncate">{story.world_name}</span>
        </div>
      </Link>
    )
  }

  return (
    <Link
      href={`/stories/${story.id}`}
      className="block glass hover:border-neon-cyan/30 transition-all overflow-hidden group card-spring"
    >
      {/* Media thumbnail */}
      <div className="aspect-video bg-bg-tertiary relative overflow-hidden">
        {(story.thumbnail_url || story.cover_image_url) ? (
          <img
            src={story.thumbnail_url || story.cover_image_url}
            alt={story.title}
            className="w-full h-full object-cover"
          />
        ) : story.video_url ? (
          <video
            src={story.video_url}
            preload="metadata"
            muted
            playsInline
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-neon-purple/20 to-neon-cyan/20">
            <span className="text-text-tertiary text-sm font-mono">STORY</span>
          </div>
        )}
        {/* Play overlay — indicates video, click navigates to story detail player */}
        {story.video_url && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 group-hover:bg-black/40 transition-colors">
            <div className="w-12 h-12 flex items-center justify-center bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan group-hover:bg-neon-cyan/30 transition-colors">
              <IconPlay size={32} />
            </div>
          </div>
        )}
      </div>

      <div className="p-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <StoryStatusBadge status={story.status} />
        <span className="text-xs text-text-muted font-mono">
          {formatRelativeTime(story.created_at)}
        </span>
      </div>

      {/* Title */}
      <h3 className="text-base font-display text-text-primary group-hover:text-neon-cyan transition-colors mb-2 line-clamp-2">
        {story.title}
      </h3>

      {/* Summary */}
      {story.summary && (
        <p className="text-sm text-text-secondary line-clamp-2 mb-3">
          {story.summary}
        </p>
      )}

      {/* Meta */}
      <div className="flex items-center gap-2 text-xs text-text-tertiary mb-3">
        <span className="text-neon-cyan">{story.author_username}</span>
        <span className="text-text-muted">•</span>
        <span className="truncate">{story.world_name}</span>
        <span className="text-text-muted">•</span>
        <PerspectiveBadge perspective={story.perspective} />
      </div>

      {/* Engagement */}
      <div className="flex items-center gap-4 text-xs text-text-muted">
        <span className="flex items-center gap-1">
          <span className="font-mono">{story.reaction_count} reactions</span>
        </span>
        <span className="flex items-center gap-1">
          <span className="font-mono">{story.comment_count} comments</span>
        </span>
        {story.perspective_dweller_name && (
          <span className="text-text-tertiary">
            via {story.perspective_dweller_name}
          </span>
        )}
      </div>
      </div>
    </Link>
  )
}
