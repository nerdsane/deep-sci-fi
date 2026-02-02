'use client'

import { useState } from 'react'
import type { World } from '@/types'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ActivityFeed } from './ActivityFeed'
import { AspectsList } from './AspectsList'

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

export function WorldDetail({ world, agents }: WorldDetailProps) {
  const [activeTab, setActiveTab] = useState<'live' | 'activity' | 'stories' | 'timeline' | 'dwellers' | 'aspects' | 'agents'>('live')

  const simulationRunning = world.simulation_status === 'running'

  return (
    <div className="space-y-8">
      {/* Hero section */}
      <div className="border-b border-white/5 pb-8">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl text-neon-cyan">{world.name}</h1>
              {simulationRunning && (
                <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-mono rounded flex items-center gap-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  SIMULATING
                </span>
              )}
            </div>
            <div className="text-text-secondary text-lg">{world.premise}</div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="primary">FOLLOW</Button>
            <Button variant="ghost">SHARE</Button>
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-6 text-text-tertiary font-mono text-sm">
          <div>
            <span className="text-text-primary">{world.dwellerCount}</span> DWELLERS
          </div>
          <div>
            <span className="text-text-primary">{world.storyCount}</span> STORIES
          </div>
          <div>
            <span className="text-text-primary">{world.followerCount}</span> FOLLOWERS
          </div>
          <div>
            <span className="text-neon-cyan">{world.yearSetting}</span> YEAR
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-white/5 overflow-x-auto">
        {(['live', 'activity', 'stories', 'timeline', 'dwellers', 'aspects', 'agents'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`
              px-4 py-3 font-mono text-sm uppercase tracking-wider
              border-b-2 transition-colors shrink-0
              ${
                activeTab === tab
                  ? 'text-neon-cyan border-neon-cyan'
                  : 'text-text-secondary border-transparent hover:text-text-primary'
              }
            `}
          >
            {tab === 'live' && '\u{1F534} '}{tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div data-testid="activity-feed">
        {activeTab === 'live' && <LiveConversations conversations={world.conversations} dwellers={world.dwellers} />}
        {activeTab === 'activity' && <ActivityFeed worldId={world.id} activity={world.activity || []} />}
        {activeTab === 'stories' && <StoriesView stories={world.stories} />}
        {activeTab === 'timeline' && <TimelineView causalChain={world.causalChain} events={world.recent_events} />}
        {activeTab === 'dwellers' && <DwellersView dwellers={world.dwellers} />}
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
            Recent World Events
          </h3>
          <div className="space-y-3">
            {events.map((event) => (
              <Card key={event.id} className="border-neon-purple/30">
                <CardContent>
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <span className="text-xs font-mono text-neon-purple uppercase">
                        {event.event_type}
                      </span>
                      <h4 className="text-text-primary font-medium mt-1">{event.title}</h4>
                      <p className="text-text-secondary text-sm mt-1">{event.description}</p>
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
            Historical Timeline
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
                      <div className="text-text-primary mb-2">{event.event}</div>
                      <div className="text-text-secondary text-sm flex items-start gap-2">
                        <span className="text-neon-purple shrink-0">→</span>
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
          <p className="text-lg mb-2">No timeline events yet</p>
          <p className="text-sm">Start the simulation to see events unfold...</p>
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
        <p className="text-lg mb-2">No active conversations</p>
        <p className="text-sm">Dwellers are currently idle...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {displayConvs.map((conv) => (
        <Card key={conv.id}>
          <CardContent>
            <div className="flex items-center gap-2 mb-4 text-xs font-mono text-text-tertiary">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              {conv.is_active ? 'LIVE CONVERSATION' : 'RECENT CONVERSATION'}
            </div>
            <div className="space-y-4">
              {conv.messages?.slice(-5).map((msg) => {
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
        <p className="text-lg mb-2">No stories yet</p>
        <p className="text-sm">Storyteller is observing this world...</p>
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
          ← BACK TO STORIES
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

          <h1 className="text-2xl text-neon-cyan mb-4">{expanded.title}</h1>

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
              <p className="text-neon-cyan text-sm font-mono mb-4">STORYTELLER SCRIPT</p>
              <div className="text-text-secondary leading-relaxed whitespace-pre-wrap font-mono text-sm">
                {expanded.transcript}
              </div>
            </div>
          ) : (
            <div className="mt-8 p-4 border border-white/10 bg-bg-tertiary">
              <p className="text-text-tertiary text-sm font-mono mb-2">STORYTELLER SCRIPT</p>
              <p className="text-text-secondary text-sm italic">
                No script recorded for this story.
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
            <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity bg-black/30">
              <span className="text-white text-4xl">▶</span>
            </div>
          </div>
          <CardContent>
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg text-text-primary flex-1">{story.title}</h3>
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
        <p className="text-lg mb-2">No dwellers yet</p>
        <p className="text-sm">This world is waiting for inhabitants...</p>
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
                    <span className="w-2 h-2 bg-green-500 rounded-full" title="Active" />
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
        <p className="text-lg mb-2">Agent status unavailable</p>
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
              agents.simulation_status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
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
                Puppeteer (World God)
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Introduces world events and environmental changes
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.puppeteer.status === 'active' ? 'text-green-400' : 'text-gray-500'}>
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
            <div className="w-10 h-10 bg-neon-purple/20 rounded flex items-center justify-center">
              <span className="text-neon-purple text-xl">🎭</span>
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
                Observer (Storyteller)
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Observes dwellers and creates video stories
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.storyteller.status === 'active' ? 'text-green-400' : 'text-gray-500'}>
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
            <div className="w-10 h-10 bg-neon-cyan/20 rounded flex items-center justify-center">
              <span className="text-neon-cyan text-xl">👁️</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Critic Status */}
      <Card>
        <CardContent>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-yellow-400 font-mono text-sm uppercase tracking-wider mb-2">
                Critic
              </h3>
              <p className="text-text-secondary text-sm mb-3">
                Evaluates stories and conversations for quality
              </p>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className={agents.critic?.status === 'active' ? 'text-green-400' : 'text-gray-500'}>
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
            <div className="w-10 h-10 bg-yellow-500/20 rounded flex items-center justify-center">
              <span className="text-yellow-400 text-xl">✂️</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dweller Agents */}
      <div>
        <h3 className="text-text-primary font-mono text-sm uppercase tracking-wider mb-4">
          Dweller Agents ({agents.dweller_agents.length})
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
                              ? 'text-green-400'
                              : agent.activity === 'seeking'
                              ? 'text-yellow-400'
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
