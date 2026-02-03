'use client'

import { HTMLAttributes, forwardRef } from 'react'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean
  accent?: 'cyan' | 'purple' | 'none'
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className = '', hover = true, accent = 'cyan', children, ...props }, ref) => {
    const accentStyles = {
      cyan: 'hover:border-neon-cyan/30 hover:shadow-lg hover:shadow-neon-cyan/5',
      purple: 'hover:border-neon-purple/30 hover:shadow-lg hover:shadow-neon-purple/5',
      none: '',
    }

    return (
      <div
        ref={ref}
        className={`
          glass
          transition-all duration-300
          ${hover ? accentStyles[accent] : ''}
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
