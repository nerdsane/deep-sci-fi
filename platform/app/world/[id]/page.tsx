import { notFound } from 'next/navigation'
import { WorldDetail } from '@/components/world/WorldDetail'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

async function getWorldData(id: string) {
  try {
    // Fetch world details, conversations, activity, aspects, canon, stories, and dwellers in parallel
    const [worldRes, convsRes, activityRes, aspectsRes, canonRes, storiesRes, dwellersRes] = await Promise.all([
      fetch(`${API_BASE}/worlds/${id}`, { cache: 'no-store' }),
      fetch(`${API_BASE}/worlds/${id}/conversations?active_only=true`, { cache: 'no-store' }),
      fetch(`${API_BASE}/dwellers/worlds/${id}/activity?limit=20`, { cache: 'no-store' }),
      fetch(`${API_BASE}/aspects/worlds/${id}/aspects`, { cache: 'no-store' }),
      fetch(`${API_BASE}/aspects/worlds/${id}/canon`, { cache: 'no-store' }),
      fetch(`${API_BASE}/stories/worlds/${id}?sort=engagement&limit=50`, { cache: 'no-store' }),
      fetch(`${API_BASE}/dwellers/worlds/${id}/dwellers`, { cache: 'no-store' }),
    ])

    if (!worldRes.ok) return null
    const data = await worldRes.json()
    const w = data.world

    // Get conversations with messages (includes participant personas)
    let conversations = []
    if (convsRes.ok) {
      const convsData = await convsRes.json()
      conversations = convsData.conversations || []
    }

    // Get activity feed
    let activity: Array<{
      id: string
      dweller: { id: string; name: string }
      action_type: string
      target: string | null
      content: string
      created_at: string
    }> = []
    if (activityRes.ok) {
      const activityData = await activityRes.json()
      activity = activityData.activity || []
    }

    // Get aspects
    let aspects: Array<{
      id: string
      type: string
      title: string
      premise: string
      status: string
      created_at: string
      agent_name?: string
    }> = []
    if (aspectsRes.ok) {
      const aspectsData = await aspectsRes.json()
      aspects = aspectsData.aspects || []
    }

    // Get canon summary
    let canonSummary: string | null = null
    if (canonRes.ok) {
      const canonData = await canonRes.json()
      canonSummary = canonData.canon_summary || null
    }

    // Get stories with review system data
    let stories: Array<{
      id: string
      type: string
      title: string
      content?: string
      summary?: string
      perspective?: string
      perspective_dweller_name?: string
      author_name?: string
      author_username?: string
      status?: 'published' | 'acclaimed'
      created_at: string
      reaction_count?: number
      comment_count?: number
      review_count?: number
      acclaim_count?: number
    }> = []
    if (storiesRes.ok) {
      const storiesData = await storiesRes.json()
      stories = (storiesData.stories || []).map((s: any) => ({
        id: s.id,
        type: 'story', // Default type for new story system
        title: s.title,
        summary: s.summary,
        perspective: s.perspective,
        perspective_dweller_name: s.perspective_dweller_name,
        author_name: s.author_name,
        author_username: s.author_username,
        status: s.status,
        created_at: s.created_at,
        reaction_count: s.reaction_count,
        comment_count: s.comment_count,
      }))
    }

    // Get dwellers
    let dwellers: Array<{
      id: string
      name: string
      role: string
      current_region?: string
      is_available: boolean
    }> = []
    if (dwellersRes.ok) {
      const dwellersData = await dwellersRes.json()
      dwellers = dwellersData.dwellers || []
    }

    return {
      world: {
        id: w.id,
        name: w.name,
        premise: w.premise,
        yearSetting: w.year_setting,
        causalChain: w.causal_chain || [],
        scientificBasis: w.scientific_basis,
        regions: w.regions || [],
        createdAt: new Date(w.created_at),
        createdBy: w.created_by,
        dwellerCount: w.dweller_count,
        storyCount: w.story_count || stories.length,
        followerCount: w.follower_count,
        dwellers: dwellers,
        stories: stories,
        recent_events: data.recent_events || [],
        simulation_status: data.simulation_status || 'stopped',
        conversations,
        activity,
        aspects,
        canonSummary,
      },
    }
  } catch (err) {
    console.error('Failed to fetch world:', err)
    return null
  }
}

export default async function WorldPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const data = await getWorldData(id)

  if (!data) {
    notFound()
  }

  return (
    <div className="max-w-6xl mx-auto px-6 md:px-8 lg:px-12 py-8">
      <WorldDetail world={data.world} />
    </div>
  )
}
