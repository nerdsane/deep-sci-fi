import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getArc, listArcs } from '@/lib/api'
import type { ArcDetailItem, ArcListItem, ArcMomentum } from '@/lib/api'

type Props = { params: Promise<{ id: string }> }

type TimelineStory = ArcDetailItem['stories'][number] & {
  gap_days: number
}

const MOMENTUM_META: Record<
  ArcMomentum,
  { label: string; badgeClass: string; barClass: string; nodeClass: string }
> = {
  heating_up: {
    label: 'HEATING UP',
    badgeClass: 'text-neon-amber border-neon-amber/50 bg-neon-amber/10',
    barClass: 'bg-neon-amber/90',
    nodeClass: 'border-neon-amber/80 bg-neon-amber/20',
  },
  active: {
    label: 'ACTIVE',
    badgeClass: 'text-neon-cyan border-neon-cyan/50 bg-neon-cyan/10',
    barClass: 'bg-neon-cyan/90',
    nodeClass: 'border-neon-cyan/80 bg-neon-cyan/20',
  },
  stalling: {
    label: 'STALLING',
    badgeClass: 'text-text-tertiary border-white/20 bg-white/5',
    barClass: 'bg-white/30',
    nodeClass: 'border-white/40 bg-white/10',
  },
  concluded: {
    label: 'CONCLUDED',
    badgeClass: 'text-text-muted border-white/10 bg-white/5',
    barClass: 'bg-white/15',
    nodeClass: 'border-white/30 bg-white/5',
  },
}

function timestamp(dateString: string): number {
  const value = Date.parse(dateString)
  return Number.isNaN(value) ? 0 : value
}

function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDaysSince(momentum: ArcMomentum, daysSinceLastStory: number): string {
  if (daysSinceLastStory === 0) {
    return momentum === 'stalling' || momentum === 'concluded' ? 'stalled today' : 'today'
  }
  const dayLabel = `${daysSinceLastStory} day${daysSinceLastStory === 1 ? '' : 's'}`
  if (momentum === 'stalling' || momentum === 'concluded') {
    return `${dayLabel} stalled`
  }
  return `${dayLabel} ago`
}

function buildTimelineStories(stories: ArcDetailItem['stories']): TimelineStory[] {
  const ordered = [...stories].sort((a, b) => timestamp(a.created_at) - timestamp(b.created_at))
  return ordered.map((story, index) => {
    if (index === 0) {
      return { ...story, gap_days: 0 }
    }
    const previous = ordered[index - 1]
    const diffMs = timestamp(story.created_at) - timestamp(previous.created_at)
    const gapDays = diffMs > 0 ? Math.floor(diffMs / 86_400_000) : 0
    return { ...story, gap_days: gapDays }
  })
}

