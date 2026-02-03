import { FeedContainer } from '@/components/feed/FeedContainer'

export default function FeedPage() {
  return (
    <div className="max-w-6xl mx-auto px-6 md:px-8 lg:px-12 py-6 md:py-8">
      {/* Header with glass effect */}
      <div className="glass-cyan mb-8 animate-fade-in">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse shadow-[0_0_8px_var(--neon-cyan)]" />
            <h1 className="font-display text-sm md:text-base text-neon-cyan tracking-wider">LIVE</h1>
          </div>
          <p className="text-text-secondary text-xs md:text-sm">
            See what's cooking across the worlds.
          </p>
        </div>
      </div>

      <FeedContainer />
    </div>
  )
}
