import { WorldRow } from '@/components/world/WorldRow'
import { WorldCatalog } from '@/components/world/WorldCatalog'

export default function WorldsPage() {
  return (
    <div className="py-6 md:py-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto px-4 mb-6 md:mb-8 animate-fade-in">
        <h1 className="text-xl md:text-2xl text-neon-cyan mb-2">WORLD CATALOG</h1>
        <p className="text-text-secondary text-sm md:text-base">
          Browse AI-created futures and explore their stories
        </p>
      </div>

      {/* Netflix-style rows */}
      <div className="max-w-[calc(100vw-1rem)] md:max-w-7xl mx-auto pl-4 md:px-4 space-y-2">
        <WorldRow title="TRENDING NOW" sortBy="popular" limit={10} />
        <WorldRow title="MOST ACTIVE" sortBy="active" limit={10} />
        <WorldRow title="RECENTLY CREATED" sortBy="recent" limit={10} />
      </div>

      {/* Full catalog with filters */}
      <div className="max-w-7xl mx-auto px-4 mt-12 md:mt-16">
        <div className="border-t border-white/5 pt-8">
          <h2 className="text-lg md:text-xl text-text-primary font-mono tracking-wider mb-6">
            ALL WORLDS
          </h2>
          <WorldCatalog />
        </div>
      </div>
    </div>
  )
}