async function getArcPageData(arcId: string): Promise<{ arc: ArcDetailItem; relatedArcs: ArcListItem[] } | null> {
  try {
    const arcResponse = await getArc(arcId)
    const arc = arcResponse.arc

    let relatedArcs: ArcListItem[] = []
    try {
      const worldArcs = await listArcs({ world_id: arc.world_id, limit: 20 })
      relatedArcs = worldArcs.arcs.filter((candidate) => candidate.id !== arc.id).slice(0, 5)
    } catch {
      // Related arcs are optional for this page.
    }

    return { arc, relatedArcs }
  } catch {
    return null
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params
  try {
    const data = await getArc(id)
    const arc = data.arc
    return {
      title: `${arc.name} — Story Arc | Deep Sci-Fi`,
      description:
        arc.summary ??
        `${arc.story_count} stories following a narrative thread in ${arc.world_name}.`,
    }
  } catch {
    return {}
  }
}

export default async function ArcDetailPage({ params }: Props) {
  const { id } = await params
  const data = await getArcPageData(id)

  if (!data) {
    notFound()
  }

  const { arc, relatedArcs } = data
  const momentumMeta = MOMENTUM_META[arc.momentum]
  const timelineStories = buildTimelineStories(arc.stories)

  return (
    <div className="py-6 md:py-8">
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12 space-y-5">
        <Link
          href="/arcs"
          className="inline-flex items-center gap-2 text-xs font-mono text-text-tertiary hover:text-neon-cyan transition-colors"
        >
          <span>&larr;</span>
          Back to arcs
        </Link>

        <section className="glass overflow-hidden animate-fade-in">
          <div className={`h-1 ${momentumMeta.barClass}`} />
          <div className="p-5 md:p-6 space-y-4">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="space-y-2 min-w-0">
                <h1 className="font-display text-base md:text-lg text-text-primary leading-tight">{arc.name}</h1>
                <div className="flex items-center flex-wrap gap-2 text-xs text-text-tertiary">
                  <Link href={`/world/${arc.world_id}`} className="text-neon-cyan hover:underline">
                    {arc.world_name}
                  </Link>
                  {arc.dweller_name && (
                    <>
                      <span className="text-text-muted">·</span>
                      {arc.dweller_id ? (
                        <Link href={`/dweller/${arc.dweller_id}`} className="hover:underline">
                          {arc.dweller_name}
                        </Link>
                      ) : (
                        <span>{arc.dweller_name}</span>
                      )}
                    </>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <span className={`text-[10px] font-mono border px-2 py-0.5 ${momentumMeta.badgeClass}`}>
                  {momentumMeta.label}
                </span>
                <span className="text-[10px] font-mono text-neon-amber border border-neon-amber/30 px-2 py-0.5 bg-neon-amber/5">
                  {arc.story_count} {arc.story_count === 1 ? 'STORY' : 'STORIES'}
                </span>
              </div>
            </div>

            {arc.summary && (
              <p className="text-sm text-text-secondary leading-relaxed border-l border-white/15 pl-3">
                {arc.summary}
              </p>
            )}
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <section className="lg:col-span-2">
            <div className="glass p-5 md:p-6 space-y-5">
              <div>
                <h2 className="font-display text-xs text-neon-cyan tracking-wider">STORY TIMELINE</h2>
                <p className="text-[11px] text-text-tertiary mt-1">
                  Stories are ordered chronologically to surface pacing and gaps between episodes.
                </p>
              </div>

              <div className="space-y-4">
                {timelineStories.map((story, index) => {
                  const visualUrl = story.thumbnail_url || story.cover_image_url
                  const isLast = index === timelineStories.length - 1

                  return (
                    <div key={story.id}>
                      {story.gap_days > 0 && (
                        <div className="ml-7 mb-2 text-[10px] font-mono text-text-muted">
                          {story.gap_days} day{story.gap_days === 1 ? '' : 's'} gap
                        </div>
                      )}

                      <div className="relative pl-7">
                        {!isLast && <div className="absolute left-[10px] top-6 bottom-[-18px] w-px bg-white/10" />}
                        <span className={`absolute left-0 top-1.5 h-5 w-5 rounded-full border ${momentumMeta.nodeClass}`} />

                        <article className="border border-white/10 bg-white/[0.02] p-3 md:p-4">
                          <div className="flex gap-3">
                            <Link
                              href={`/stories/${story.id}`}
                              className="w-24 h-16 md:w-28 md:h-20 border border-white/10 bg-white/[0.03] overflow-hidden shrink-0"
                            >
                              {visualUrl ? (
                                <img
                                  src={visualUrl}
                                  alt={story.title}
                                  className="w-full h-full object-cover"
                                  loading="lazy"
                                />
                              ) : (
                                <div className="h-full w-full bg-gradient-to-br from-neon-cyan/15 to-neon-purple/10" />
                              )}
                            </Link>

                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between gap-3 flex-wrap">
                                <Link
                                  href={`/stories/${story.id}`}
                                  className="text-sm text-text-primary hover:text-neon-cyan transition-colors leading-snug"
                                >
                                  {story.title}
                                </Link>
                                <span className="text-[10px] font-mono text-text-tertiary shrink-0">
                                  {formatDateTime(story.created_at)}
                                </span>
                              </div>
                              {story.summary && (
                                <p className="text-xs text-text-secondary mt-1.5 leading-relaxed">
                                  {story.summary}
                                </p>
                              )}
                            </div>
                          </div>
                        </article>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </section>

          <aside className="space-y-4">
            <section className="glass p-5 space-y-3">
              <h2 className="font-display text-xs text-neon-amber tracking-wider">ARC METADATA</h2>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-muted font-mono">World</span>
                  <Link href={`/world/${arc.world_id}`} className="text-neon-cyan hover:underline truncate max-w-[180px]">
                    {arc.world_name}
                  </Link>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-muted font-mono">Dweller</span>
                  <span className="text-text-secondary truncate max-w-[180px]">{arc.dweller_name || 'Unknown'}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-muted font-mono">Momentum</span>
                  <span className="text-text-secondary">{momentumMeta.label}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-muted font-mono">Last Story</span>
                  <span className="text-text-secondary">{formatDaysSince(arc.momentum, arc.days_since_last_story)}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-text-muted font-mono">Health</span>
                  <span className="text-text-secondary">{Math.round(arc.arc_health_score * 100)}%</span>
                </div>
              </div>
            </section>

            <section className="glass p-5 space-y-3">
              <h2 className="font-display text-xs text-neon-cyan tracking-wider">RELATED ARCS</h2>
              {relatedArcs.length === 0 ? (
                <p className="text-xs text-text-tertiary">
                  No other arcs in this world yet.
                </p>
              ) : (
                <div className="space-y-2">
                  {relatedArcs.map((related) => {
                    const relatedMeta = MOMENTUM_META[related.momentum]
                    return (
                      <Link
                        key={related.id}
                        href={`/arcs/${related.id}`}
                        className="block border border-white/10 bg-white/[0.02] p-3 hover:border-neon-cyan/35 transition-colors"
                      >
                        <p className="text-xs text-text-primary leading-snug">{related.name}</p>
                        <div className="mt-1.5 flex items-center justify-between gap-2">
                          <span className={`text-[9px] font-mono border px-1.5 py-0.5 ${relatedMeta.badgeClass}`}>
                            {relatedMeta.label}
                          </span>
                          <span className="text-[10px] font-mono text-text-tertiary">
                            {related.story_count} stories
                          </span>
                        </div>
                      </Link>
                    )
                  })}
                </div>
              )}
            </section>
          </aside>
        </div>
      </div>
    </div>
  )
}
