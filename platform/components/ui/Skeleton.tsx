'use client'

import { HTMLAttributes } from 'react'

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'text' | 'rectangular' | 'circular'
}

export function Skeleton({
  className = '',
  variant = 'rectangular',
  ...props
}: SkeletonProps) {
  const variantStyles = {
    text: 'h-4 w-full',
    rectangular: '',
    circular: 'rounded-full',
  }

  return (
    <div
      className={`skeleton bg-bg-tertiary ${variantStyles[variant]} ${className}`}
      {...props}
    />
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-bg-secondary border border-white/5 overflow-hidden animate-fade-in">
      {/* Thumbnail */}
      <div className="aspect-video skeleton" />

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* World badge */}
        <Skeleton className="h-3 w-24" />

        {/* Title */}
        <Skeleton className="h-5 w-3/4" />

        {/* Description */}
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>

        {/* Stats */}
        <div className="flex gap-4 pt-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-3 w-20" />
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/5 px-4 py-3 flex justify-between">
        <div className="flex gap-3">
          <Skeleton className="h-6 w-12" />
          <Skeleton className="h-6 w-12" />
          <Skeleton className="h-6 w-12" />
        </div>
        <Skeleton className="h-6 w-20" />
      </div>
    </div>
  )
}

export function ConversationSkeleton() {
  return (
    <div className="bg-bg-secondary border border-white/5 overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-10" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-4 w-16" />
      </div>

      {/* Participants */}
      <div className="px-4 py-4 border-b border-white/5">
        <div className="flex gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-8 w-8" />
              <div className="space-y-1">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="h-6 w-6 shrink-0" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-3 w-2/3" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function WorldCardSkeleton() {
  return (
    <div className="bg-bg-secondary border border-white/5 overflow-hidden animate-fade-in">
      {/* Thumbnail */}
      <div className="aspect-video skeleton" />

      {/* Content */}
      <div className="p-4 space-y-3">
        <Skeleton className="h-5 w-2/3" />
        <div className="space-y-2">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-3/4" />
        </div>
        <div className="flex gap-4 pt-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/5 px-4 py-3 flex justify-between">
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>
    </div>
  )
}

interface FeedSkeletonProps {
  count?: number
}

export function FeedSkeleton({ count = 3 }: FeedSkeletonProps) {
  return (
    <div className="space-y-6">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}

export function WorldGridSkeleton({ count = 6 }: FeedSkeletonProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {Array.from({ length: count }).map((_, i) => (
        <WorldCardSkeleton key={i} />
      ))}
    </div>
  )
}
