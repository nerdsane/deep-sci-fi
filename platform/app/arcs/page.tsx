import { listArcs } from '@/lib/api'
import type { ArcListItem, ArcMomentum } from '@/lib/api'
import Link from 'next/link'

export const metadata = {
  title: 'Story Arcs — Deep Sci-Fi',
  description: 'Narrative threads spanning multiple stories from the same dweller perspective.',
}

type SortOption = 'recent' | 'active' | 'count' | 'world'
type MomentumFilter = 'all' | 'heating_up' | 'active' | 'stalling'

type SearchParams = Record<string, string | string[] | undefined>

const SORT_OPTIONS: Array<{ value: SortOption; label: string }> = [
  { value: 'recent', label: 'Most Recent' },
  { value: 'active', label: 'Most Active' },
  { value: 'count', label: 'Story Count' },
  { value: 'world', label: 'World' },
]

const MOMENTUM_OPTIONS: Array<{ value: MomentumFilter; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'heating_up', label: 'Heating Up' },
  { value: 'active', label: 'Active' },
  { value: 'stalling', label: 'Stalling' },
]

const MOMENTUM_META: Record<
  ArcMomentum,
  { label: string; badgeClass: string; barClass: string }
> = {
  heating_up: {
    label: 'HEATING UP',
    badgeClass: 'text-neon-amber border-neon-amber/50 bg-neon-amber/10',
    barClass: 'bg-neon-amber/90',
  },
  active: {
    label: 'ACTIVE',
    badgeClass: 'text-neon-cyan border-neon-cyan/50 bg-neon-cyan/10',
    barClass: 'bg-neon-cyan/90',
  },
  stalling: {
    label: 'STALLING',
    badgeClass: 'text-text-tertiary border-white/20 bg-white/5',
    barClass: 'bg-white/30',
  },
  concluded: {
    label: 'CONCLUDED',
    badgeClass: 'text-text-muted border-white/10 bg-white/5',
    barClass: 'bg-white/15',
  },
}

function normalizeSort(value: string | undefined): SortOption {
  if (value === 'active' || value === 'count' || value === 'world') return value
  return 'recent'
}

function normalizeMomentum(value: string | undefined): MomentumFilter {
  if (value === 'heating_up' || value === 'active' || value === 'stalling') return value
  return 'all'
}

function getSingleValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}

function buildHref(sort: SortOption, momentum: MomentumFilter): string {
  const params = new URLSearchParams()
  params.set('sort', sort)
  if (momentum !== 'all') params.set('momentum', momentum)
  const query = params.toString()
  return `/arcs${query ? `?${query}` : ''}`
}

function formatRecencyLabel(arc: ArcListItem): string {
  const dayLabel = `${arc.days_since_last_story} day${arc.days_since_last_story === 1 ? '' : 's'}`
  if (arc.momentum === 'stalling' || arc.momentum === 'concluded') {
    return `${dayLabel} stalled`
  }
  if (arc.days_since_last_story === 0) {
    return 'today'
  }
  return `${dayLabel} ago`
}

function sortArcs(arcs: ArcListItem[], sort: SortOption): ArcListItem[] {
  const copy = [...arcs]
  if (sort === 'active') {
    return copy.sort((a, b) => {
      if (b.arc_health_score !== a.arc_health_score) return b.arc_health_score - a.arc_health_score
      if (a.days_since_last_story !== b.days_since_last_story) {
        return a.days_since_last_story - b.days_since_last_story
      }
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    })
  }
  if (sort === 'count') {
    return copy.sort((a, b) => {
      if (b.story_count !== a.story_count) return b.story_count - a.story_count
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    })
  }
  if (sort === 'world') {
    return copy.sort((a, b) => {
      const byWorld = a.world_name.localeCompare(b.world_name)
      if (byWorld !== 0) return byWorld
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    })
  }
  return copy.sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  )
}

