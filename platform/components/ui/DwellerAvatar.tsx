'use client'

import { useState } from 'react'

interface DwellerAvatarProps {
  name: string
  portrait_url?: string | null
  sizeClass?: string
  textClass?: string
}

export function DwellerAvatar({
  name,
  portrait_url,
  sizeClass = 'w-14 h-14',
  textClass = 'text-lg',
}: DwellerAvatarProps) {
  const [imgError, setImgError] = useState(false)

  if (portrait_url && !imgError) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={portrait_url}
        alt={name}
        className={`${sizeClass} object-cover shrink-0`}
        onError={() => setImgError(true)}
      />
    )
  }

  return (
    <div className={`${sizeClass} bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 flex items-center justify-center ${textClass} font-mono text-neon-cyan shrink-0`}>
      {name.charAt(0)}
    </div>
  )
}
