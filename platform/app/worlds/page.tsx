import { WorldRow } from '@/components/world/WorldRow'
import { WorldCatalog } from '@/components/world/WorldCatalog'

export default function WorldsPage() {
  return (
    <div className="py-6 md:py-8">
      {/* Header with glass effect */}
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12 mb-6 md:mb-8 animate-fade-in">
        <div className="glass-cyan p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-neon-cyan rounded-full shadow-[0_0_8px_var(--neon-cyan)]" />
            <h1 className="font-display text-sm md:text-base text-neon-cyan tracking-wider">WORLD CATALOG</h1>
          </div>
          <p className="text-text-secondary text-xs md:text-sm">
            Explore scientifically plausible futures — each world branches from today through a unique causal chain
          </p>
        </div>
      </div>

      {/* Netflix-style rows */}
      <div className="max-w-[calc(100vw-1rem)] md:max-w-7xl mx-auto pl-6 md:pl-8 lg:pl-12 space-y-2">
        <WorldRow title="TRENDING NOW" sortBy="popular" limit={10} />
        <WorldRow title="MOST ACTIVE" sortBy="active" limit={10} />
        <WorldRow title="RECENTLY CREATED" sortBy="recent" limit={10} />
      </div>

      {/* Full catalog with filters */}
      <div className="max-w-7xl mx-auto px-6 md:px-8 lg:px-12 mt-12 md:mt-16">
        <div className="border-t border-white/5 pt-8">
          <h2 className="text-xs md:text-sm text-text-primary font-mono tracking-wider mb-6">
            ALL WORLDS
          </h2>
          <WorldCatalog />
        </div>
      </div>
    </div>
  )
}
