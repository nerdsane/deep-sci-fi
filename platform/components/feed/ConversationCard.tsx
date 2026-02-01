'use client'

import { useState, useEffect } from 'react'
import { formatDistanceToNow } from 'date-fns'
import type { Conversation, World, Dweller } from '@/types'
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/Card'
import Link from 'next/link'

interface ConversationCardProps {
  conversation: Conversation
  world?: World
  dwellers?: Dweller[]
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      <div className="typing-dot" />
      <div className="typing-dot" />
      <div className="typing-dot" />
    </div>
  )
}

export function ConversationCard({
  conversation,
  world,
  dwellers = [],
}: ConversationCardProps) {
  const [showTyping, setShowTyping] = useState(false)

  const getDweller = (dwellerId: string) =>
    dwellers.find((d) => d.id === dwellerId)

  // Simulate typing indicator for live conversations
  useEffect(() => {
    // Show typing indicator periodically for live conversations
    const interval = setInterval(() => {
      setShowTyping(true)
      setTimeout(() => setShowTyping(false), 2000)
    }, 8000)

    return () => clearInterval(interval)
  }, [])

  return (
    <Card accent="purple">
      <CardHeader className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-neon-purple border border-neon-purple/50 px-2 py-0.5 animate-pulse">
            LIVE
          </span>
          {world && (
            <Link
              href={`/world/${world.id}`}
              className="text-xs font-mono text-text-secondary hover:text-neon-cyan transition-colors"
            >
              {world.name}
            </Link>
          )}
        </div>
        <span className="text-xs text-text-tertiary">
          {formatDistanceToNow(conversation.updatedAt, { addSuffix: true })}
        </span>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Participants */}
        <div className="flex items-center gap-3 md:gap-4 pb-3 border-b border-white/5 overflow-x-auto scrollbar-hide">
          {dwellers.map((dweller) => (
            <div key={dweller.id} className="flex items-center gap-2 shrink-0">
              <div className="w-8 h-8 bg-neon-purple/20 flex items-center justify-center">
                <span className="text-neon-purple text-sm font-mono">
                  {dweller.persona.name.charAt(0)}
                </span>
              </div>
              <div className="min-w-0">
                <div className="text-sm text-text-primary truncate">
                  {dweller.persona.name}
                </div>
                <div className="text-xs text-text-tertiary truncate">
                  {dweller.persona.role}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Messages */}
        <div className="space-y-3">
          {conversation.messages.slice(-5).map((message, index) => {
            const dweller = getDweller(message.dwellerId)
            const isLast = index === conversation.messages.slice(-5).length - 1
            return (
              <div
                key={message.id}
                className={`flex gap-3 ${isLast ? 'animate-slide-up' : ''}`}
              >
                <div className="w-6 h-6 bg-neon-purple/10 flex items-center justify-center shrink-0 mt-1">
                  <span className="text-neon-purple text-xs">
                    {dweller?.persona.name.charAt(0) || '?'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm text-text-primary font-medium">
                      {dweller?.persona.name || 'Unknown'}
                    </span>
                    <span className="text-xs text-text-tertiary">
                      {formatDistanceToNow(message.timestamp, {
                        addSuffix: true,
                      })}
                    </span>
                  </div>
                  <p className="text-text-secondary text-sm leading-relaxed break-words">
                    {message.content}
                  </p>
                </div>
              </div>
            )
          })}

          {/* Typing indicator */}
          {showTyping && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-6 h-6 bg-neon-purple/10 flex items-center justify-center shrink-0 mt-1">
                <span className="text-neon-purple text-xs">?</span>
              </div>
              <TypingIndicator />
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex items-center justify-between gap-2 flex-wrap">
        <Link
          href={`/conversation/${conversation.id}`}
          className="text-text-secondary hover:text-neon-cyan transition-colors text-xs font-mono"
        >
          VIEW FULL CONVERSATION
        </Link>
        <button className="text-text-secondary hover:text-neon-cyan transition-colors text-xs font-mono">
          FOLLOW WORLD
        </button>
      </CardFooter>
    </Card>
  )
}
