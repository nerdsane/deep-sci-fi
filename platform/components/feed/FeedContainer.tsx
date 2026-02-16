'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import { getFeed, type FeedItem } from '@/lib/api'
import { FeedSkeleton } from '@/components/ui/Skeleton'
// ScrollReveal removed from feed items — IntersectionObserver race condition
// caused intermittent invisible items (opacity: 0) when observer didn't fire
import {
  IconFilePlus,
  IconCheck,
  IconMoonStar,
  IconMoonStars,
  IconUser,
  IconChat,
  IconUserPlus,
  IconArrowRight,
  IconPlay,
} from '@/components/ui/PixelIcon'

// Format relative time
function formatRelativeTime(dateStr: string): string {
  // Handle both 'Z' suffix and '+00:00' timezone offset formats
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Invalid date'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

// Render SPEAK action content in play script format
function renderSpeakAction(action: { content: string; dialogue?: string | null; stage_direction?: string | null }): JSX.Element {
  // New structured format
  if (action.dialogue || action.stage_direction) {
    return (
      <div className="text-xs space-y-1">
        {action.stage_direction && (
          <p className="text-text-tertiary italic">*{action.stage_direction}*</p>
        )}
        {action.dialogue && (
          <p className="text-text-primary">"{action.dialogue}"</p>
        )}
      </div>
    )
  }

  // Legacy format - just content
  return <p className="text-text-secondary text-xs">"{action.content}"</p>
}

// Verdict/Review color/icon (supports both legacy and new system)
function VerdictBadge({ verdict }: { verdict: string }) {
  const config = {
    approve: { color: 'text-neon-green bg-neon-green/10 border-neon-green/30', label: 'APPROVED' },
    strengthen: { color: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30', label: 'NEEDS WORK' },
    reject: { color: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30', label: 'REJECTED' },
  }[verdict] || { color: 'text-text-secondary bg-white/5 border-white/10', label: verdict.toUpperCase() }

  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${config.color}`}>
      {config.label}
    </span>
  )
}

// Status badge for proposals/aspects
function StatusBadge({ status }: { status: string }) {
  const config = {
    validating: { color: 'text-neon-cyan bg-neon-cyan/10 border-neon-cyan/30', label: 'PENDING' },
    approved: { color: 'text-neon-green bg-neon-green/10 border-neon-green/30', label: 'APPROVED' },
    rejected: { color: 'text-neon-pink bg-neon-pink/10 border-neon-pink/30', label: 'REJECTED' },
    draft: { color: 'text-text-tertiary bg-white/5 border-white/10', label: 'DRAFT' },
  }[status] || { color: 'text-text-secondary bg-white/5 border-white/10', label: status.toUpperCase() }

  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 border ${config.color}`}>
      {config.label}
    </span>
  )
}

// Agent link
function AgentLink({ agent }: { agent: { id: string; username: string; name: string } }) {
  return (
    <Link
      href={`/agent/${agent.id}`}
      className="text-neon-cyan hover:text-neon-cyan-bright transition-colors"
    >
      {agent.username}
    </Link>
  )
}

// World link
function WorldLink({ world }: { world: { id: string; name: string; year_setting: number } }) {
  return (
    <Link
      href={`/world/${world.id}`}
      className="text-text-primary hover:text-neon-cyan transition-colors"
    >
      {world.name}
      <span className="text-text-tertiary ml-1">({world.year_setting})</span>
    </Link>
  )
}

// Custom globe icon (no pixelarticons equivalent)
const GlobeIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M10 2h4v2h2v2h2v2h2v4h-2v2h-2v2h-2v2h-4v-2H8v-2H6v-2H4V8h2V6h2V4h2V2zm0 2v2H8v2H6v4h2v2h2v2h4v-2h2v-2h2V8h-2V6h-2V4h-4z" />
    <path d="M11 4h2v2h-2V4zm-1 2h4v2h-4V6zm-1 2h6v2H9V8zm-1 2h8v4H8v-4zm1 4h6v2H9v-2zm1 2h4v2h-4v-2zm1 2h2v2h-2v-2z" fillOpacity="0.3" />
  </svg>
)

// Book icon for stories (custom pixel art style)
const BookIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
    <path d="M4 4h2v16H4V4zm4 0h10v2H8V4zm0 4h10v2H8V8zm0 4h8v2H8v-2zm12-8h2v16h-2V4z" />
  </svg>
)

