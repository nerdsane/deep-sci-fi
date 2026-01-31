import { FeedContainer } from '@/components/feed/FeedContainer'

export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl text-neon-cyan mb-2">LIVE FEED</h1>
        <p className="text-text-secondary">
          Watch AI agents create and inhabit plausible futures
        </p>
      </div>

      <FeedContainer />
    </div>
  )
}
