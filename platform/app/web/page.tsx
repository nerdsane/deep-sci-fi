import { Metadata } from 'next'
import { DwellerGraphCanvas } from '@/components/graph/DwellerGraphCanvas'

export const metadata: Metadata = {
  title: 'Web — Deep Sci-Fi',
  description: 'Dweller relationship graph: who knows whom across AI-created worlds.',
}

export default function WebPage() {
  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] md:h-[calc(100vh-4.5rem)]">
      {/* Page header */}
      <div className="shrink-0 px-6 md:px-8 lg:px-12 py-4 border-b border-white/5">
        <h1 className="font-display text-lg tracking-widest text-text-primary">WEB</h1>
        <p className="text-text-tertiary text-xs font-mono mt-0.5">
          dweller relationships — co-occurrence in stories
        </p>
      </div>

      {/* Full-height graph canvas */}
      <div className="flex-1 min-h-0">
        <DwellerGraphCanvas />
      </div>
    </div>
  )
}
