'use client'

import { useState, useRef, useEffect } from 'react'
import type { Story, World } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { ReactionButtons } from '@/components/social/ReactionButtons'
import Link from 'next/link'

interface StoryCardProps {
  story: Story
  world?: World
}

export function StoryCard({ story, world }: StoryCardProps) {
  const [isHovering, setIsHovering] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Handle video preview on hover
  useEffect(() => {
    if (!videoRef.current || !story.videoUrl) return

    if (isHovering) {
      videoRef.current.currentTime = 0
      videoRef.current.play().catch(() => {})
    } else {
      videoRef.current.pause()
    }
  }, [isHovering, story.videoUrl])

  return (
    <Card className="h-full flex flex-col">
      {/* Video/Thumbnail area */}
      <Link
        href={`/story/${story.id}`}
        className="relative aspect-video bg-bg-tertiary cursor-pointer group block overflow-hidden"
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
      >
        {/* Thumbnail */}
        {story.thumbnailUrl && (
          <img
            src={story.thumbnailUrl}
            alt={story.title}
            className={`
              absolute inset-0 w-full h-full object-cover
              transition-opacity duration-300
              ${isHovering && story.videoUrl ? 'opacity-0' : 'opacity-100'}
            `}
          />
        )}

        {/* Video preview (plays on hover) */}
        {story.videoUrl && (
          <video
            ref={videoRef}
            src={story.videoUrl}
            muted
            loop
            playsInline
            preload="metadata"
            className={`
              absolute inset-0 w-full h-full object-cover
              transition-opacity duration-300
              ${isHovering ? 'opacity-100' : 'opacity-0'}
            `}
          />
        )}

        {/* Play indicator when not hovering */}
        {!isHovering && !story.thumbnailUrl && (
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
        <div className={`
          absolute inset-0 bg-black/40 flex items-center justify-center
          transition-opacity duration-200
          ${isHovering ? 'opacity-100' : 'opacity-0'}
        `}>
          <div className="w-14 h-14 flex items-center justify-center bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan text-2xl transform group-hover:scale-110 transition-transform">
            ▶
          </div>
        </div>

        {/* Type badge */}
        <div className="absolute top-2 left-2 bg-neon-cyan/20 border border-neon-cyan/50 px-2 py-1">
          <span className="text-xs font-mono text-neon-cyan uppercase">
            {story.type}
          </span>
        </div>
      </Link>

      <CardContent className="flex-1">
        {/* World link */}
        {world && (
          <Link
            href={`/world/${world.id}`}
            className="text-xs font-mono text-neon-purple hover:text-neon-purple/80 transition-colors"
          >
            {world.name} • {world.yearSetting}
          </Link>
        )}

        {/* Title and description */}
        <h3 className="text-base md:text-lg text-text-primary mt-2 line-clamp-2">{story.title}</h3>
        <p className="text-text-secondary text-sm mt-1 line-clamp-2">
          {story.description}
        </p>

        {/* Stats */}
        <div className="flex items-center gap-2 md:gap-4 mt-3 text-text-tertiary text-xs font-mono flex-wrap">
          <span>{story.viewCount.toLocaleString()} VIEWS</span>
          <span className="hidden xs:inline">•</span>
          <span className="hidden xs:inline">{new Date(story.createdAt).toLocaleDateString()}</span>
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between gap-2">
        <ReactionButtons
          counts={story.reactionCounts}
          targetType="story"
          targetId={story.id}
        />
        <button className="text-text-tertiary hover:text-neon-cyan transition-colors font-mono text-xs shrink-0">
          COMMENTS
        </button>
      </CardFooter>
    </Card>
  )
}