function ArcCard({ arc }: { arc: ArcListItem }) {
  const momentumMeta = MOMENTUM_META[arc.momentum]
  const visibleStories = arc.stories.slice(0, 4)
  const hiddenStoryCount = Math.max(0, arc.stories.length - visibleStories.length)

  return (
    <div className="glass overflow-hidden">
      <div className={`h-1 ${momentumMeta.barClass}`} />
      <div className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Link
              href={`/arcs/${arc.id}`}
              className="font-display text-text-primary text-sm md:text-base leading-snug hover:text-neon-cyan transition-colors"
            >
              {arc.name}
            </Link>
            <div className="flex items-center gap-2 text-xs text-text-tertiary flex-wrap mt-1">
              <Link
                href={`/world/${arc.world_id}`}
                className="text-neon-cyan hover:underline truncate max-w-[220px]"
              >
                {arc.world_name}
              </Link>
              {arc.dweller_name && (
                <>
                  <span className="text-text-muted">·</span>
                  <Link
                    href={arc.dweller_id ? `/dweller/${arc.dweller_id}` : '#'}
                    className={arc.dweller_id ? 'hover:underline' : ''}
                  >
                    {arc.dweller_name}
                  </Link>
                </>
              )}
            </div>
          </div>
          <span className="text-[10px] font-mono text-neon-amber border border-neon-amber/30 px-2 py-0.5 bg-neon-amber/5 shrink-0">
            {arc.story_count} {arc.story_count === 1 ? 'STORY' : 'STORIES'}
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[10px] font-mono border px-2 py-0.5 ${momentumMeta.badgeClass}`}>
            {momentumMeta.label}
          </span>
          <span className="text-[11px] text-text-tertiary font-mono">{formatRecencyLabel(arc)}</span>
        </div>

        {arc.summary && (
          <p className="text-xs text-text-secondary leading-relaxed border-l border-white/15 pl-3">
            {arc.summary}
          </p>
        )}

        <div className="space-y-1.5 pt-2 border-t border-white/5">
          {visibleStories.map((story, idx) => (
            <Link
              key={story.id}
              href={`/stories/${story.id}`}
              className="flex items-center gap-2 text-xs text-text-secondary hover:text-neon-cyan transition-colors group"
            >
              <span className="font-mono text-text-muted text-[10px] w-4 shrink-0">{idx + 1}</span>
              <span className="truncate group-hover:underline underline-offset-2">{story.title}</span>
            </Link>
          ))}
          {hiddenStoryCount > 0 && (
            <span className="block text-[10px] text-text-muted font-mono pl-6">
              +{hiddenStoryCount} more stories
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default async function ArcsPage({
  searchParams,
}: {
  searchParams?: SearchParams | Promise<SearchParams>
}) {
  const resolvedParams = await Promise.resolve(searchParams ?? {})
  const sort = normalizeSort(getSingleValue(resolvedParams.sort))
  const momentumFilter = normalizeMomentum(getSingleValue(resolvedParams.momentum))

  let arcsData = null
  try {
    arcsData = await listArcs({ limit: 100 })
  } catch {
    // API may be unavailable during build — render gracefully.
  }

  const allArcs = arcsData?.arcs ?? []
  const filteredArcs =
    momentumFilter === 'all'
      ? allArcs
      : allArcs.filter((arc) => arc.momentum === momentumFilter)
  const arcs = sortArcs(filteredArcs, sort)

  return (
    <div className="py-6 md:py-8">
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12 mb-6 md:mb-8 animate-fade-in">
        <div className="glass-cyan p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-neon-cyan rounded-full shadow-[0_0_8px_var(--neon-cyan)]" />
            <h1 className="font-display text-sm md:text-base text-neon-cyan tracking-wider">STORY ARCS</h1>
          </div>
          <p className="text-text-secondary text-xs md:text-sm">
            Living narrative threads across episodes. Track pace, momentum, and where each thread might be headed.
          </p>

          <div className="mt-5 space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-mono text-text-muted">Sort by:</span>
              {SORT_OPTIONS.map((option) => (
                <Link
                  key={option.value}
                  href={buildHref(option.value, momentumFilter)}
                  className={`px-2.5 py-1 text-[11px] font-mono border transition-colors ${
                    sort === option.value
                      ? 'text-neon-cyan border-neon-cyan/40 bg-neon-cyan/10'
                      : 'text-text-tertiary border-white/10 hover:border-white/20'
                  }`}
                >
                  {option.label}
                </Link>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-mono text-text-muted">Momentum:</span>
              {MOMENTUM_OPTIONS.map((option) => (
                <Link
                  key={option.value}
                  href={buildHref(sort, option.value)}
                  className={`px-2.5 py-1 text-[11px] font-mono border transition-colors ${
                    momentumFilter === option.value
                      ? 'text-neon-amber border-neon-amber/40 bg-neon-amber/10'
                      : 'text-text-tertiary border-white/10 hover:border-white/20'
                  }`}
                >
                  {option.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12">
        {allArcs.length === 0 ? (
          <div className="glass p-8 text-center">
            <p className="text-text-secondary text-sm font-mono mb-2">NO ARCS DETECTED YET</p>
            <p className="text-text-tertiary text-xs">
              Arc detection runs daily. Threads appear as stories accumulate around a shared narrative line.
            </p>
          </div>
        ) : arcs.length === 0 ? (
          <div className="glass p-8 text-center">
            <p className="text-text-secondary text-sm font-mono mb-2">NO MATCHING ARCS</p>
            <p className="text-text-tertiary text-xs">
              Try a different momentum filter.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-[11px] font-mono text-text-muted">
              Showing {arcs.length} of {allArcs.length} arcs
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {arcs.map((arc) => (
                <ArcCard key={arc.id} arc={arc} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
