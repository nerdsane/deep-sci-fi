'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import type { World } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ActivityFeed } from './ActivityFeed'
import { AspectsList } from './AspectsList'
import {
  IconArrowLeft,
  IconArrowRight,
  IconPlay,
  IconMoodHappy,
  IconEye,
  IconCardStack,
} from '@/components/ui/PixelIcon'

interface Story {
  id: string
  type: string
  title: string
  description?: string
  transcript?: string  // Full storyteller script
  video_url?: string
  thumbnail_url?: string
  duration_seconds?: number
  created_at: string
  view_count?: number
  reaction_counts?: Record<string, number>
}

interface Dweller {
  id: string
  persona: {
    name: string
    role: string
    background?: string
    beliefs?: string[]
    avatar_url?: string
    avatar_prompt?: string
  }
  is_active: boolean
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

interface AgentStatus {
  puppeteer: {
    status: string
    events_count: number
    last_event: string | null
  }
  storyteller: {
    status: string
    observations_count: number
    stories_created: number
    last_activity: string | null
  }
  critic: {
    status: string
    evaluations_count: number
    last_evaluation: string | null
    average_score: number | null
  }
  dweller_agents: Array<{
    dweller_id: string
    activity: string
    conversation_id: string | null
    last_active: string
  }>
  tick_count: number
  simulation_status: string
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
  agents?: AgentStatus
}

type TabType = 'live' | 'activity' | 'stories' | 'timeline' | 'characters' | 'aspects' | 'agents'

const VALID_TABS: TabType[] = ['live', 'activity', 'stories', 'timeline', 'characters', 'aspects', 'agents']

export function WorldDetail({ world, agents }: WorldDetailProps) {
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
      {/* Hero section with glass effect */}
      <div className="glass-cyan mb-8">
        <div className="p-6 md:p-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <div className="flex items-center gap-3 mb-3">
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
              <div className="text-text-secondary text-sm max-w-2xl">{world.premise}</div>
            </div>
{/* Follow/Share buttons hidden until functionality is implemented */}
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
        {activeTab === 'live' && <LiveConversations conversations={world.conversations} dwellers={world.dwellers} />}
        {activeTab === 'activity' && <ActivityFeed worldId={world.id} activity={world.activity || []} />}
        {activeTab === 'stories' && <StoriesView stories={world.stories} />}
        {activeTab === 'timeline' && <TimelineView causalChain={world.causalChain} events={world.recent_events} />}
        {activeTab === 'characters' && <DwellersView dwellers={world.dwellers} />}
        {activeTab === 'aspects' && (
          <AspectsList
            worldId={world.id}
            aspects={world.aspects || []}
            canonSummary={world.canonSummary}
            originalPremise={world.premise}
          />
        )}
        {activeTab === 'agents' && <AgentsView agents={agents} dwellers={world.dwellers} />}
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

            <div className="space-y-6">
              {causalChain.map((event, index) => (
                <div key={index} className="relative flex gap-6">
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
                </div>
              ))}
            </div>
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

  // Add personas from dwellers
  dwellers?.forEach(d => {
    personaMap.set(d.id, d.persona)
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
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">Quiet right now.</p>
        <p className="text-sm">Characters are idle.</p>
      </div>
    )
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

function StoriesView({ stories }: { stories?: Story[] }) {
  const [expandedStory, setExpandedStory] = useState<string | null>(null)

  if (!stories || stories.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">No stories yet.</p>
        <p className="text-sm">Storyteller is watching.</p>
      </div>
    )
  }

  const expanded = expandedStory ? stories.find(s => s.id === expandedStory) : null

  // Expanded story view
  if (expanded) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => setExpandedStory(null)}
          className="text-neon-cyan hover:text-neon-cyan/80 font-mono text-sm flex items-center gap-2"
        >
          <IconArrowLeft size={16} /> STORIES
        </button>

        <div className="max-w-3xl">
          {/* Video/thumbnail */}
          <div className="aspect-video bg-bg-tertiary relative overflow-hidden mb-6">
            {expanded.video_url ? (
              <video
                src={expanded.video_url}
                className="w-full h-full object-cover"
                controls
                autoPlay
                poster={expanded.thumbnail_url}
              />
            ) : expanded.thumbnail_url ? (
              <img
                src={expanded.thumbnail_url}
                alt={expanded.title}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-neon-purple/20 to-neon-cyan/20">
                <span className="text-text-tertiary font-mono">
                  {expanded.type?.toUpperCase() || 'STORY'}
                </span>
              </div>
            )}
          </div>

          <h1 className="text-lg text-neon-cyan mb-4">{expanded.title}</h1>

          <div className="flex items-center gap-4 text-text-tertiary text-xs font-mono mb-6">
            <span>{new Date(expanded.created_at).toLocaleDateString()}</span>
            {expanded.duration_seconds && expanded.duration_seconds > 0 && (
              <span>{Math.floor(expanded.duration_seconds / 60)}:{String(expanded.duration_seconds % 60).padStart(2, '0')}</span>
            )}
            {expanded.view_count !== undefined && expanded.view_count > 0 && (
              <span>{expanded.view_count} views</span>
            )}
          </div>

          {expanded.description && (
            <div className="text-text-secondary leading-relaxed mb-6">
              {expanded.description}
            </div>
          )}

          {/* Full storyteller script */}
          {expanded.transcript ? (
            <div className="mt-4 p-6 border border-white/10 bg-bg-tertiary">
              <p className="text-neon-cyan text-sm font-mono mb-4">SCRIPT</p>
              <div className="text-text-secondary leading-relaxed whitespace-pre-wrap font-mono text-sm">
                {expanded.transcript}
              </div>
            </div>
          ) : (
            <div className="mt-8 p-4 border border-white/10 bg-bg-tertiary">
              <p className="text-text-tertiary text-sm font-mono mb-2">SCRIPT</p>
              <p className="text-text-secondary text-sm italic">
                No script recorded.
              </p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Grid view
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {stories.map((story) => (
        <Card
          key={story.id}
          className="cursor-pointer hover:border-neon-cyan/30 transition-colors"
          onClick={() => setExpandedStory(story.id)}
        >
          {/* Video/thumbnail */}
          <div className="aspect-video bg-bg-tertiary relative overflow-hidden">
            {story.video_url ? (
              <video
                src={story.video_url}
                className="w-full h-full object-cover"
                poster={story.thumbnail_url}
              />
            ) : story.thumbnail_url ? (
              <img
                src={story.thumbnail_url}
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
            {/* Play overlay */}
            <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/30 text-white">
              <IconPlay size={48} />
            </div>
          </div>
          <CardContent>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-sm text-text-primary flex-1">{story.title}</h3>
              {story.duration_seconds && story.duration_seconds > 0 && (
                <span className="text-text-tertiary text-xs font-mono">
                  {Math.floor(story.duration_seconds / 60)}:{String(story.duration_seconds % 60).padStart(2, '0')}
                </span>
              )}
            </div>
            {story.description && (
              <p className="text-text-secondary text-sm line-clamp-2">{story.description}</p>
            )}
            <div className="flex items-center gap-4 text-text-tertiary text-xs font-mono mt-2">
              <span>{new Date(story.created_at).toLocaleDateString()}</span>
              {story.view_count !== undefined && story.view_count > 0 && (
                <span>{story.view_count} views</span>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function DwellersView({ dwellers }: { dwellers?: Dweller[] }) {
  if (!dwellers || dwellers.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">No characters yet.</p>
        <p className="text-sm">Waiting for agents to inhabit characters.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {dwellers.map((dweller) => (
        <Card key={dweller.id}>
          <CardContent>
            <div className="flex items-start gap-3">
              {dweller.persona.avatar_url ? (
                <img
                  src={dweller.persona.avatar_url}
                  alt={dweller.persona.name}
                  className="w-12 h-12 rounded object-cover shrink-0"
                />
              ) : (
                <div className="w-12 h-12 rounded bg-neon-cyan/20 flex items-center justify-center text-lg font-mono text-neon-cyan shrink-0">
                  {dweller.persona.name?.charAt(0) || '?'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-text-primary font-medium truncate">
                    {dweller.persona.name}
                  </h3>
                  {dweller.is_active && (
                    <span className="w-2 h-2 bg-neon-green rounded-full" title="Active" />
                  )}
                </div>
                <div className="text-neon-purple text-sm">{dweller.persona.role}</div>
                {dweller.persona.background && (
                  <p className="text-text-secondary text-xs mt-2 line-clamp-2">
                    {dweller.persona.background}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function AgentsView({
  agents,
  dwellers,
}: {
  agents?: AgentStatus
  dwellers?: Dweller[]
}) {
  if (!agents) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">Agent status unavailable</p>
        <p className="text-sm">Start the simulation to see agent activity...</p>
      </div>
    )
  }

  const dwellerMap = new Map<string, Dweller>()
  dwellers?.forEach(d => dwellerMap.set(d.id, d))

  return (
    <div className="space-y-8">
      {/* Simulation Status */}
      <div className="flex items-center gap-4 p-4 border border-white/10 rounded">
        <div className="flex items-center gap-2">
          <span
            className={`w-3 h-3 rounded-full ${
              agents.simulation_status === 'running' ? 'bg-neon-green animate-pulse' : 'bg-text-muted'
            }`}
          />
          <span className="font-mono text-sm uppercase">
            Simulation {agents.simulation_status}
          </span>
        </div>
        <span className="text-text-tertiary text-xs font-mono">
          Tick #{agents.tick_count}
        </span>
      </div>

      {/* Puppeteer Status */}
      <Card>
        <CardContent>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-neon-purple font-mono text-sm uppercase tracking-wider mb-2">
                PUPPETEER
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Introduces world events
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.puppeteer.status === 'active' ? 'text-neon-green' : 'text-text-muted'}>
                  {agents.puppeteer.status.toUpperCase()}
                </span>
                <span className="text-text-tertiary">
                  {agents.puppeteer.events_count} events
                </span>
                {agents.puppeteer.last_event && (
                  <span className="text-text-tertiary">
                    Last: {new Date(agents.puppeteer.last_event).toLocaleTimeString()}
                  </span>
                )}
              </div>
            </div>
            <div className="w-10 h-10 bg-neon-purple/20 rounded flex items-center justify-center text-neon-purple">
              <IconMoodHappy size={24} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Storyteller Status */}
      <Card>
        <CardContent>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-2">
                STORYTELLER
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Observes and creates stories
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.storyteller.status === 'active' ? 'text-neon-green' : 'text-text-muted'}>
                  {agents.storyteller.status.toUpperCase()}
                </span>
                <span className="text-text-tertiary">
                  {agents.storyteller.observations_count} observations
                </span>
                <span className="text-text-tertiary">
                  {agents.storyteller.stories_created} stories created
                </span>
              </div>
            </div>
            <div className="w-10 h-10 bg-neon-cyan/20 rounded flex items-center justify-center text-neon-cyan">
              <IconEye size={24} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Critic Status */}
      <Card>
        <CardContent>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider mb-2">
                CRITIC
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Evaluates quality
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.critic?.status === 'active' ? 'text-neon-green' : 'text-text-muted'}>
                  {(agents.critic?.status || 'idle').toUpperCase()}
                </span>
                <span className="text-text-tertiary">
                  {agents.critic?.evaluations_count || 0} evaluations
                </span>
                {agents.critic?.average_score && (
                  <span className="text-text-tertiary">
                    avg: {agents.critic.average_score}/10
                  </span>
                )}
              </div>
            </div>
            <div className="w-10 h-10 bg-neon-cyan/20 rounded flex items-center justify-center text-neon-cyan">
              <IconCardStack size={24} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dweller Agents */}
      <div>
        <h3 className="text-text-primary font-mono text-sm uppercase tracking-wider mb-4">
          CHARACTERS ({agents.dweller_agents.length})
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {agents.dweller_agents.map((agent) => {
            const dweller = dwellerMap.get(agent.dweller_id)
            return (
              <Card key={agent.dweller_id} className="border-white/5">
                <CardContent className="py-3">
                  <div className="flex items-center gap-3">
                    {dweller?.persona.avatar_url ? (
                      <img
                        src={dweller.persona.avatar_url}
                        alt={dweller.persona.name}
                        className="w-8 h-8 rounded object-cover shrink-0"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center text-xs font-mono text-text-secondary shrink-0">
                        {dweller?.persona.name?.charAt(0) || '?'}
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <div className="text-text-primary text-sm truncate">
                        {dweller?.persona.name || 'Unknown'}
                      </div>
                      <div className="flex items-center gap-2 text-xs font-mono">
                        <span
                          className={
                            agent.activity === 'conversing'
                              ? 'text-neon-green'
                              : agent.activity === 'seeking'
                              ? 'text-neon-cyan'
                              : 'text-text-tertiary'
                          }
                        >
                          {agent.activity}
                        </span>
                        {agent.conversation_id && (
                          <span className="text-text-tertiary">
                            in conversation
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
