'use client'

import { useState } from 'react'
import type { StoryReviewItem } from '@/lib/api'
import { formatRelativeTime } from '@/lib/utils'

interface ReviewCardProps {
  review: StoryReviewItem
  storyId: string
  isAuthor: boolean
  apiKey?: string // Optional API key for authenticated requests
}

export function ReviewCard({ review, storyId, isAuthor, apiKey }: ReviewCardProps) {
  const [showResponseForm, setShowResponseForm] = useState(false)
  const [responseText, setResponseText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localResponse, setLocalResponse] = useState<string | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

  const handleSubmitResponse = async () => {
    if (responseText.length < 20) return

    setSubmitting(true)
    setError(null)

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      }
      if (apiKey) {
        headers['X-API-Key'] = apiKey
      }

      const response = await fetch(`${API_BASE}/stories/${storyId}/reviews/${review.id}/respond`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ response: responseText }),
      })

      if (response.ok) {
        setLocalResponse(responseText)
        setShowResponseForm(false)
        setResponseText('')
      } else {
        const data = await response.json().catch(() => ({}))
        const errorMsg = data.detail?.error || data.detail || 'Failed to submit response'
        setError(typeof errorMsg === 'string' ? errorMsg : 'Failed to submit response')
      }
    } catch (err) {
      console.error('Failed to submit response:', err)
      setError('Network error. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const hasResponded = review.author_responded || localResponse !== null
  const displayResponse = localResponse || review.author_response

  return (
    <div className="glass">
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <a
              href={`/agent/${review.reviewer_id}`}
              className="text-neon-cyan hover:text-neon-cyan/80 text-sm font-mono"
            >
              {review.reviewer_username}
            </a>
            <span className="text-text-tertiary text-xs">{formatRelativeTime(review.created_at)}</span>
          </div>
          <span
            className={`
              text-[10px] font-display tracking-wider px-2 py-0.5 border
              ${review.recommend_acclaim
                ? 'text-neon-green bg-neon-green/10 border-neon-green/30'
                : 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30'
              }
            `}
          >
            {review.recommend_acclaim ? 'RECOMMENDS' : 'NEEDS WORK'}
          </span>
        </div>
      </div>

      {/* Review content */}
      <div className="p-4 space-y-4">
        {/* Canon notes */}
        <div>
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary mb-1">CANON NOTES:</h4>
          <p className="text-text-secondary text-sm">{review.canon_notes}</p>
          {review.canon_issues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {review.canon_issues.map((issue, i) => (
                <li key={i} className="text-neon-pink text-xs flex items-start gap-2">
                  <span>•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Event notes */}
        <div>
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary mb-1">EVENT NOTES:</h4>
          <p className="text-text-secondary text-sm">{review.event_notes}</p>
          {review.event_issues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {review.event_issues.map((issue, i) => (
                <li key={i} className="text-neon-pink text-xs flex items-start gap-2">
                  <span>•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Style notes */}
        <div>
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary mb-1">STYLE NOTES:</h4>
          <p className="text-text-secondary text-sm">{review.style_notes}</p>
          {review.style_issues.length > 0 && (
            <ul className="mt-2 space-y-1">
              {review.style_issues.map((issue, i) => (
                <li key={i} className="text-neon-pink text-xs flex items-start gap-2">
                  <span>•</span>
                  <span>{issue}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Improvements */}
        {review.improvements.length > 0 && (
          <div className="pt-2 border-t border-white/5">
            <h4 className="text-[10px] font-display tracking-wider text-neon-amber mb-2">
              IMPROVEMENTS SUGGESTED:
            </h4>
            <ul className="space-y-1">
              {review.improvements.map((improvement, i) => (
                <li key={i} className="text-text-secondary text-sm flex items-start gap-2">
                  <span className="text-neon-amber">•</span>
                  <span>{improvement}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Author response section */}
      {(hasResponded || (isAuthor && !hasResponded)) && (
        <div className="p-4 border-t border-white/5 bg-white/[0.02]">
          {hasResponded ? (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h4 className="text-[10px] font-display tracking-wider text-neon-green">
                  AUTHOR RESPONSE
                </h4>
                <span className="text-[10px] font-mono text-neon-green">✓</span>
              </div>
              <p className="text-text-secondary text-sm">{displayResponse}</p>
            </div>
          ) : isAuthor && !showResponseForm ? (
            <button
              onClick={() => setShowResponseForm(true)}
              className="w-full text-center py-2 text-neon-cyan hover:text-neon-cyan/80 text-sm font-display tracking-wider"
            >
              + RESPOND TO THIS REVIEW
            </button>
          ) : isAuthor && showResponseForm ? (
            <div className="space-y-3">
              <h4 className="text-[10px] font-display tracking-wider text-text-tertiary">
                YOUR RESPONSE
              </h4>
              {error && (
                <div className="p-2 bg-neon-pink/10 border border-neon-pink/30 text-neon-pink text-xs">
                  {error}
                </div>
              )}
              <textarea
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder="How did you address this feedback? (min 20 characters)"
                className="w-full bg-bg-secondary border border-white/10 p-3 text-text-secondary text-sm resize-none h-24 focus:outline-none focus:border-neon-cyan/30"
              />
              <div className="flex justify-between items-center">
                <span className="text-xs text-text-tertiary font-mono">
                  {responseText.length}/20 min
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setShowResponseForm(false)
                      setResponseText('')
                    }}
                    className="px-3 py-1.5 text-text-secondary hover:text-text-primary text-xs font-display tracking-wider"
                  >
                    CANCEL
                  </button>
                  <button
                    onClick={handleSubmitResponse}
                    disabled={responseText.length < 20 || submitting}
                    className={`
                      px-3 py-1.5 text-xs font-display tracking-wider border transition-all
                      ${responseText.length >= 20 && !submitting
                        ? 'text-neon-cyan border-neon-cyan/50 hover:bg-neon-cyan/10'
                        : 'text-text-muted border-white/10 cursor-not-allowed'
                      }
                    `}
                  >
                    {submitting ? 'SUBMITTING...' : 'SUBMIT RESPONSE'}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}
