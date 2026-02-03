'use client'

import { useState } from 'react'
import type { StoryReviewsResponse, StoryReviewItem } from '@/lib/api'
import { ReviewCard } from './ReviewCard'
import { ReviewForm } from './ReviewForm'

interface StoryReviewsProps {
  storyId: string
  storyTitle: string
  authorId: string
  reviewsData: StoryReviewsResponse | null
  loading: boolean
}

export function StoryReviews({
  storyId,
  storyTitle,
  authorId,
  reviewsData,
  loading,
}: StoryReviewsProps) {
  const [showReviewForm, setShowReviewForm] = useState(false)
  const [localReviews, setLocalReviews] = useState<StoryReviewItem[]>([])

  // Combine server reviews with any locally added reviews
  const reviews = reviewsData?.reviews || []
  const allReviews = [...reviews, ...localReviews]

  // Check if user can see reviews (not blind review blocked)
  const isBlindReviewBlocked = reviewsData?.blind_review_notice !== undefined

  const handleReviewSubmitted = (newReview: StoryReviewItem) => {
    setLocalReviews(prev => [...prev, newReview])
    setShowReviewForm(false)
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-display text-text-primary tracking-wider">REVIEWS</h2>
        <div className="glass p-8 flex items-center justify-center">
          <div className="text-neon-cyan animate-pulse font-mono text-sm">LOADING REVIEWS...</div>
        </div>
      </div>
    )
  }

  // Blind review notice - user hasn't submitted a review yet
  if (isBlindReviewBlocked) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-display text-text-primary tracking-wider">REVIEWS</h2>
          <span className="text-xs font-mono text-text-tertiary">
            {reviewsData?.review_count || 0} reviews
          </span>
        </div>

        <div className="glass-amber p-4">
          <div className="flex items-start gap-3">
            <span className="text-neon-amber text-lg">⚠️</span>
            <div>
              <h3 className="text-neon-amber font-display text-sm tracking-wider mb-1">BLIND REVIEW</h3>
              <p className="text-text-secondary text-xs leading-relaxed">
                {reviewsData?.blind_review_notice}
              </p>
            </div>
          </div>
        </div>

        {!showReviewForm ? (
          <button
            onClick={() => setShowReviewForm(true)}
            className="w-full glass hover:border-neon-cyan/30 transition-all p-4 text-center"
          >
            <span className="text-neon-cyan font-display text-sm tracking-wider">
              WRITE YOUR REVIEW FIRST
            </span>
          </button>
        ) : (
          <ReviewForm
            storyId={storyId}
            storyTitle={storyTitle}
            onCancel={() => setShowReviewForm(false)}
            onSubmitted={handleReviewSubmitted}
          />
        )}
      </div>
    )
  }

  // Full reviews view
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-display text-text-primary tracking-wider">REVIEWS</h2>
        <div className="flex items-center gap-4">
          {reviewsData?.acclaim_count !== undefined && (
            <span className="text-xs font-mono text-text-tertiary">
              {reviewsData.acclaim_count} recommend acclaim
            </span>
          )}
          <span className="text-xs font-mono text-text-tertiary">
            {allReviews.length} reviews
          </span>
        </div>
      </div>

      {/* Review form toggle */}
      {!showReviewForm ? (
        <button
          onClick={() => setShowReviewForm(true)}
          className="w-full glass hover:border-neon-cyan/30 transition-all p-4 text-center"
        >
          <span className="text-neon-cyan font-display text-sm tracking-wider">
            + WRITE A REVIEW
          </span>
        </button>
      ) : (
        <ReviewForm
          storyId={storyId}
          storyTitle={storyTitle}
          onCancel={() => setShowReviewForm(false)}
          onSubmitted={handleReviewSubmitted}
        />
      )}

      {/* Reviews list */}
      {allReviews.length === 0 ? (
        <div className="glass p-8 text-center">
          <p className="text-text-tertiary text-sm">No reviews yet. Be the first to review this story.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {allReviews.map((review) => (
            <ReviewCard
              key={review.id}
              review={review}
              storyId={storyId}
              isAuthor={authorId === reviewsData?.author_id}
            />
          ))}
        </div>
      )}
    </div>
  )
}
