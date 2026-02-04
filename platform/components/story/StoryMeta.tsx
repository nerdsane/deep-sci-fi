'use client'

import type { StoryDetail } from '@/lib/api'

interface StoryMetaProps {
  story: StoryDetail
}

const perspectiveLabels: Record<string, string> = {
  first_person_agent: 'First Person (Agent)',
  first_person_dweller: 'First Person (Dweller)',
  third_person_limited: 'Third Person Limited',
  third_person_omniscient: 'Third Person Omniscient',
}

export function StoryMeta({ story }: StoryMetaProps) {
  const hasPerspectiveDweller = story.perspective_dweller_name
  const hasTimePeriod = story.time_period_start || story.time_period_end
  const hasSources = (story.source_events?.length || 0) > 0 || (story.source_actions?.length || 0) > 0

  if (!hasPerspectiveDweller && !hasTimePeriod && !hasSources) {
    return null
  }

  return (
    <div className="glass p-4 space-y-3">
      {/* Perspective info */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-display tracking-wider text-text-tertiary">PERSPECTIVE:</span>
          <span className="text-sm text-text-secondary">
            {perspectiveLabels[story.perspective] || story.perspective}
          </span>
        </div>

        {hasPerspectiveDweller && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-display tracking-wider text-text-tertiary">VIA:</span>
            <span className="text-sm text-neon-purple">{story.perspective_dweller_name}</span>
          </div>
        )}
      </div>

      {/* Time period */}
      {hasTimePeriod && (
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-display tracking-wider text-text-tertiary">TIME PERIOD:</span>
          <span className="text-sm text-text-secondary font-mono">
            {story.time_period_start}
            {story.time_period_end && story.time_period_end !== story.time_period_start && (
              <> to {story.time_period_end}</>
            )}
          </span>
        </div>
      )}

      {/* Sources */}
      {hasSources && (
        <div className="flex flex-wrap items-start gap-2">
          <span className="text-[10px] font-display tracking-wider text-text-tertiary pt-0.5">SOURCES:</span>
          <div className="flex flex-wrap gap-2">
            {story.source_events?.map((event) => (
              <span
                key={`event-${event.id}`}
                className="text-xs font-mono px-2 py-0.5 bg-neon-purple/10 border border-neon-purple/30 text-neon-purple"
              >
                {event.title}
              </span>
            ))}
            {story.source_actions?.map((action) => (
              <span
                key={`action-${action.id}`}
                className="text-xs font-mono px-2 py-0.5 bg-neon-cyan/10 border border-neon-cyan/30 text-neon-cyan"
              >
                {action.dweller_name} &middot; {action.action_type}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
