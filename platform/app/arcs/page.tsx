import { listArcs } from '@/lib/api'
import type { ArcListItem } from '@/lib/api'
import Link from 'next/link'
import { formatRelativeTime } from '@/lib/utils'

export const metadata = {
  title: 'Story Arcs — Deep Sci-Fi',
  description: 'Narrative threads spanning multiple stories from the same dweller perspective.',
}

function ArcCard({ arc }: { arc: ArcListItem }) {
  return (
    <div className="glass p-5 space-y-3">
      {/* Arc name + meta */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-display text-text-primary text-sm md:text-base leading-snug mb-1">
            {arc.name}
          </h3>
          <div className="flex items-center gap-2 text-xs text-text-tertiary flex-wrap">
            <Link
              href={`/worlds/${arc.world_id}`}
              className="text-neon-cyan hover:underline truncate max-w-[200px]"
            >
              {arc.world_name}
            </Link>
            {arc.dweller_name && (
              <>
                <span className="text-text-muted">·</span>
                <span>{arc.dweller_name}</span>
              </>
            )}
            <span className="text-text-muted">·</span>
            <span>{formatRelativeTime(arc.updated_at)}</span>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <span className="text-[10px] font-mono text-neon-amber border border-neon-amber/30 px-2 py-0.5 bg-neon-amber/5">
            {arc.story_count} {arc.story_count === 1 ? 'STORY' : 'STORIES'}
          </span>
        </div>
      </div>

      {/* Story list with titles */}
      <div className="space-y-1.5 pt-1 border-t border-white/5">
        {arc.stories.map((story, idx) => (
          <Link
            key={story.id}
            href={`/stories/${story.id}`}
            className="flex items-center gap-2 text-xs text-text-secondary hover:text-neon-cyan transition-colors group"
          >
            <span className="font-mono text-text-muted text-[10px] w-4 shrink-0">{idx + 1}</span>
            <span className="truncate group-hover:underline underline-offset-2">{story.title}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}

export default async function ArcsPage() {
  let arcsData = null
  try {
    arcsData = await listArcs({ limit: 50 })
  } catch {
    // API may be unavailable during build — render gracefully
  }

  const arcs = arcsData?.arcs ?? []

  // Group arcs by world
  const byWorld: Record<string, { worldName: string; worldId: string; arcs: ArcListItem[] }> = {}
  for (const arc of arcs) {
    if (!byWorld[arc.world_id]) {
      byWorld[arc.world_id] = { worldName: arc.world_name, worldId: arc.world_id, arcs: [] }
    }
    byWorld[arc.world_id].arcs.push(arc)
  }

  return (
    <div className="py-6 md:py-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12 mb-6 md:mb-8 animate-fade-in">
        <div className="glass-cyan p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-neon-cyan rounded-full shadow-[0_0_8px_var(--neon-cyan)]" />
            <h1 className="font-display text-sm md:text-base text-neon-cyan tracking-wider">STORY ARCS</h1>
          </div>
          <p className="text-text-secondary text-xs md:text-sm">
            Narrative threads detected across multiple stories. Follow a dweller's ongoing story across episodes.
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12">
        {arcs.length === 0 ? (
          <div className="glass p-8 text-center">
            <p className="text-text-secondary text-sm font-mono mb-2">NO ARCS DETECTED YET</p>
            <p className="text-text-tertiary text-xs">
              Arc detection runs daily. Arcs form when 2+ related stories from the same dweller appear within 7 days.
            </p>
          </div>
        ) : (
          <div className="space-y-10">
            {Object.values(byWorld).map(({ worldName, worldId, arcs: worldArcs }) => (
              <section key={worldId}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-1.5 h-1.5 bg-neon-purple rounded-full" />
                  <Link
                    href={`/worlds/${worldId}`}
                    className="text-xs font-mono text-text-secondary hover:text-neon-cyan tracking-wider uppercase transition-colors"
                  >
                    {worldName}
                  </Link>
                  <span className="text-[10px] text-text-muted font-mono">
                    {worldArcs.length} {worldArcs.length === 1 ? 'ARC' : 'ARCS'}
                  </span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {worldArcs.map((arc) => (
                    <ArcCard key={arc.id} arc={arc} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
