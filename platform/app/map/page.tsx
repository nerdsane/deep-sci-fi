import type { Metadata } from 'next'
import { WorldMapCanvas } from '@/components/world/WorldMapCanvas'

export const metadata: Metadata = {
  title: 'The Archaeology',
  description: 'A constellation map of all sci-fi worlds, positioned by thematic similarity.',
}

export default function MapPage() {
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 px-6 md:px-8 lg:px-12 py-4 border-b border-white/5">
        <div className="max-w-7xl mx-auto flex items-center gap-4">
          <div className="w-2 h-2 bg-neon-purple rounded-full shadow-[0_0_8px_var(--neon-purple)]" />
          <div>
            <h1 className="font-display text-sm md:text-base text-neon-purple tracking-wider">
              THE ARCHAEOLOGY
            </h1>
            <p className="text-zinc-400 text-xs mt-0.5">
              Worlds positioned by thematic similarity — a constellation of speculative thought
            </p>
          </div>
        </div>
      </div>

      {/* Full-bleed map canvas */}
      <div className="flex-1 min-h-0 relative">
        <WorldMapCanvas />
      </div>
    </div>
  )
}
