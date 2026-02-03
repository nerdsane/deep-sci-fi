'use client'

import { useState, useEffect } from 'react'
import type { StoryDetail as StoryDetailType, StoryReviewsResponse, StoryReviewItem } from '@/lib/api'
import { StoryHeader } from './StoryHeader'
import { StoryContent } from './StoryContent'
import { StoryMeta } from './StoryMeta'
import { StoryReviews } from './StoryReviews'
import { AcclaimProgress } from './AcclaimProgress'

interface StoryDetailProps {
  story: StoryDetailType
  acclaimEligibility: {
    eligible: boolean
    reason: string
  }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

export function StoryDetail({ story, acclaimEligibility }: StoryDetailProps) {
  const [reviewsData, setReviewsData] = useState<StoryReviewsResponse | null>(null)
  const [loadingReviews, setLoadingReviews] = useState(true)

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

      {/* Meta: Perspective, time period, sources */}
      <StoryMeta story={story} />

      {/* Full story content */}
      <StoryContent story={story} />

      {/* Engagement stats */}
      <div className="flex items-center gap-6 py-4 border-t border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-lg">🔥</span>
          <span className="text-text-secondary font-mono text-sm">{story.reaction_count}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg">💬</span>
          <span className="text-text-secondary font-mono text-sm">{story.comment_count} comments</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg">📝</span>
          <span className="text-text-secondary font-mono text-sm">{story.review_count} reviews</span>
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
        storyTitle={story.title}
        authorId={story.author_id}
        reviewsData={reviewsData}
        loading={loadingReviews}
      />
    </div>
  )
}
