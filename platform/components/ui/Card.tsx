'use client'

import { HTMLAttributes, forwardRef } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  accent?: 'cyan' | 'purple' | 'none'
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', hover = true, accent = 'cyan', children, ...props }, ref) => {
    const accentStyles = {
      cyan: 'hover:border-t-neon-cyan/50',
      purple: 'hover:border-t-neon-purple/50',
      none: '',
    }

    return (
      <div
        ref={ref}
        className={`
          bg-bg-secondary
          border border-white/5
          ${hover ? 'card-hover' : ''}
          ${accent !== 'none' ? accentStyles[accent] : ''}
          ${className}
        `}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export function CardHeader({
  className = '',
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`border-b border-white/5 px-4 py-3 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardContent({
  className = '',
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`px-4 py-4 ${className}`} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({
  className = '',
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`border-t border-white/5 px-4 py-3 ${className}`}
      {...props}
    >
      {children}
    </div>
  )
}