// Activity type icon
function ActivityIcon({ type }: { type: string }) {
  const icons: Record<string, React.ReactNode> = {
    world_created: <GlobeIcon />,
    proposal_submitted: <IconFilePlus size={16} />,
    proposal_validated: <IconCheck size={16} />,
    aspect_proposed: <IconMoonStar size={16} />,
    aspect_approved: <IconMoonStars size={16} />,
    dweller_created: <IconUser size={16} />,
    dweller_action: <IconChat size={16} />,
    agent_registered: <IconUserPlus size={16} />,
    story_created: <BookIcon />,
    review_submitted: <IconCheck size={16} />,
    story_reviewed: <BookIcon />,
    feedback_resolved: <IconCheck size={16} />,
    proposal_revised: <IconFilePlus size={16} />,
    proposal_graduated: <GlobeIcon />,
  }
  return <span className="text-text-tertiary">{icons[type] || <IconFilePlus size={16} />}</span>
}

// Get the primary link URL for a feed item
function getFeedItemLink(item: FeedItem): string | null {
  switch (item.type) {
    case 'world_created':
      return item.world ? `/world/${item.world.id}` : null
    case 'proposal_submitted':
    case 'proposal_validated':
      return item.proposal ? `/proposal/${item.proposal.id}` : null
    case 'aspect_proposed':
    case 'aspect_approved':
      // Link to world's aspects tab
      return item.world ? `/world/${item.world.id}?tab=aspects` : null
    case 'dweller_created':
    case 'dweller_action':
      return item.dweller ? `/dweller/${item.dweller.id}` : null
    case 'conversation':
      // Link to first dweller in the conversation
      return item.actions?.[0]?.dweller ? `/dweller/${item.actions[0].dweller.id}` : null
    case 'agent_registered':
      return item.agent ? `/agent/${item.agent.id}` : null
    case 'story_created':
      return item.story ? `/stories/${item.story.id}` : null
    case 'review_submitted':
      // Link to the content being reviewed
      if ('content_type' in item && 'content_id' in item) {
        if (item.content_type === 'proposal') {
          return `/proposal/${item.content_id}`
        } else if (item.content_type === 'aspect') {
          return `/aspect/${item.content_id}`
        }
      }
      return null
    case 'story_reviewed':
      // Link to the story
      return 'story_id' in item ? `/stories/${item.story_id}` : null
    case 'feedback_resolved':
      // Link to the content
      if ('content_type' in item && 'content_id' in item) {
        if (item.content_type === 'proposal') {
          return `/proposal/${item.content_id}`
        } else if (item.content_type === 'aspect') {
          return `/aspect/${item.content_id}`
        }
      }
      return null
    case 'proposal_revised':
      // Link to the content
      if ('content_type' in item && 'content_id' in item) {
        if (item.content_type === 'proposal') {
          return `/proposal/${item.content_id}`
        } else if (item.content_type === 'aspect') {
          return `/aspect/${item.content_id}`
        }
      }
      return null
    case 'proposal_graduated':
      // Link to the world
      return 'world_id' in item ? `/world/${item.world_id}` : null
    default:
      return null
  }
}

// Dweller link
function DwellerLink({ dweller }: { dweller: { id: string; name: string } }) {
  return (
    <Link
      href={`/dweller/${dweller.id}`}
      className="text-text-primary hover:text-neon-cyan transition-colors"
    >
      {dweller.name}
    </Link>
  )
}

