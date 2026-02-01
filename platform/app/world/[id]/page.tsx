import { notFound } from 'next/navigation'
import { WorldDetail } from '@/components/world/WorldDetail'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

async function getWorldData(id: string) {
  try {
    // Fetch world details, conversations, and agents in parallel
    const [worldRes, convsRes, agentsRes] = await Promise.all([
      fetch(`${API_BASE}/worlds/${id}`, { cache: 'no-store' }),
      fetch(`${API_BASE}/worlds/${id}/conversations?active_only=true`, { cache: 'no-store' }),
      fetch(`${API_BASE}/worlds/${id}/agents`, { cache: 'no-store' }),
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

    // Get agent status
    let agents = null
    if (agentsRes.ok) {
      agents = await agentsRes.json()
    }

    return {
      world: {
        id: w.id,
        name: w.name,
        premise: w.premise,
        yearSetting: w.year_setting,
        causalChain: w.causal_chain || [],
        createdAt: new Date(w.created_at),
        createdBy: w.created_by,
        dwellerCount: w.dweller_count,
        storyCount: w.story_count,
        followerCount: w.follower_count,
        dwellers: data.dwellers || [],
        stories: data.recent_stories || [],
        recent_events: data.recent_events || [],
        simulation_status: data.simulation_status || 'stopped',
        conversations,
      },
      agents,
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
    <div className="max-w-6xl mx-auto px-4 py-8">
      <WorldDetail world={data.world} agents={data.agents} />
    </div>
  )
}
