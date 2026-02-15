'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'
import {
  IconChat,
  IconHumanRun,
  IconEye,
  IconUser,
  IconMoodNeutral,
  IconLightbulb,
  IconMoonStar,
  IconCircle,
} from '@/components/ui/PixelIcon'

interface Activity {
  id: string
  dweller: {
    id: string
    name: string
  }
  action_type: string
  target: string | null
  content: string
  dialogue?: string | null
  stage_direction?: string | null
  created_at: string
  in_reply_to_action_id?: string | null
}

interface ActivityFeedProps {
  worldId: string
  activity: Activity[]
}

const ACTION_ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  speak: IconChat,
  move: IconHumanRun,
  observe: IconEye,
  interact: IconUser,
  decide: IconMoodNeutral,
  work: IconLightbulb,
  create: IconMoonStar,
  default: IconCircle,
}

function ActionIcon({ type }: { type: string }) {
  const Icon = ACTION_ICONS[type] || ACTION_ICONS.default
  return <Icon size={20} />
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString()
}

function formatTimeRange(earliest: string, latest: string): string {
  const earliestTime = formatRelativeTime(earliest)
  const latestTime = formatRelativeTime(latest)
  if (earliestTime === latestTime) return earliestTime
  return `${latestTime} - ${earliestTime}`
}

// Render SPEAK action content in play script format
function renderSpeakContent(action: Activity): JSX.Element {
  // New structured format
  if (action.dialogue || action.stage_direction) {
    return (
      <div className="space-y-1">
        {action.stage_direction && (
          <p className="text-text-tertiary text-xs italic">*{action.stage_direction}*</p>
        )}
        {action.dialogue && (
          <p className="text-text-primary text-xs">"{action.dialogue}"</p>
        )}
      </div>
    )
  }

  // Legacy format - just content
  return (
    <p className="text-text-primary text-xs italic">
      <ExpandableText text={action.content} />
    </p>
  )
}

type ActivityGroup = {
  type: 'single' | 'conversation' | 'activity_group'
  dweller: { id: string; name: string }
  actions: Activity[]
  earliest: string
  latest: string
}

