'use client'

import { formatDistanceToNow } from 'date-fns'
import type { World } from '@/types'
import { Card, CardContent, CardFooter } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'

interface WorldCreatedCardProps {
  world: World
}

export function WorldCreatedCard({ world }: WorldCreatedCardProps) {
  return (
    <Card>
      <CardContent>
        {/* New world badge */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-mono text-neon-cyan bg-neon-cyan/10 border border-neon-cyan/30 px-2 py-0.5">
            NEW WORLD
          </span>
          <span className="text-xs text-text-tertiary">
            {formatDistanceToNow(world.createdAt, { addSuffix: true })}
          </span>
        </div>

        {/* World info */}
        <h3 className="text-xl text-neon-cyan mb-2">{world.name}</h3>
        <p className="text-text-primary mb-4">{world.premise}</p>

        {/* Causal chain preview */}
        {world.causalChain.length > 0 && (
          <div className="border border-white/5 bg-bg-tertiary p-4 mb-4">
            <div className="text-xs font-mono text-text-tertiary mb-3">
              CAUSAL CHAIN TO {world.yearSetting}
            </div>
            <div className="space-y-2">
              {world.causalChain.slice(0, 3).map((event, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="text-xs font-mono text-neon-cyan shrink-0 mt-0.5">
                    {event.year}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-text-primary">
                      {event.event}
                    </div>
                    <div className="text-xs text-text-tertiary mt-0.5">
                      → {event.consequence}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats */}
        <div className="flex items-center gap-4 text-text-tertiary text-xs font-mono">
          <span>{world.dwellerCount} DWELLERS</span>
          <span>•</span>
          <span>{world.followerCount} FOLLOWERS</span>
        </div>
      </CardContent>

      <CardFooter className="flex items-center gap-3">
        <Button variant="primary" size="sm">
          EXPLORE WORLD
        </Button>
        <Button variant="ghost" size="sm">
          FOLLOW
        </Button>
      </CardFooter>
    </Card>
  )
}
