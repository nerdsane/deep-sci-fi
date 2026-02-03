'use client'

import { useState } from 'react'
import type { StoryReviewItem } from '@/lib/api'

interface ReviewFormProps {
  storyId: string
  storyTitle: string
  onCancel: () => void
  onSubmitted: (review: StoryReviewItem) => void
}

export function ReviewForm({ storyId, storyTitle, onCancel, onSubmitted }: ReviewFormProps) {
  const [recommendAcclaim, setRecommendAcclaim] = useState<boolean | null>(null)
  const [canonNotes, setCanonNotes] = useState('')
  const [eventNotes, setEventNotes] = useState('')
  const [styleNotes, setStyleNotes] = useState('')
  const [improvements, setImprovements] = useState<string[]>([''])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

  const addImprovement = () => {
    setImprovements(prev => [...prev, ''])
  }

  const updateImprovement = (index: number, value: string) => {
    setImprovements(prev => {
      const updated = [...prev]
      updated[index] = value
      return updated
    })
  }

  const removeImprovement = (index: number) => {
    setImprovements(prev => prev.filter((_, i) => i !== index))
  }

  const isValid = () => {
    if (recommendAcclaim === null) return false
    if (canonNotes.length < 20) return false
    if (eventNotes.length < 20) return false
    if (styleNotes.length < 20) return false
    const validImprovements = improvements.filter(imp => imp.trim().length > 0)
    if (validImprovements.length === 0) return false
    return true
  }

  const handleSubmit = async () => {
    if (!isValid()) return

    setSubmitting(true)
    setError(null)

    const validImprovements = improvements.filter(imp => imp.trim().length > 0)

    try {
      const response = await fetch(`${API_BASE}/stories/${storyId}/review`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recommend_acclaim: recommendAcclaim,
          improvements: validImprovements,
          canon_notes: canonNotes,
          event_notes: eventNotes,
          style_notes: styleNotes,
          canon_issues: [],
          event_issues: [],
          style_issues: [],
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail?.error || 'Failed to submit review')
      }

      const data = await response.json()

      // Create a mock review item for immediate display
      const newReview: StoryReviewItem = {
        id: data.review.id,
        story_id: storyId,
        reviewer_id: 'current_user', // Would come from auth context
        reviewer_name: 'You',
        reviewer_username: '@you',
        recommend_acclaim: recommendAcclaim!,
        improvements: validImprovements,
        canon_notes: canonNotes,
        event_notes: eventNotes,
        style_notes: styleNotes,
        canon_issues: [],
        event_issues: [],
        style_issues: [],
        created_at: new Date().toISOString(),
        author_responded: false,
        author_response: null,
        author_responded_at: null,
      }

      onSubmitted(newReview)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit review')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="glass p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-display text-text-primary tracking-wider">REVIEW THIS STORY</h3>
        <button
          onClick={onCancel}
          className="text-text-tertiary hover:text-text-secondary text-xs font-display tracking-wider"
        >
          CANCEL
        </button>
      </div>

      {error && (
        <div className="p-3 bg-neon-pink/10 border border-neon-pink/30 text-neon-pink text-sm">
          {error}
        </div>
      )}

      {/* Acclaim recommendation */}
      <div className="space-y-2">
        <h4 className="text-[10px] font-display tracking-wider text-text-tertiary">
          DO YOU RECOMMEND THIS STORY FOR ACCLAIM?
        </h4>
        <div className="flex gap-3">
          <button
            onClick={() => setRecommendAcclaim(true)}
            className={`
              flex-1 py-2 px-4 border text-sm font-display tracking-wider transition-all
              ${recommendAcclaim === true
                ? 'text-neon-green border-neon-green/50 bg-neon-green/10'
                : 'text-text-secondary border-white/10 hover:border-white/20'
              }
            `}
          >
            YES, RECOMMEND
          </button>
          <button
            onClick={() => setRecommendAcclaim(false)}
            className={`
              flex-1 py-2 px-4 border text-sm font-display tracking-wider transition-all
              ${recommendAcclaim === false
                ? 'text-neon-cyan border-neon-cyan/50 bg-neon-cyan/10'
                : 'text-text-secondary border-white/10 hover:border-white/20'
              }
            `}
          >
            NOT YET
          </button>
        </div>
      </div>

      {/* Canon notes */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary">
            CANON CONSISTENCY (required)
          </h4>
          <span className="text-[10px] font-mono text-text-muted">{canonNotes.length}/20 min</span>
        </div>
        <textarea
          value={canonNotes}
          onChange={(e) => setCanonNotes(e.target.value)}
          placeholder="Does the story respect world canon? Are there any contradictions?"
          className="w-full bg-bg-secondary border border-white/10 p-3 text-text-secondary text-sm resize-none h-20 focus:outline-none focus:border-neon-cyan/30"
        />
      </div>

      {/* Event notes */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary">
            EVENT ACCURACY (required)
          </h4>
          <span className="text-[10px] font-mono text-text-muted">{eventNotes.length}/20 min</span>
        </div>
        <textarea
          value={eventNotes}
          onChange={(e) => setEventNotes(e.target.value)}
          placeholder="Do referenced events match what actually happened in the world?"
          className="w-full bg-bg-secondary border border-white/10 p-3 text-text-secondary text-sm resize-none h-20 focus:outline-none focus:border-neon-cyan/30"
        />
      </div>

      {/* Style notes */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-[10px] font-display tracking-wider text-text-tertiary">
            WRITING QUALITY (required)
          </h4>
          <span className="text-[10px] font-mono text-text-muted">{styleNotes.length}/20 min</span>
        </div>
        <textarea
          value={styleNotes}
          onChange={(e) => setStyleNotes(e.target.value)}
          placeholder="Perspective consistency, pacing, voice, narrative arc..."
          className="w-full bg-bg-secondary border border-white/10 p-3 text-text-secondary text-sm resize-none h-20 focus:outline-none focus:border-neon-cyan/30"
        />
      </div>

      {/* Improvements */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-[10px] font-display tracking-wider text-neon-amber">
            IMPROVEMENTS (at least 1 required)
          </h4>
          <button
            onClick={addImprovement}
            className="text-neon-cyan hover:text-neon-cyan/80 text-xs font-display tracking-wider"
          >
            + ADD
          </button>
        </div>
        <div className="space-y-2">
          {improvements.map((improvement, index) => (
            <div key={index} className="flex gap-2">
              <input
                type="text"
                value={improvement}
                onChange={(e) => updateImprovement(index, e.target.value)}
                placeholder="What could be improved?"
                className="flex-1 bg-bg-secondary border border-white/10 p-2 text-text-secondary text-sm focus:outline-none focus:border-neon-cyan/30"
              />
              {improvements.length > 1 && (
                <button
                  onClick={() => removeImprovement(index)}
                  className="px-2 text-neon-pink hover:text-neon-pink/80 text-sm"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3 pt-2 border-t border-white/5">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-text-secondary hover:text-text-primary text-sm font-display tracking-wider"
        >
          CANCEL
        </button>
        <button
          onClick={handleSubmit}
          disabled={!isValid() || submitting}
          className={`
            px-4 py-2 text-sm font-display tracking-wider border transition-all
            ${isValid() && !submitting
              ? 'text-neon-cyan border-neon-cyan/50 hover:bg-neon-cyan/10'
              : 'text-text-muted border-white/10 cursor-not-allowed'
            }
          `}
        >
          {submitting ? 'SUBMITTING...' : 'SUBMIT REVIEW'}
        </button>
      </div>
    </div>
  )
}
