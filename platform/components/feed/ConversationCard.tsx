'use client'

import { formatDistanceToNow } from 'date-fns'
import type { Conversation, World, Dweller } from '@/types'
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/Card'

interface ConversationCardProps {
  conversation: Conversation
  world: World
  dwellers: Dweller[]
}

export function ConversationCard({
  conversation,
  world,
  dwellers,
}: ConversationCardProps) {
  const getDweller = (dwellerId: string) =>
    dwellers.find((d) => d.id === dwellerId)

  return (
    <Card accent="purple">
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-neon-purple border border-neon-purple/50 px-2 py-0.5">
            LIVE
          </span>
          <a
            href={`/world/${world.id}`}
            className="text-xs font-mono text-text-secondary hover:text-neon-cyan transition-colors"
          >
            {world.name}
          </a>
        </div>
        <span className="text-xs text-text-tertiary">
          {formatDistanceToNow(conversation.updatedAt, { addSuffix: true })}
        </span>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Participants */}
        <div className="flex items-center gap-4 pb-3 border-b border-white/5">
          {dwellers.map((dweller) => (
            <div key={dweller.id} className="flex items-center gap-2">
              <div className="w-8 h-8 bg-neon-purple/20 flex items-center justify-center">
                <span className="text-neon-purple text-sm font-mono">
                  {dweller.persona.name.charAt(0)}
                </span>
              </div>
              <div>
                <div className="text-sm text-text-primary">
                  {dweller.persona.name}
                </div>
                <div className="text-xs text-text-tertiary">
                  {dweller.persona.role}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Messages */}
        <div className="space-y-3">
          {conversation.messages.slice(-5).map((message) => {
            const dweller = getDweller(message.dwellerId)
            return (
              <div key={message.id} className="flex gap-3">
                <div className="w-6 h-6 bg-neon-purple/10 flex items-center justify-center shrink-0 mt-1">
                  <span className="text-neon-purple text-xs">
                    {dweller?.persona.name.charAt(0) || '?'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm text-text-primary font-medium">
                      {dweller?.persona.name || 'Unknown'}
                    </span>
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(message.timestamp, {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                  <p className="text-text-secondary text-sm leading-relaxed">
                    {message.content}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between">
        <button className="text-text-secondary hover:text-neon-cyan transition-colors text-xs font-mono">
          VIEW FULL CONVERSATION
        </button>
        <button className="text-text-secondary hover:text-neon-cyan transition-colors text-xs font-mono">
          FOLLOW WORLD
        </button>
      </CardFooter>
    </Card>
  )
}
