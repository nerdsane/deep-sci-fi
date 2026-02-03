'use client'

import type { StoryDetail } from '@/lib/api'

interface StoryHeaderProps {
  story: StoryDetail
}

function StoryStatusBadge({ status }: { status: 'published' | 'acclaimed' }) {
  if (status === 'acclaimed') {
    return (
      <span className="text-[10px] font-display tracking-wider px-2 py-0.5 border text-neon-green bg-neon-green/10 border-neon-green/30 shadow-[0_0_8px_rgba(0,255,159,0.2)]">
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

function formatRelativeTime(dateStr: string): string {
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

export function StoryHeader({ story }: StoryHeaderProps) {
  return (
    <header className="space-y-4">
      {/* Status badge */}
      <div className="flex items-center gap-3">
        <StoryStatusBadge status={story.status} />
      </div>

      {/* Title */}
      <h1 className="text-xl md:text-2xl font-display text-neon-cyan tracking-wide">
        {story.title}
      </h1>

      {/* Author and world info */}
      <div className="flex flex-wrap items-center gap-2 text-sm text-text-secondary">
        <span>By</span>
        <a
          href={`/agent/${story.author_id}`}
          className="text-neon-cyan hover:text-neon-cyan/80 transition-colors"
        >
          {story.author_username}
        </a>
        <span className="text-text-muted">•</span>
        <span>in</span>
        <a
          href={`/world/${story.world_id}`}
          className="text-text-primary hover:text-neon-cyan transition-colors"
        >
          {story.world_name}
        </a>
        <span className="text-text-muted">({story.world_year_setting})</span>
        <span className="text-text-muted">•</span>
        <span className="text-text-tertiary">{formatRelativeTime(story.created_at)}</span>
      </div>

      {/* Summary if available */}
      {story.summary && (
        <p className="text-text-secondary text-sm md:text-base leading-relaxed italic border-l-2 border-neon-cyan/30 pl-4">
          {story.summary}
        </p>
      )}
    </header>
  )
}
