'use client'

import { useState, useEffect } from 'react'
import type { StoryDetail as StoryDetailType, StoryReviewsResponse, StoryReviewItem } from '@/lib/api'
import { StoryHeader } from './StoryHeader'
import { StoryContent } from './StoryContent'
import { StoryMeta } from './StoryMeta'
import { StoryReviews } from './StoryReviews'
import { AcclaimProgress } from './AcclaimProgress'
import { VideoPlayer } from '@/components/video/VideoPlayer'
import { IconZap, IconChat, IconFilePlus, IconCopy, IconArrowDown } from '@/components/ui/PixelIcon'
import { ShareOnX } from '@/components/ui/ShareOnX'

interface StoryDetailProps {
  story: StoryDetailType
  acclaimEligibility: {
    eligible: boolean
    reason: string
  }
  currentUserId?: string // The logged-in user's ID (if any)
  apiKey?: string // API key for authenticated requests
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export function StoryDetail({ story, acclaimEligibility, currentUserId, apiKey }: StoryDetailProps) {
  const [reviewsData, setReviewsData] = useState<StoryReviewsResponse | null>(null)
  const [loadingReviews, setLoadingReviews] = useState(true)
  const [copied, setCopied] = useState(false)

  const handleCopyMarkdown = async () => {
    const md = `# ${story.title}\n\n*By ${story.author_name} · ${story.world_name}*\n\n${story.content || ''}`
    await navigator.clipboard.writeText(md)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadVideo = () => {
    if (!story.video_url) return
    const a = document.createElement('a')
    a.href = story.video_url
    a.download = `${story.title.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}.mp4`
    a.click()
  }

  useEffect(() => {
    async function fetchReviews() {
      try {
        // Fetch reviews (will respect blind review rules on backend)
        const response = await fetch(`${API_BASE}/stories/${story.id}/reviews`, {
          cache: 'no-store',
        })
        if (response.ok) {
          const data = await response.json()
          setReviewsData(data)
        }
      } catch (err) {
        console.error('Failed to fetch reviews:', err)
      } finally {
        setLoadingReviews(false)
      }
    }

    fetchReviews()
  }, [story.id])

  return (
    <div className="space-y-8">
      {/* Header: Status badge, title, author, meta */}
      <StoryHeader story={story} />

      {/* Video player or cover image */}
      {story.video_url ? (
        <div className="aspect-video">
          <VideoPlayer
            src={story.video_url}
            poster={story.cover_image_url || story.thumbnail_url}
            className="w-full h-full"
          />
        </div>
      ) : story.cover_image_url ? (
        <div className="aspect-video relative overflow-hidden bg-bg-tertiary">
          <img
            src={story.cover_image_url}
            alt={story.title}
            className="w-full h-full object-cover"
          />
        </div>
      ) : null}

      {/* Meta: Perspective, time period, sources */}
      <StoryMeta story={story} />

      {/* Full story content */}
      <StoryContent story={story} />

      {/* Engagement stats */}
      <div className="flex items-center gap-6 py-4 border-t border-b border-white/10">
        <div className="flex items-center gap-2">
          <IconZap size={18} className="text-neon-amber" />
          <span className="text-text-secondary font-mono text-sm">{story.reaction_count}</span>
        </div>
        <div className="flex items-center gap-2">
          <IconChat size={18} className="text-neon-cyan" />
          <span className="text-text-secondary font-mono text-sm">{story.comment_count} comments</span>
        </div>
        <div className="flex items-center gap-2">
          <IconFilePlus size={18} className="text-neon-pink" />
          <span className="text-text-secondary font-mono text-sm">{story.review_count} reviews</span>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={handleCopyMarkdown}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono text-text-tertiary hover:text-neon-cyan border border-white/10 hover:border-neon-cyan/30 transition-colors"
            title="Copy story as markdown"
          >
            <IconCopy size={14} />
            {copied ? 'COPIED' : 'COPY MD'}
          </button>
          {story.video_url && (
            <button
              onClick={handleDownloadVideo}
              className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono text-text-tertiary hover:text-neon-purple border border-white/10 hover:border-neon-purple/30 transition-colors"
              title="Download video"
            >
              <IconArrowDown size={14} />
              VIDEO
            </button>
          )}
          <ShareOnX
            text={`${story.title} — a story from ${story.world_name}`}
            hashtags={['DeepSciFi']}
            xPostId={story.x_post_id}
          />
        </div>
      </div>

      {/* Acclaim progress indicator */}
      <AcclaimProgress
        status={story.status}
        reviewCount={story.review_count}
        acclaimCount={story.acclaim_count}
        eligibility={acclaimEligibility}
      />

      {/* Reviews section */}
      <StoryReviews
        storyId={story.id}
        authorId={story.author_id}
        currentUserId={currentUserId}
        apiKey={apiKey}
        reviewsData={reviewsData}
        loading={loadingReviews}
      />
    </div>
  )
}
