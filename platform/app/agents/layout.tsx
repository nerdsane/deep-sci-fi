'use client'

import { useEffect, useRef } from 'react'

export default function AgentsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Prevent parent scroll by ensuring our container doesn't overflow
    // Find the parent main element and disable its scroll
    const main = containerRef.current?.closest('main')
    if (main) {
      main.style.overflow = 'hidden'
      main.style.paddingBottom = '0'
    }
    return () => {
      if (main) {
        main.style.overflow = ''
        main.style.paddingBottom = ''
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      style={{
        height: '100%',
        width: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      {children}
    </div>
  )
}
