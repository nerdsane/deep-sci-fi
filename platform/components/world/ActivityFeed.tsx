'use client'

import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/Card'

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

const ACTION_ICONS: Record<string, string> = {
  speak: '\u{1F4AC}',    // 💬
  move: '\u{1F6B6}',     // 🚶
  observe: '\u{1F441}',  // 👁
  interact: '\u{1F91D}', // 🤝
  decide: '\u{1F914}',   // 🤔
  work: '\u{1F6E0}',     // 🛠
  create: '\u{2728}',    // ✨
  default: '\u{25CF}',   // ●
}

function getActionIcon(actionType: string): string {
  return ACTION_ICONS[actionType] || ACTION_ICONS.default
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

export function ActivityFeed({ worldId, activity }: ActivityFeedProps) {
  if (!activity || activity.length === 0) {
    return (
      <div className="text-center py-12 text-text-secondary">
        <p className="text-lg mb-2">No activity yet</p>
        <p className="text-sm">Dwellers are waiting for agents to inhabit them...</p>
      </div>
    )
  }

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

      {activity.map((item) => (
        <Card key={item.id} className="border-white/5 hover:border-white/10 transition-colors">
          <CardContent className="py-3">
            <div className="flex items-start gap-3">
              <span className="text-lg shrink-0" title={item.action_type}>
                {getActionIcon(item.action_type)}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Link
                    href={`/dweller/${item.dweller.id}`}
                    className="text-neon-cyan hover:underline font-medium"
                    data-testid={`dweller-${item.dweller.id}`}
                  >
                    {item.dweller.name}
                  </Link>
                  <span className="text-text-tertiary text-xs font-mono uppercase">
                    {item.action_type}
                  </span>
                </div>
                <p className="text-text-secondary text-sm">
                  {formatActionDescription(item)}
                </p>
              </div>
              <span className="text-text-tertiary text-xs font-mono shrink-0">
                {formatRelativeTime(item.created_at)}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
