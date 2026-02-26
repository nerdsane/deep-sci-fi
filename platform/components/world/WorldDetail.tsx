'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import type { World } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ActivityFeed } from './ActivityFeed'
import { AspectsList } from './AspectsList'
import { fadeInUp } from '@/lib/motion'
import { ScrollReveal, StaggerReveal } from '@/components/ui/ScrollReveal'
import {
  IconArrowRight,
  IconPlay,
} from '@/components/ui/PixelIcon'
import { ShareOnX } from '@/components/ui/ShareOnX'

interface Story {
  id: string
  type: string
  title: string
  description?: string
  transcript?: string  // Full storyteller script - deprecated, use content
  content?: string     // Full story narrative
  summary?: string     // Short summary
  cover_image_url?: string
  video_url?: string
  thumbnail_url?: string
  duration_seconds?: number
  created_at: string
  view_count?: number
  reaction_counts?: Record<string, number>
  // Review system fields
  status?: 'published' | 'acclaimed'
  perspective?: string
  perspective_dweller_name?: string
  author_name?: string
  author_username?: string
  review_count?: number
  acclaim_count?: number
  reaction_count?: number
  comment_count?: number
}

interface Dweller {
  id: string
  // Flat structure from API
  name: string
  role: string
  current_region?: string
  is_available: boolean
  portrait_url?: string | null
  // Legacy persona structure for backwards compat with conversations
  persona?: {
    name: string
    role: string
    background?: string
    beliefs?: string[]
    avatar_url?: string
    avatar_prompt?: string
  }
  is_active?: boolean
  joined_at?: string
}

interface ConversationParticipant {
  id: string
  persona: {
    name: string
    role: string
    background?: string
    avatar_url?: string
  } | null
}

interface WorldEvent {
  id: string
  event_type: string
  title: string
  description: string
  timestamp: string
}

interface Conversation {
  id: string
  participants: ConversationParticipant[]
  is_active: boolean
  updated_at?: string
  messages?: Array<{
    id: string
    dweller_id: string
    content: string
    timestamp: string
  }>
}

interface Activity {
  id: string
  dweller: {
    id: string
    name: string
  }
  action_type: string
  target: string | null
  content: string
  created_at: string
}

interface Aspect {
  id: string
  type: string
  title: string
  premise: string
  status: string
  created_at: string
}

interface WorldDetailProps {
  world: World & {
    stories?: Story[]
    dwellers?: Dweller[]
    conversations?: Conversation[]
    recent_events?: WorldEvent[]
    simulation_status?: string
    activity?: Activity[]
    aspects?: Aspect[]
    canonSummary?: string | null
  }
}

type TabType = 'live' | 'stories' | 'timeline' | 'dwellers' | 'aspects'

const VALID_TABS: TabType[] = ['live', 'stories', 'timeline', 'dwellers', 'aspects']

