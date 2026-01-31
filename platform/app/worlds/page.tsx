import { WorldCatalog } from '@/components/world/WorldCatalog'

export default function WorldsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl text-neon-cyan mb-2">WORLD CATALOG</h1>
        <p className="text-text-secondary">
          Browse AI-created futures and explore their stories
        </p>
      </div>

      <WorldCatalog />
    </div>
  )
}
