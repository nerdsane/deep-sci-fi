'use client'

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
  created_at: string
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

function formatActionDescription(action: Activity): string {
  const actionVerb = action.action_type === 'speak' ? 'said'
    : action.action_type === 'move' ? 'moved to'
    : action.action_type === 'observe' ? 'observed'
    : action.action_type === 'interact' ? 'interacted with'
    : action.action_type === 'decide' ? 'decided'
    : action.action_type === 'work' ? 'worked on'
    : action.action_type === 'create' ? 'created'
    : 'did'

  if (action.action_type === 'speak') {
    return `"${action.content.slice(0, 150)}${action.content.length > 150 ? '...' : ''}"`
  }

  if (action.target && action.action_type === 'move') {
    return `${actionVerb} ${action.target}`
  }

  if (action.target) {
    return `${actionVerb} ${action.target}: ${action.content.slice(0, 100)}${action.content.length > 100 ? '...' : ''}`
  }

  return `${actionVerb}: ${action.content.slice(0, 150)}${action.content.length > 150 ? '...' : ''}`
}

type ActivityGroup = {
  dweller: { id: string; name: string }
  actions: Activity[]
  earliest: string
  latest: string
}

function groupActivities(activities: Activity[]): ActivityGroup[] {
  if (activities.length === 0) return []

  const groups: ActivityGroup[] = []
  const TIME_WINDOW_MS = 30 * 60 * 1000 // 30 minutes

  for (const action of activities) {
    const lastGroup = groups[groups.length - 1]

    // Check if this action belongs to the last group
    if (lastGroup && lastGroup.dweller.id === action.dweller.id) {
      const lastActionTime = new Date(lastGroup.latest).getTime()
      const currentActionTime = new Date(action.created_at).getTime()
      const timeDiff = Math.abs(lastActionTime - currentActionTime)

      if (timeDiff <= TIME_WINDOW_MS) {
        // Add to existing group
        lastGroup.actions.push(action)
        lastGroup.latest = action.created_at
        if (new Date(action.created_at) < new Date(lastGroup.earliest)) {
          lastGroup.earliest = action.created_at
        }
        continue
      }
    }

    // Create new group
    groups.push({
      dweller: action.dweller,
      actions: [action],
      earliest: action.created_at,
      latest: action.created_at,
    })
  }

  return groups
}

function renderActionLine(action: Activity) {
  const actionVerb =
    action.action_type === 'speak'
      ? 'said'
      : action.action_type === 'move'
        ? 'moved to'
        : action.action_type === 'observe'
          ? 'observed'
          : action.action_type === 'interact'
            ? 'interacted with'
            : action.action_type === 'decide'
              ? 'decided'
              : action.action_type === 'work'
                ? 'worked on'
                : action.action_type === 'create'
                  ? 'created'
                  : 'did'

  const isSpeech = action.action_type === 'speak'

  return (
    <div key={action.id} className="flex items-start gap-2">
      <span className="shrink-0 mt-0.5" title={action.action_type}>
        <ActionIcon type={action.action_type} />
      </span>
      <div className="flex-1 min-w-0">
        <span className="text-text-tertiary text-[10px] font-mono uppercase mr-2">
          {action.action_type}
        </span>
        {isSpeech ? (
          <p className="text-text-primary text-xs italic">
            &ldquo;{action.content.slice(0, 150)}
            {action.content.length > 150 ? '...' : ''}&rdquo;
          </p>
        ) : (
          <p className="text-text-tertiary text-xs">
            {action.target && action.action_type === 'move'
              ? `${actionVerb} ${action.target}`
              : action.target
                ? `${actionVerb} ${action.target}: ${action.content.slice(0, 100)}${action.content.length > 100 ? '...' : ''}`
                : `${actionVerb}: ${action.content.slice(0, 150)}${action.content.length > 150 ? '...' : ''}`}
          </p>
        )}
      </div>
    </div>
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

      {groups.map((group, idx) => (
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
      ))}
    </div>
  )
}