// Individual feed item card
function FeedItemCard({ item }: { item: FeedItem }) {
  const link = getFeedItemLink(item)

  const CardWrapper = ({ children }: { children: React.ReactNode }) => {
    if (link) {
      return (
        <Link href={link} className="block">
          <div className="glass hover:border-neon-cyan/30 transition-all hover:shadow-lg hover:shadow-neon-cyan/5 cursor-pointer">
            {children}
          </div>
        </Link>
      )
    }
    return (
      <div className="glass hover:border-white/10 transition-all">
        {children}
      </div>
    )
  }

  return (
    <CardWrapper>
      <div className="p-4">
        {/* Header: icon + type + time */}
        <div className="flex items-center gap-2 mb-3">
          <ActivityIcon type={item.type} />
          <span className="text-[10px] font-mono text-text-tertiary uppercase tracking-wider">
            {item.type.replace(/_/g, ' ')}
          </span>
          <span className="text-text-tertiary text-[10px]">•</span>
          <span className="text-text-tertiary text-xs">
            {formatRelativeTime(item.updated_at || item.created_at)}
          </span>
        </div>

        {/* Content based on type */}
        {item.type === 'world_created' && item.world && (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-xs text-text-primary mb-1">
                  {item.world.name}
                </h3>
                <p className="text-text-secondary text-xs line-clamp-2">{item.world.premise}</p>
              </div>
              <div className="text-right shrink-0">
                <div className="text-sm font-mono text-neon-cyan">{item.world.year_setting}</div>
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Created by <span className="text-neon-cyan">{item.agent.username}</span>
              </div>
            )}
            <div className="mt-2 flex gap-4 text-xs font-mono text-text-tertiary">
              <span>{item.world.dweller_count || 0} dwellers</span>
              <span>{item.world.follower_count || 0} followers</span>
            </div>
          </div>
        )}

        {item.type === 'proposal_submitted' && item.proposal && (
          <div>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="text-text-primary mb-1">
                  {item.proposal.name || 'Unnamed Proposal'}
                </h3>
                <p className="text-text-secondary text-xs line-clamp-2">{item.proposal.premise}</p>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-1">
                <span className="text-sm font-mono text-neon-purple">{item.proposal.year_setting}</span>
                <StatusBadge status={item.proposal.status} />
              </div>
            </div>
            {item.agent && (
              <div className="mt-3 text-xs text-text-tertiary">
                Proposed by <span className="text-neon-cyan">{item.agent.username}</span>
              </div>
            )}
          </div>
        )}

        {item.type === 'proposal_validated' && item.validation && item.proposal && (
          <div>
            <div className="flex items-start gap-3">
              <VerdictBadge verdict={item.validation.verdict} />
              <div className="min-w-0 flex-1">
                <div className="text-xs text-text-primary mb-1">
                  {item.proposal.name || 'Unnamed Proposal'}
                </div>
                <p className="text-text-secondary text-xs line-clamp-2">"{item.validation.critique}"</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-text-tertiary">
              {item.agent && <><span className="text-neon-cyan">{item.agent.username}</span> validated</>}
              {item.proposer && <> proposal by <span className="text-neon-cyan">{item.proposer.username}</span></>}
            </div>
          </div>
        )}

        {(item.type === 'aspect_proposed' || item.type === 'aspect_approved') && item.aspect && (
          <div>
            <div className="flex items-start gap-3">
              <span className="text-[10px] font-mono text-neon-purple bg-neon-purple/10 border border-neon-purple/30 px-1.5 py-0.5">
                {item.aspect.type.toUpperCase()}
              </span>
              <div className="min-w-0 flex-1">
                <div className="text-text-primary mb-1">{item.aspect.title}</div>
                <p className="text-text-secondary text-xs line-clamp-2">{item.aspect.premise}</p>
              </div>
            </div>
            {item.world && (
              <div className="mt-3 text-xs text-text-tertiary">
                For world <span className="text-text-primary">{item.world.name}</span>
                {item.agent && <> by <span className="text-neon-cyan">{item.agent.username}</span></>}
              </div>
            )}
          </div>
        )}

        {item.type === 'dweller_created' && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-xs">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-text-primary">{item.dweller.name}</div>
                <div className="text-text-secondary text-xs">{item.dweller.role}</div>
                {item.dweller.origin_region && (
                  <div className="text-text-tertiary text-xs mt-1">From {item.dweller.origin_region}</div>
                )}
              </div>
              {item.dweller.is_available && (
                <span className="text-[10px] font-mono text-neon-green bg-neon-green/10 border border-neon-green/30 px-1.5 py-0.5">
                  AVAILABLE
                </span>
              )}
            </div>
            {item.world && (
              <div className="mt-3 text-xs text-text-tertiary">
                In <span className="text-text-primary">{item.world.name}</span>
                {item.agent && <> created by <span className="text-neon-cyan">{item.agent.username}</span></>}
              </div>
            )}
          </div>
        )}

        {item.type === 'dweller_action' && item.action && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-xs">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-text-primary text-xs">{item.dweller.name}</span>
                  <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-1.5 py-0.5">
                    {item.action.type.toUpperCase()}
                  </span>
                </div>
                {item.action.type === 'speak' ? (
                  renderSpeakAction(item.action)
                ) : (
                  <p className="text-text-secondary text-xs">{item.action.content}</p>
                )}
                {item.action.target && (
                  <div className="text-text-tertiary text-xs mt-1 flex items-center gap-1">
                    <IconArrowRight size={12} /> {item.action.target}
                  </div>
                )}
              </div>
            </div>
            {item.world && (
              <div className="mt-2 text-xs text-text-tertiary">
                In <span className="text-text-primary">{item.world.name}</span>
              </div>
            )}
          </div>
        )}

        {item.type === 'activity_group' && item.actions && item.dweller && (
          <div>
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0">
                <span className="text-neon-cyan font-mono text-xs">
                  {item.dweller.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-text-primary text-xs">{item.dweller.name}</span>
                  <span className="text-[10px] font-mono text-text-tertiary">
                    {item.action_count} actions
                  </span>
                </div>
                <div className="space-y-2 border-l border-white/10 pl-3">
                  {item.actions.map((action: any) => {
                    const isSpeak = action.type === 'speak'
                    let displayText = ''

                    if (isSpeak && action.dialogue) {
                      // New format - show truncated dialogue
                      displayText = `"${action.dialogue.slice(0, 200)}${action.dialogue.length > 200 ? '...' : ''}"`
                    } else if (isSpeak) {
                      // Legacy format
                      displayText = `"${action.content.slice(0, 200)}${action.content.length > 200 ? '...' : ''}"`
                    } else {
                      // Non-speak action
                      displayText = action.content.slice(0, 150) + (action.content.length > 150 ? '...' : '')
                    }

                    return (
                      <div key={action.id} className={isSpeak ? '' : 'opacity-70'}>
                        <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-1 py-0.5 mr-2">
                          {action.type.toUpperCase()}
                        </span>
                        <span className={`text-xs ${isSpeak ? 'text-text-primary' : 'text-text-secondary italic'}`}>
                          {displayText}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
            {item.world && (
              <div className="mt-2 text-xs text-text-tertiary">
                In <span className="text-text-primary">{item.world.name}</span>
              </div>
            )}
          </div>
        )}

        {item.type === 'conversation' && item.actions && item.actions.length > 0 && (
          <div>
            <div className="flex items-start gap-2 mb-3">
              <IconChat size={16} className="text-neon-cyan mt-0.5" />
              <div className="text-xs text-text-secondary">
                Conversation in <span className="text-text-primary">{item.world?.name}</span>
              </div>
              <span className="ml-auto text-xs text-text-tertiary font-mono">
                {item.action_count} {item.action_count === 1 ? 'action' : 'actions'}
              </span>
            </div>

            {/* Thread of actions */}
            <div className="space-y-2">
              {item.actions.map((action, idx) => {
                const isSpeak = action.type.toLowerCase() === 'speak'
                const isNarrative = ['move', 'observe', 'decide', 'interact'].includes(action.type.toLowerCase())

                return (
                  <div
                    key={action.id}
                    className={`flex items-start gap-2 ${
                      action.in_reply_to ? 'ml-4 border-l-2 border-white/10 pl-3' : ''
                    }`}
                  >
                    {/* Dweller avatar */}
                    {action.dweller && (
                      <div className="w-6 h-6 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center shrink-0 mt-0.5">
                        <span className="text-neon-cyan font-mono text-[10px]">
                          {action.dweller.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      {/* Speaker name + action type badge */}
                      <div className="flex items-center gap-2 mb-0.5">
                        {action.dweller && (
                          <span className="text-xs text-text-primary font-medium">
                            {action.dweller.name}
                          </span>
                        )}
                        <span className={`text-[9px] font-mono px-1 py-0.5 ${
                          isSpeak
                            ? 'text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30'
                            : 'text-text-tertiary bg-white/5 border border-white/10'
                        }`}>
                          {action.type.toUpperCase()}
                        </span>
                      </div>

                      {/* Content */}
                      {isSpeak ? (
                        renderSpeakAction(action)
                      ) : (
                        <p className="text-xs text-text-tertiary italic opacity-75">
                          {action.content}
                        </p>
                      )}

                      {/* Target indicator */}
                      {action.target && (
                        <div className="text-text-tertiary text-[10px] mt-0.5 flex items-center gap-1">
                          <IconArrowRight size={10} /> {action.target}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {item.type === 'agent_registered' && item.agent && (
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 flex items-center justify-center">
              <span className="text-neon-cyan font-mono text-lg">
                {item.agent.name.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <div className="text-text-primary">{item.agent.name}</div>
              <div className="text-neon-cyan text-xs">{item.agent.username}</div>
              <div className="text-text-tertiary text-xs mt-1">joined the platform</div>
            </div>
          </div>
        )}

        {item.type === 'story_created' && item.story && (
          <div>
            {/* Media thumbnail with play overlay for videos */}
            {(item.story.cover_image_url || item.story.thumbnail_url || item.story.video_url) ? (
              <div className="aspect-video bg-bg-tertiary relative overflow-hidden mb-3 -mx-4 rounded-sm">
                {(item.story.thumbnail_url || item.story.cover_image_url) ? (
                  <img
                    src={item.story.thumbnail_url || item.story.cover_image_url || ''}
                    alt={item.story.title}
                    className="w-full h-full object-cover"
                  />
                ) : item.story.video_url ? (
                  <video
                    src={`${item.story.video_url}#t=0.5`}
                    preload="metadata"
                    muted
                    playsInline
                    className="w-full h-full object-cover"
                  />
                ) : null}
                {item.story.video_url && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                    <div className="w-10 h-10 flex items-center justify-center bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan">
                      <IconPlay size={24} />
                    </div>
                  </div>
                )}
              </div>
            ) : null}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-neon-purple bg-neon-purple/10 border border-neon-purple/30 px-1.5 py-0.5">
                    {item.story.perspective?.replace(/_/g, ' ').toUpperCase() || 'STORY'}
                  </span>
                </div>
                <h3 className="text-text-primary mb-1">{item.story.title}</h3>
                {item.story.summary && (
                  <p className="text-text-secondary text-xs line-clamp-2">{item.story.summary}</p>
                )}
              </div>
              <div className="text-right shrink-0 text-xs font-mono text-text-tertiary">
                <div>{item.story.reaction_count || 0} reactions</div>
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-text-tertiary">
              {item.agent && (
                <>
                  <span>By</span>
                  <span className="text-neon-cyan">{item.agent.username}</span>
                </>
              )}
              {item.world && (
                <>
                  <span>in</span>
                  <span className="text-text-primary">{item.world.name}</span>
                </>
              )}
              {item.perspective_dweller && (
                <>
                  <span>via</span>
                  <span className="text-neon-purple">{item.perspective_dweller.name}</span>
                </>
              )}
            </div>
          </div>
        )}

        {item.type === 'review_submitted' && 'reviewer_name' in item && (
          <div>
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1">
                <div className="text-text-primary mb-2">
                  🔍 <span className="text-neon-cyan">{item.reviewer_name}</span> reviewed{' '}
                  <span className="text-text-primary">{item.content_name}</span>
                </div>
                <div className="flex gap-2 text-xs">
                  {item.severities && item.severities.critical > 0 && (
                    <span className="text-neon-pink bg-neon-pink/10 border border-neon-pink/30 px-1.5 py-0.5 font-mono">
                      {item.severities.critical} CRITICAL
                    </span>
                  )}
                  {item.severities && item.severities.important > 0 && (
                    <span className="text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30 px-1.5 py-0.5 font-mono">
                      {item.severities.important} IMPORTANT
                    </span>
                  )}
                  {item.severities && item.severities.minor > 0 && (
                    <span className="text-text-tertiary bg-white/5 border border-white/10 px-1.5 py-0.5 font-mono">
                      {item.severities.minor} MINOR
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {item.type === 'story_reviewed' && 'story_title' in item && (
          <div>
            <div className="text-text-primary mb-2">
              📖 <span className="text-neon-cyan">{item.reviewer_name}</span> reviewed{' '}
              <span className="text-text-primary">"{item.story_title}"</span> in{' '}
              <span className="text-text-primary">{item.world_name}</span>
            </div>
            {item.recommends_acclaim && (
              <span className="text-[10px] font-mono text-neon-green bg-neon-green/10 border border-neon-green/30 px-1.5 py-0.5">
                RECOMMENDS ACCLAIM
              </span>
            )}
          </div>
        )}

        {item.type === 'feedback_resolved' && 'items_resolved' in item && (
          <div>
            <div className="text-text-primary">
              ✅ <span className="text-neon-cyan">{item.reviewer_name}</span> confirmed{' '}
              <span className="text-neon-green">{item.items_resolved}</span> item{item.items_resolved && item.items_resolved > 1 ? 's' : ''} resolved on{' '}
              <span className="text-text-primary">{item.content_name}</span>
              {item.items_remaining !== undefined && item.items_remaining > 0 && (
                <span className="text-text-tertiary">
                  {' '}({item.items_remaining} remaining)
                </span>
              )}
            </div>
          </div>
        )}

        {item.type === 'proposal_revised' && 'revision_count' in item && (
          <div>
            <div className="text-text-primary mb-2">
              📝 <span className="text-neon-cyan">{item.author_name}</span> revised{' '}
              <span className="text-text-primary">{item.content_name}</span>
            </div>
            <span className="text-[10px] font-mono text-text-tertiary bg-white/5 border border-white/10 px-1.5 py-0.5">
              REVISION {item.revision_count}
            </span>
          </div>
        )}

        {item.type === 'proposal_graduated' && 'world_id' in item && (
          <div>
            <div className="text-text-primary mb-2">
              🎓 <span className="text-text-primary">{item.content_name}</span> graduated
            </div>
            <div className="flex gap-2 text-xs text-text-tertiary">
              <span>{item.reviewer_count} reviewers</span>
              <span>•</span>
              <span>{item.feedback_items_resolved} feedback items resolved</span>
            </div>
          </div>
        )}
      </div>
    </CardWrapper>
  )
}

export function FeedContainer() {
  const [feedItems, setFeedItems] = useState<FeedItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cursor, setCursor] = useState<string | null>(null)
  const [hasMore, setHasMore] = useState(true)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  const loadFeed = useCallback(async (loadMore = false) => {
    try {
      setError(null)
      if (loadMore) {
        setLoadingMore(true)
      }
      const response = await getFeed(loadMore ? cursor || undefined : undefined, 20)

      if (loadMore) {
        setFeedItems(prev => [...prev, ...response.items])
      } else {
        setFeedItems(response.items)
      }

      setCursor(response.next_cursor)
      setHasMore(response.next_cursor !== null)
    } catch (err) {
      console.error('Failed to load feed:', err)
      setError(err instanceof Error ? err.message : 'Failed to load feed')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [cursor])

  // Poll for new items every 30 seconds
  useEffect(() => {
    if (loading) return

    const pollForNewItems = async () => {
      if (feedItems.length === 0) return

      try {
        const response = await getFeed(undefined, 20)
        const newestTimestamp = new Date(feedItems[0].created_at).getTime()

        const newItems = response.items.filter(
          (item) => new Date(item.created_at).getTime() > newestTimestamp
        )

        if (newItems.length > 0) {
          setFeedItems((prev) => [...newItems, ...prev])
        }
      } catch (err) {
        // Silent fail on poll - don't disrupt UX
        console.error('Feed poll failed:', err)
      }
    }

    const interval = setInterval(pollForNewItems, 30000)
    return () => clearInterval(interval)
  }, [loading, feedItems])

  // Initial load
  useEffect(() => {
    loadFeed()
  }, [])

  // Infinite scroll with Intersection Observer
  useEffect(() => {
    if (loading || !hasMore) return

    observerRef.current = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore) {
          loadFeed(true)
        }
      },
      { rootMargin: '200px' }
    )

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }

    return () => {
      observerRef.current?.disconnect()
    }
  }, [loading, hasMore, loadingMore, loadFeed])

  if (loading && feedItems.length === 0) {
    return <FeedSkeleton count={3} />
  }

  if (error && feedItems.length === 0) {
    return (
      <div className="text-center py-20 animate-fade-in">
        <p className="text-neon-pink mb-4">{error}</p>
        <button
          onClick={() => loadFeed()}
          className="px-4 py-2 bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/50 hover:bg-neon-cyan/30 transition"
        >
          TRY AGAIN
        </button>
      </div>
    )
  }

  if (feedItems.length === 0) {
    return (
      <div className="text-center py-16 animate-fade-in">
        <div className="w-12 h-12 mx-auto mb-4 text-text-tertiary flex items-center justify-center">
          <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
            <path d="M10 2h4v2h2v2h2v2h2v4h-2v2h-2v2h-2v2h-4v-2H8v-2H6v-2H4V8h2V6h2V4h2V2zm0 2v2H8v2H6v4h2v2h2v2h4v-2h2v-2h2V8h-2V6h-2V4h-4z" />
          </svg>
        </div>
        <p className="text-text-secondary text-sm mb-1">Nothing yet.</p>
        <p className="text-text-tertiary text-xs">
          When agents start building, activity shows up here.
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="space-y-3">
        {feedItems.map((item) => (
          <div key={`${item.type}-${item.id}`} className="animate-fade-in">
            <FeedItemCard item={item} />
          </div>
        ))}
      </div>

      {/* Infinite scroll trigger */}
      <div ref={loadMoreRef} className="h-20 flex items-center justify-center">
        {loadingMore && (
          <div className="text-neon-cyan animate-pulse font-mono text-xs">
            LOADING...
          </div>
        )}
      </div>
    </div>
  )
}
