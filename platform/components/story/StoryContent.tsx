'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
      <div className="story-prose prose prose-invert prose-p:text-text-secondary prose-headings:text-text-primary prose-headings:font-display prose-headings:tracking-wide prose-strong:text-text-primary prose-em:text-text-secondary prose-blockquote:border-neon-cyan/30 prose-blockquote:text-text-tertiary prose-hr:border-white/10">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {story.content}
        </ReactMarkdown>
      </div>
    </article>
  )
}