function groupActivities(activities: Activity[]): ActivityGroup[] {
  if (activities.length === 0) return []

  // First pass: identify conversation threads (speak actions with in_reply_to chains)
  const actionMap = new Map<string, Activity>()
  for (const a of activities) {
    actionMap.set(a.id, a)
  }

  // Find conversation chains: group speak actions that reference each other
  const conversationGroups: Map<string, Activity[]> = new Map()
  const assignedToConversation = new Set<string>()

  for (const action of activities) {
    if (action.action_type !== 'speak') continue
    if (assignedToConversation.has(action.id)) continue

    // Walk the reply chain backwards to find the root
    let root = action
    const visited = new Set<string>([root.id])
    while (root.in_reply_to_action_id && actionMap.has(root.in_reply_to_action_id)) {
      if (visited.has(root.in_reply_to_action_id)) break
      visited.add(root.in_reply_to_action_id)
      root = actionMap.get(root.in_reply_to_action_id)!
    }

    // If root is already in a conversation, add to it
    if (assignedToConversation.has(root.id)) {
      const existingConvo = Array.from(conversationGroups.entries()).find(([_, acts]) =>
        acts.some((a) => a.id === root.id)
      )
      if (existingConvo && !assignedToConversation.has(action.id)) {
        existingConvo[1].push(action)
        assignedToConversation.add(action.id)
      }
      continue
    }

    // Collect all actions in this thread
    const thread: Activity[] = [root]
    assignedToConversation.add(root.id)

    // Find all replies to this chain
    for (const other of activities) {
      if (other.action_type !== 'speak') continue
      if (assignedToConversation.has(other.id)) continue
      if (other.in_reply_to_action_id && visited.has(other.in_reply_to_action_id)) {
        thread.push(other)
        assignedToConversation.add(other.id)
        visited.add(other.id)
      }
    }

    // Also find speak actions between the same dwellers with targets
    if (root.target) {
      for (const other of activities) {
        if (assignedToConversation.has(other.id)) continue
        if (other.action_type !== 'speak') continue
        // Same pair of dwellers talking
        const sameConvo =
          (other.dweller.name === root.dweller.name && other.target === root.target) ||
          (other.dweller.name === root.target && other.target === root.dweller.name)
        if (sameConvo) {
          thread.push(other)
          assignedToConversation.add(other.id)
          visited.add(other.id)
        }
      }
    }

    if (thread.length > 1) {
      // Sort by time
      thread.sort(
        (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      )
      conversationGroups.set(root.id, thread)
    } else {
      // Single speak, release it
      assignedToConversation.delete(root.id)
    }
  }

  // Second pass: group remaining non-conversation actions by dweller + time window
  const TIME_WINDOW_MS = 30 * 60 * 1000
  const result: ActivityGroup[] = []

  // Build ordered list mixing conversations and activity groups
  const processed = new Set<string>()

  for (const action of activities) {
    if (processed.has(action.id)) continue

    // Check if this action starts a conversation group
    if (conversationGroups.has(action.id)) {
      const thread = conversationGroups.get(action.id)!
      thread.forEach((a) => processed.add(a.id))
      result.push({
        type: 'conversation',
        dweller: thread[0].dweller,
        actions: thread,
        earliest: thread[0].created_at,
        latest: thread[thread.length - 1].created_at,
      })
      continue
    }

    // Check if action is part of a conversation (not the root)
    if (assignedToConversation.has(action.id)) continue

    // Otherwise group by dweller + time window
    const group: Activity[] = [action]
    processed.add(action.id)

    for (let i = activities.indexOf(action) + 1; i < activities.length; i++) {
      const next = activities[i]
      if (processed.has(next.id) || assignedToConversation.has(next.id)) continue
      if (next.dweller.id !== action.dweller.id) continue
      if (conversationGroups.has(next.id)) continue

      const timeDiff = Math.abs(
        new Date(next.created_at).getTime() - new Date(group[group.length - 1].created_at).getTime()
      )
      if (timeDiff > TIME_WINDOW_MS) break

      group.push(next)
      processed.add(next.id)
    }

    result.push({
      type: group.length > 1 ? 'activity_group' : 'single',
      dweller: action.dweller,
      actions: group,
      earliest: group[0].created_at,
      latest: group[group.length - 1].created_at,
    })
  }

  return result
}

function ExpandableText({ text, className }: { text: string; className?: string }) {
  const [expanded, setExpanded] = useState(false)
  const THRESHOLD = 300

  if (text.length <= THRESHOLD) {
    return <span className={className}>{text}</span>
  }

  return (
    <span className={className}>
      {expanded ? text : text.slice(0, THRESHOLD) + '…'}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-neon-cyan/60 hover:text-neon-cyan text-[10px] ml-1 font-mono"
      >
        {expanded ? '[less]' : '[more]'}
      </button>
    </span>
  )
}

function renderConversation(group: ActivityGroup) {
  return (
    <Card
      key={`conv-${group.actions[0].id}`}
      className="border-neon-cyan/10 hover:border-neon-cyan/20 transition-colors"
    >
      <CardContent className="py-3">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <IconChat size={16} />
            <span className="text-neon-cyan text-[10px] font-mono uppercase tracking-wider">
              Conversation
            </span>
          </div>
          <span className="text-text-tertiary text-[10px] font-mono shrink-0">
            {formatTimeRange(group.earliest, group.latest)}
          </span>
        </div>

        <div className="space-y-2">
          {group.actions.map((action) => (
            <div key={action.id} className="flex items-start gap-2">
              <div className="w-5 h-5 rounded-full bg-neon-cyan/20 flex items-center justify-center text-neon-cyan text-[9px] font-mono font-bold shrink-0 mt-0.5">
                {action.dweller.name[0].toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <Link
                  href={`/dweller/${action.dweller.id}`}
                  className="text-neon-cyan hover:underline text-xs font-medium"
                >
                  {action.dweller.name}
                </Link>
                {action.target && (
                  <span className="text-text-tertiary text-[10px] font-mono ml-1">
                    → {action.target}
                  </span>
                )}
                <div className="mt-0.5">
                  {renderSpeakContent(action)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function renderNonSpeakAction(action: Activity) {
  const actionLabel = action.action_type.toUpperCase()

  return (
    <div key={action.id} className="flex items-start gap-2">
      <span className="shrink-0 mt-0.5" title={action.action_type}>
        <ActionIcon type={action.action_type} />
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-text-tertiary text-[10px] font-mono uppercase mr-2">
          {actionLabel}
        </span>
        <p className="text-text-tertiary text-xs">
          <ExpandableText
            text={
              action.target && action.action_type === 'move'
                ? `moved to: ${action.content}`
                : action.target
                  ? `${action.target}: ${action.content}`
                  : action.content
            }
          />
        </p>
      </div>
    </div>
  )
}

function renderSpeakAction(action: Activity) {
  return (
    <div key={action.id} className="flex items-start gap-2">
      <span className="shrink-0 mt-0.5">
        <IconChat size={20} />
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-text-tertiary text-[10px] font-mono uppercase mr-2">SPEAK</span>
        {action.target && (
          <span className="text-text-tertiary text-[10px] font-mono">→ {action.target}</span>
        )}
        <div className="mt-0.5">
          {renderSpeakContent(action)}
        </div>
      </div>
    </div>
  )
}

function renderActionLine(action: Activity) {
  if (action.action_type === 'speak') {
    return renderSpeakAction(action)
  }
  return renderNonSpeakAction(action)
}

function renderActivityGroup(group: ActivityGroup, idx: number) {
  if (group.type === 'conversation') {
    return renderConversation(group)
  }

  return (
    <Card
      key={`${group.dweller.id}-${idx}`}
      className="border-white/5 hover:border-white/10 transition-colors"
    >
      <CardContent className="py-3">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-full bg-neon-cyan/20 flex items-center justify-center text-neon-cyan text-xs font-mono font-bold">
              {group.dweller.name[0].toUpperCase()}
            </div>
            <Link
              href={`/dweller/${group.dweller.id}`}
              className="text-neon-cyan hover:underline text-sm font-medium"
              data-testid={`dweller-${group.dweller.id}`}
            >
              {group.dweller.name}
            </Link>
          </div>
          <span className="text-text-tertiary text-[10px] font-mono shrink-0">
            {formatTimeRange(group.earliest, group.latest)}
          </span>
        </div>

        <div className="space-y-2 pl-8">{group.actions.map(renderActionLine)}</div>
      </CardContent>
    </Card>
  )
}

export function ActivityFeed({ worldId, activity }: ActivityFeedProps) {
  if (!activity || activity.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-sm mb-1">No activity yet</p>
        <p className="text-sm">Dwellers are waiting for agents to inhabit them...</p>
      </div>
    )
  }

  const groups = groupActivities(activity)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-neon-cyan font-mono text-sm uppercase tracking-wider">
          Recent Activity
        </h3>
        <span className="text-text-tertiary text-xs font-mono">
          {activity.length} action{activity.length !== 1 ? 's' : ''}
        </span>
      </div>

      {groups.map((group, idx) => renderActivityGroup(group, idx))}
    </div>
  )
}
