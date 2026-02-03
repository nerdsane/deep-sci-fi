'use client'

import type { StoryDetail } from '@/lib/api'

interface StoryContentProps {
  story: StoryDetail
}

export function StoryContent({ story }: StoryContentProps) {
  if (!story.content) {
    return (
      <div className="glass p-6">
        <p className="text-text-tertiary text-sm font-mono mb-2">STORY CONTENT</p>
        <p className="text-text-secondary text-sm italic">No content available.</p>
      </div>
    )
  }

  return (
    <article className="glass p-6 md:p-8">
      <div className="prose prose-invert max-w-none">
        <div className="text-text-secondary leading-relaxed whitespace-pre-wrap text-sm md:text-base">
          {story.content}
        </div>
      </div>
    </article>
  )
}
