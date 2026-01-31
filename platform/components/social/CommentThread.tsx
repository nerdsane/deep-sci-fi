'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import type { Comment, User } from '@/types'
import { Button } from '@/components/ui/Button'

interface CommentThreadProps {
  comments: Comment[]
  targetType: 'story' | 'world' | 'conversation'
  targetId: string
}

export function CommentThread({
  comments,
  targetType,
  targetId,
}: CommentThreadProps) {
  const [newComment, setNewComment] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newComment.trim()) return

    setIsSubmitting(true)
    try {
      // TODO: Send to API
      // await fetch('/api/social/comment', {
      //   method: 'POST',
      //   body: JSON.stringify({ targetType, targetId, content: newComment }),
      // })
      setNewComment('')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Comment input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
          className="flex-1 bg-bg-tertiary border border-white/10 px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-neon-cyan/50"
        />
        <Button type="submit" size="sm" loading={isSubmitting}>
          POST
        </Button>
      </form>

      {/* Comments list */}
      <div className="space-y-3">
        {comments.map((comment) => (
          <CommentItem key={comment.id} comment={comment} />
        ))}
      </div>
    </div>
  )
}

function CommentItem({ comment }: { comment: Comment }) {
  const isAgentUser = comment.user?.type === 'agent'

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div
        className={`
          w-8 h-8 flex items-center justify-center shrink-0
          ${isAgentUser ? 'bg-neon-purple/20' : 'bg-neon-cyan/20'}
        `}
      >
        <span
          className={`text-sm ${isAgentUser ? 'text-neon-purple' : 'text-neon-cyan'}`}
        >
          {comment.user?.name.charAt(0) || '?'}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm text-text-primary font-medium">
            {comment.user?.name || 'Anonymous'}
          </span>
          {isAgentUser && (
            <span className="text-xs font-mono text-neon-purple border border-neon-purple/30 px-1.5 py-0.5">
              AGENT
            </span>
          )}
          <span className="text-xs text-text-tertiary">
            {formatDistanceToNow(comment.createdAt, { addSuffix: true })}
          </span>
        </div>
        <p className="text-text-secondary text-sm">{comment.content}</p>

        {/* Reply button */}
        <button className="text-xs text-text-tertiary hover:text-neon-cyan transition-colors mt-1 font-mono">
          REPLY
        </button>
      </div>
    </div>
  )
}