export function WorldDetail({ world }: WorldDetailProps) {
  const searchParams = useSearchParams()
  const tabParam = searchParams.get('tab')
  const initialTab = tabParam && VALID_TABS.includes(tabParam as TabType) ? (tabParam as TabType) : 'live'

  const [activeTab, setActiveTab] = useState<TabType>(initialTab)

  // Update tab when URL param changes
  useEffect(() => {
    if (tabParam && VALID_TABS.includes(tabParam as TabType)) {
      setActiveTab(tabParam as TabType)
    }
  }, [tabParam])

  const simulationRunning = world.simulation_status === 'running'

  return (
    <div className="space-y-8">
      {/* Hero section with glass effect + enhanced glow */}
      <div className="glass-cyan glow-cyan-layered mb-8 relative overflow-hidden">
        {/* Prominent cover image */}
        {world.coverImageUrl && (
          <div className="relative aspect-[21/9] w-full overflow-hidden m-[1px]">
            <img
              src={world.coverImageUrl}
              alt={world.name}
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
          </div>
        )}
        <div className="p-6 md:p-8 relative">
          <div className="mb-6">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <h1 className="text-xl md:text-2xl font-display text-neon-cyan tracking-wide drop-shadow-[0_0_12px_var(--neon-cyan)]">
                  {world.name}
                </h1>
                {simulationRunning && (
                  <span className="px-2 py-1 bg-neon-green/20 text-neon-green text-[10px] font-display tracking-wider border border-neon-green/30 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-neon-green rounded-full animate-pulse shadow-[0_0_6px_var(--neon-green)]" />
                    LIVE
                  </span>
                )}
              </div>
              <ShareOnX
                text={`Check out ${world.name} — a sci-fi world set in ${world.yearSetting}`}
                hashtags={['DeepSciFi']}
              />
            </div>
            <div className="text-text-secondary text-sm">{world.premise}</div>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap items-center gap-4 md:gap-6">
            <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/5">
              <span className="text-neon-cyan font-mono text-sm">{world.dwellerCount || 0}</span>
              <span className="text-text-tertiary text-[10px] font-display tracking-wider">DWELLERS</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/5">
              <span className="text-neon-purple font-mono text-sm">{world.storyCount || 0}</span>
              <span className="text-text-tertiary text-[10px] font-display tracking-wider">STORIES</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.03] border border-white/5">
              <span className="text-neon-green font-mono text-sm">{world.followerCount || 0}</span>
              <span className="text-text-tertiary text-[10px] font-display tracking-wider">FOLLOWING</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-neon-cyan/10 border border-neon-cyan/20">
              <span className="text-neon-cyan font-mono text-sm drop-shadow-[0_0_6px_var(--neon-cyan)]">{world.yearSetting}</span>
              <span className="text-neon-cyan/70 text-[10px] font-display tracking-wider">YEAR</span>
            </div>
          </div>

          {/* Scientific Basis */}
          {world.scientificBasis && (
            <div className="mt-6 pt-4">
              <div className="divider-gradient-cyan mb-4" />
              <h3 className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider mb-2">SCIENTIFIC BASIS</h3>
              <p className="text-text-secondary text-sm leading-relaxed">{world.scientificBasis}</p>
            </div>
          )}

          {/* Regions */}
          {world.regions && world.regions.length > 0 && (
            <div className="mt-4">
              <h3 className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider mb-2">REGIONS</h3>
              <div className="flex flex-wrap gap-2">
                {world.regions.map((region: any, i: number) => (
                  <span key={i} className="text-xs bg-white/5 border border-white/10 px-2 py-1 text-text-secondary">
                    {typeof region === 'string' ? region : region.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 glass mb-6 p-1 overflow-x-auto">
        {VALID_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              px-4 py-2 font-display text-[10px] uppercase tracking-wider
              transition-all shrink-0
              ${
                activeTab === tab
                  ? 'text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30 shadow-[0_0_12px_var(--neon-cyan)/20]'
                  : 'text-text-secondary border border-transparent hover:text-neon-cyan/70 hover:bg-white/[0.02]'
              }
            `}
          >
            {tab === 'live' && (
              <span className="inline-block w-1.5 h-1.5 bg-neon-pink rounded-full mr-1.5 animate-pulse" />
            )}
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div data-testid="activity-feed">
        {activeTab === 'live' && (
          <div className="space-y-8">
            <LiveConversations conversations={world.conversations} dwellers={world.dwellers} />
            <ActivityFeed worldId={world.id} activity={world.activity || []} />
          </div>
        )}
        {activeTab === 'stories' && <StoriesView stories={world.stories} worldId={world.id} />}
        {activeTab === 'timeline' && <TimelineView causalChain={world.causalChain} events={world.recent_events} />}
        {activeTab === 'dwellers' && <DwellersView dwellers={world.dwellers} worldId={world.id} />}
        {activeTab === 'aspects' && (
          <AspectsList
            worldId={world.id}
            aspects={world.aspects || []}
            canonSummary={world.canonSummary}
            originalPremise={world.premise}
          />
        )}
      </div>
    </div>
  )
}

function TimelineView({
  causalChain,
  events,
}: {
  causalChain: { year: number; event: string; consequence: string }[]
  events?: WorldEvent[]
}) {
  return (
    <div className="space-y-8">
      {/* Recent World Events from Puppeteer */}
      {events && events.length > 0 && (
        <div className="mb-8">
          <h3 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-4">
            RECENT EVENTS
          </h3>
          <div className="space-y-3">
            {events.map((event) => (
              <Card key={event.id} className="border-neon-purple/30">
                <CardContent>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <span className="text-[10px] font-mono text-neon-purple uppercase">
                        {event.event_type}
                      </span>
                      <h4 className="text-text-primary text-sm mt-1">{event.title}</h4>
                      <p className="text-text-secondary text-xs mt-1">{event.description}</p>
                    </div>
                    <span className="text-text-tertiary text-xs font-mono shrink-0">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Historical Causal Chain */}
      {causalChain.length > 0 && (
        <>
          <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-4">
            TIMELINE
          </h3>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[60px] top-0 bottom-0 w-px bg-white/10" />

            <StaggerReveal className="space-y-6">
              {causalChain.map((event, index) => (
                <motion.div key={index} variants={fadeInUp} className="relative flex gap-6">
                  {/* Year marker */}
                  <div className="w-[50px] shrink-0 text-right">
                    <span className="font-mono text-neon-cyan text-sm">{event.year}</span>
                  </div>

                  {/* Dot on timeline */}
                  <div className="relative">
                    <div className="absolute left-[10px] top-2 w-3 h-3 bg-neon-cyan/30 border border-neon-cyan" />
                  </div>

                  {/* Content */}
                  <Card className="flex-1 ml-4" hover={false}>
                    <CardContent>
                      <div className="text-text-primary text-xs mb-1">{event.event}</div>
                      <div className="text-text-tertiary text-[10px] flex items-start gap-1">
                        <span className="text-neon-purple shrink-0"><IconArrowRight size={12} /></span>
                        {event.consequence}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </StaggerReveal>
          </div>
        </>
      )}

      {causalChain.length === 0 && (!events || events.length === 0) && (
        <div className="text-center py-12 text-text-secondary">
          <p className="text-sm mb-1">No events yet.</p>
          <p className="text-sm">Events will appear as the world unfolds.</p>
        </div>
      )}
    </div>
  )
}

function LiveConversations({
  conversations,
  dwellers
}: {
  conversations?: Conversation[]
  dwellers?: Dweller[]
}) {
  // Build persona map from both conversation participants and dwellers list
  const personaMap = new Map<string, { name: string; role: string; avatar_url?: string }>()

  // Add personas from dwellers (handle both flat and nested structure)
  dwellers?.forEach(d => {
    if (d.persona) {
      personaMap.set(d.id, d.persona)
    } else {
      personaMap.set(d.id, { name: d.name, role: d.role })
    }
  })

  // Add/override with personas from conversation participants (more up-to-date)
  conversations?.forEach(conv => {
    conv.participants.forEach(p => {
      if (p.persona) {
        personaMap.set(p.id, p.persona)
      }
    })
  })

  const activeConvs = conversations?.filter(c => c.is_active) || []

  // Also show conversations with messages even if not marked active
  const convsWithMessages = conversations?.filter(c =>
    c.messages && c.messages.length > 0
  ) || []

  const displayConvs = activeConvs.length > 0 ? activeConvs : convsWithMessages

  if (displayConvs.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      {displayConvs.map((conv) => (
        <Card key={conv.id}>
          <CardContent>
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-text-tertiary">
              <span className="w-2 h-2 bg-neon-green rounded-full animate-pulse" />
              {conv.is_active ? 'LIVE' : 'RECENT'}
            </div>
            <div className="max-h-80 overflow-y-auto space-y-4">
              {conv.messages?.map((msg) => {
                const persona = personaMap.get(msg.dweller_id)
                return (
                  <div key={msg.id} className="flex gap-3">
                    {persona?.avatar_url ? (
                      <img
                        src={persona.avatar_url}
                        alt={persona.name}
                        className="w-8 h-8 rounded object-cover shrink-0"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded bg-neon-cyan/20 flex items-center justify-center text-xs font-mono text-neon-cyan shrink-0">
                        {persona?.name?.charAt(0) || '?'}
                      </div>
                    )}
                    <div className="flex-1">
                      <div className="text-sm text-neon-cyan mb-1">
                        {persona?.name || 'Unknown'}
                        <span className="text-text-tertiary ml-2 text-xs">{persona?.role}</span>
                      </div>
                      <div className="text-text-secondary text-sm whitespace-pre-wrap">
                        {msg.content.slice(0, 300)}{msg.content.length > 300 ? '...' : ''}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// Story status badge component
function StoryStatusBadge({ status }: { status?: 'published' | 'acclaimed' }) {
  if (status === 'acclaimed') {
    return (
      <span className="text-[10px] font-display tracking-wider px-2 py-0.5 border text-neon-green bg-neon-green/10 border-neon-green/30 badge-pulse-acclaimed">
        ACCLAIMED
      </span>
    )
  }
  return (
    <span className="text-[10px] font-display tracking-wider px-2 py-0.5 border text-text-tertiary bg-white/5 border-white/10">
      PUBLISHED
    </span>
  )
}

function StoriesView({ stories, worldId }: { stories?: Story[]; worldId?: string }) {
  const router = useRouter()
  const [statusFilter, setStatusFilter] = useState<'all' | 'published' | 'acclaimed'>('all')
  const [sortBy, setSortBy] = useState<'engagement' | 'recent'>('engagement')

  if (!stories || stories.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">No stories yet.</p>
        <p className="text-sm">Storyteller is watching.</p>
      </div>
    )
  }

  // Filter and sort stories
  let filteredStories = [...stories]
  if (statusFilter !== 'all') {
    filteredStories = filteredStories.filter(s => s.status === statusFilter)
  }

  // Sort stories
  if (sortBy === 'engagement') {
    // Acclaimed first, then by reaction_count
    filteredStories.sort((a, b) => {
      if (a.status === 'acclaimed' && b.status !== 'acclaimed') return -1
      if (b.status === 'acclaimed' && a.status !== 'acclaimed') return 1
      return (b.reaction_count || 0) - (a.reaction_count || 0)
    })
  } else {
    filteredStories.sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
  }

  // Grid view with filter bar
  return (
    <div className="space-y-6">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-4 glass p-3">
        <span className="text-[10px] font-display tracking-wider text-text-tertiary">FILTER:</span>
        <div className="flex gap-1">
          {(['all', 'published', 'acclaimed'] as const).map((filter) => (
            <button
              key={filter}
              onClick={() => setStatusFilter(filter)}
              className={`
                px-3 py-1 text-[10px] font-display tracking-wider uppercase transition-all
                ${statusFilter === filter
                  ? 'text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30'
                  : 'text-text-tertiary border border-transparent hover:text-neon-cyan/70'
                }
              `}
            >
              {filter}
            </button>
          ))}
        </div>
        <span className="text-white/20">|</span>
        <span className="text-[10px] font-display tracking-wider text-text-tertiary">SORT:</span>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'engagement' | 'recent')}
          className="bg-transparent text-text-secondary text-xs font-mono border border-white/10 px-2 py-1 focus:outline-none focus:border-neon-cyan/30"
        >
          <option value="engagement">Engagement</option>
          <option value="recent">Recent</option>
        </select>
      </div>

      {filteredStories.length === 0 ? (
        <div className="text-center py-12 text-text-secondary">
          <p className="text-sm">No {statusFilter} stories found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredStories.map((story) => (
            <Card
              key={story.id}
              className="cursor-pointer hover:border-neon-cyan/30 transition-colors"
              onClick={() => router.push(`/stories/${story.id}`)}
            >
              {/* Video/thumbnail/cover image */}
              <div className="aspect-video bg-bg-tertiary relative overflow-hidden">
                {story.video_url ? (
                  <video
                    src={story.video_url}
                    className="w-full h-full object-cover"
                    poster={story.thumbnail_url || story.cover_image_url}
                  />
                ) : story.thumbnail_url ? (
                  <img
                    src={story.thumbnail_url}
                    alt={story.title}
                    className="w-full h-full object-cover"
                  />
                ) : story.cover_image_url ? (
                  <img
                    src={story.cover_image_url}
                    alt={story.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-neon-purple/20 to-neon-cyan/20">
                    <span className="text-text-tertiary text-sm font-mono">
                      {story.type?.toUpperCase() || 'STORY'}
                    </span>
                  </div>
                )}
                {/* Status badge overlay */}
                <div className="absolute top-2 right-2">
                  <StoryStatusBadge status={story.status} />
                </div>
                {/* Play overlay */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/30 text-white">
                  <IconPlay size={48} />
                </div>
              </div>
              <CardContent>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-sm text-text-primary flex-1 line-clamp-1">{story.title}</h3>
                  {story.duration_seconds && story.duration_seconds > 0 && (
                    <span className="text-text-tertiary text-xs font-mono">
                      {Math.floor(story.duration_seconds / 60)}:{String(story.duration_seconds % 60).padStart(2, '0')}
                    </span>
                  )}
                </div>
                {story.author_username && (
                  <p className="text-text-tertiary text-xs mb-2">
                    by <span className="text-neon-cyan">{story.author_username}</span>
                  </p>
                )}
                {(story.summary || story.description) && (
                  <p className="text-text-secondary text-sm line-clamp-2">{story.summary || story.description}</p>
                )}
                <div className="flex items-center gap-4 text-text-tertiary text-xs font-mono mt-2">
                  <span>{new Date(story.created_at).toLocaleDateString()}</span>
                  {story.reaction_count !== undefined && story.reaction_count > 0 && (
                    <span>{story.reaction_count} reactions</span>
                  )}
                  {story.review_count !== undefined && story.review_count > 0 && (
                    <span>{story.review_count} reviews</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function DwellerListAvatar({ name, portraitUrl }: { name: string; portraitUrl?: string | null }) {
  const [imgError, setImgError] = useState(false)

  if (portraitUrl && !imgError) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={portraitUrl}
        alt={name}
        className="w-10 h-10 rounded object-cover shrink-0"
        onError={() => setImgError(true)}
      />
    )
  }

  return (
    <div className="w-10 h-10 rounded bg-neon-cyan/20 flex items-center justify-center text-sm font-mono text-neon-cyan shrink-0">
      {name.charAt(0) || '?'}
    </div>
  )
}

function DwellersView({ dwellers, worldId }: { dwellers?: Dweller[]; worldId: string }) {
  if (!dwellers || dwellers.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">No dwellers yet.</p>
        <p className="text-sm">Create one to inhabit this world.</p>
      </div>
    )
  }

  return (
    <StaggerReveal className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {dwellers.map((dweller) => {
        // Support both flat structure (from API) and nested persona structure (from conversations)
        const name = dweller.name || dweller.persona?.name || 'Unknown'
        const role = dweller.role || dweller.persona?.role || 'Dweller'
        const portraitUrl = dweller.portrait_url || dweller.persona?.avatar_url

        return (
          <motion.div key={dweller.id} variants={fadeInUp}>
            <a
              href={`/dweller/${dweller.id}`}
              className="block bg-bg-secondary border border-white/5 rounded p-3 hover:border-neon-cyan/30 transition-colors"
            >
              <div className="flex items-center gap-3">
                <DwellerListAvatar name={name} portraitUrl={portraitUrl} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary truncate">{name}</span>
                    {!dweller.is_available && (
                      <span className="w-2 h-2 bg-neon-green rounded-full shrink-0" title="Inhabited" />
                    )}
                  </div>
                  <div className="text-xs text-text-tertiary">{role}</div>
                  {dweller.current_region && (
                    <div className="text-xs text-text-tertiary mt-0.5">{dweller.current_region}</div>
                  )}
                </div>
              </div>
            </a>
          </motion.div>
        )
      })}
    </StaggerReveal>
  )
}

