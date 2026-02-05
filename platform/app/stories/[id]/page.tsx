import { notFound } from 'next/navigation'
import Link from 'next/link'
import { StoryDetail } from '@/components/story/StoryDetail'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

async function getStoryData(id: string) {
  try {
    const response = await fetch(`${API_BASE}/stories/${id}`, { cache: 'no-store' })

    if (!response.ok) {
      return null
    }

    const data = await response.json()
    return data
  } catch (err) {
    console.error('Failed to fetch story:', err)
    return null
  }
}

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await getStoryData(id)

  if (!data) {
    notFound()
  }

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-8 lg:px-12 py-8">
      {/* Back to world link */}
      <Link
        href={`/world/${data.story.world_id}?tab=stories`}
        className="inline-flex items-center gap-2 text-neon-cyan hover:text-neon-cyan/80 font-mono text-sm mb-6"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20 11v2H8v2H6v-2H4v-2h2V9h2v2h12Z" />
        </svg>
        Back to {data.story.world_name}
      </Link>

      <StoryDetail
        story={data.story}
        acclaimEligibility={data.acclaim_eligibility}
      />
    </div>
  )
}
