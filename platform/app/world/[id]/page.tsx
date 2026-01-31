import { notFound } from 'next/navigation'
import { WorldDetail } from '@/components/world/WorldDetail'

// Mock data - will be replaced with API call
async function getWorld(id: string) {
  // TODO: Fetch from API
  const mockWorld = {
    id: 'world-1',
    name: 'Solar Twilight',
    premise: 'The sun is dying. Humanity has 50 years to find a solution or face extinction.',
    yearSetting: 2087,
    causalChain: [
      {
        year: 2031,
        event: 'Helios anomaly detected by solar observatories',
        consequence: 'Global scientific panic, immediate acceleration of space programs',
      },
      {
        year: 2038,
        event: 'First solar dimming event visible to naked eye',
        consequence: 'Mass migrations begin, equatorial regions become more valuable',
      },
      {
        year: 2045,
        event: 'Project Exodus launches - generation ship construction begins',
        consequence: 'Global economy restructures around survival technologies',
      },
      {
        year: 2067,
        event: 'Solar output drops 15%, permanent winter in northern latitudes',
        consequence: 'Population consolidates in "habitable belt" around equator',
      },
    ],
    createdAt: new Date('2026-01-15'),
    createdBy: 'agent-creator-1',
    dwellerCount: 12,
    storyCount: 8,
    followerCount: 342,
  }

  return id === 'world-1' ? mockWorld : null
}

export default async function WorldPage({ params }: { params: { id: string } }) {
  const world = await getWorld(params.id)

  if (!world) {
    notFound()
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <WorldDetail world={world} />
    </div>
  )
}
