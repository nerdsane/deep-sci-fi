import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { StoryDetail } from '@/components/story/StoryDetail'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

type Props = { params: Promise<{ id: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params
  try {
    const res = await fetch(`${API_BASE}/stories/${id}`, { cache: 'no-store' })
    if (!res.ok) return {}
    const data = await res.json()
    const s = data.story

    const title = s.title
    const description = s.summary?.slice(0, 200)
      || s.content?.slice(0, 200)
      || `A story from ${s.world_name} on Deep Sci-Fi`

    const imageUrl = s.cover_image_url || s.thumbnail_url
    const videoUrl = s.video_url
    const hasImage = !!imageUrl
    const hasVideo = !!videoUrl

    // Build OG metadata — give X/social crawlers everything we have
    const ogMeta: any = {
      title: `${title} | Deep Sci-Fi`,
      description,
      url: `https://deep-sci-fi.world/stories/${id}`,
      type: 'article',
      siteName: 'Deep Sci-Fi',
    }

    // Always include image if we have one (X strongly prefers image cards)
    if (hasImage) {
      ogMeta.images = [{ url: imageUrl, width: 1200, height: 630, alt: title }]
    }
    // Always include video if we have one (alongside image — both can coexist)
    if (hasVideo) {
      ogMeta.videos = [{ url: videoUrl, type: 'video/mp4', width: 1280, height: 720 }]
    }

    // Twitter card config
    const twitterMeta: any = {
      title: `${title} | Deep Sci-Fi`,
      description,
      site: '@arni0x9053',
      creator: '@arni0x9053',
    }

    if (hasImage) {
      // summary_large_image gives the best visual on X timelines
      twitterMeta.card = 'summary_large_image'
      twitterMeta.images = [imageUrl]
    } else if (hasVideo) {
      // No image but have video — use summary_large_image anyway
      // X will pick up og:video for some clients, but we need an image fallback
      // Use a branded fallback so the card isn't empty
      twitterMeta.card = 'summary_large_image'
      twitterMeta.images = ['https://deep-sci-fi.world/og-default.png']
    } else {
      twitterMeta.card = 'summary'
      twitterMeta.images = ['https://deep-sci-fi.world/og-default.png']
    }

    return {
      title: `${title} | Deep Sci-Fi`,
      description,
      openGraph: ogMeta,
      twitter: twitterMeta,
    }
  } catch {
    return {}
  }
}

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
