'use client'

import { useState } from 'react'
import type { Story, World, ReactionType } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { ReactionButtons } from '@/components/social/ReactionButtons'

interface StoryCardProps {
  story: Story
  world: World
}

export function StoryCard({ story, world }: StoryCardProps) {
  const [isPlaying, setIsPlaying] = useState(false)

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <Card>
      {/* Video/Thumbnail area */}
      <div
        className="relative aspect-video bg-bg-tertiary cursor-pointer group"
        onClick={() => setIsPlaying(!isPlaying)}
      >
        {story.thumbnailUrl ? (
          <img
            src={story.thumbnailUrl}
            alt={story.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-6xl text-neon-cyan/20">▶</div>
          </div>
        )}

        {/* Duration badge */}
        <div className="absolute bottom-2 right-2 bg-black/80 px-2 py-1">
          <span className="text-xs font-mono text-text-primary">
            {formatDuration(story.durationSeconds)}
          </span>
        </div>

        {/* Play overlay on hover */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <div className="text-5xl text-neon-cyan">▶</div>
        </div>

        {/* Type badge */}
        <div className="absolute top-2 left-2 bg-neon-cyan/20 border border-neon-cyan/50 px-2 py-1">
          <span className="text-xs font-mono text-neon-cyan uppercase">
            {story.type}
          </span>
        </div>
      </div>

      <CardContent>
        {/* World link */}
        <a
          href={`/world/${world.id}`}
          className="text-xs font-mono text-neon-purple hover:text-neon-purple/80 transition-colors"
        >
          {world.name} • {world.yearSetting}
        </a>

        {/* Title and description */}
        <h3 className="text-lg text-text-primary mt-2">{story.title}</h3>
        <p className="text-text-secondary text-sm mt-1 line-clamp-2">
          {story.description}
        </p>

        {/* Stats */}
        <div className="flex items-center gap-4 mt-3 text-text-tertiary text-xs font-mono">
          <span>{story.viewCount.toLocaleString()} VIEWS</span>
          <span>•</span>
          <span>{new Date(story.createdAt).toLocaleDateString()}</span>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between">
        <ReactionButtons
          counts={story.reactionCounts}
          targetType="story"
          targetId={story.id}
        />
        <button className="text-text-tertiary hover:text-neon-cyan transition-colors font-mono text-xs">
          COMMENTS
        </button>
      </CardFooter>
    </Card>
  )
}
