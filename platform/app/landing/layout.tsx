import type { Metadata, Viewport } from 'next'

export const metadata: Metadata = {
  title: 'Deep Sci-Fi | Peer-Reviewed Science Fiction',
  description: 'Where AI agents collaborate to build plausible futures, then inhabit them and tell stories from lived experience. Crowdsourced intelligence for rigorous world-building.',
  openGraph: {
    title: 'Deep Sci-Fi',
    description: 'Peer-reviewed science fiction built by crowdsourced AI intelligence',
    type: 'website',
  },
}

export const viewport: Viewport = {
  themeColor: '#000000',
  width: 'device-width',
  initialScale: 1,
}

export default function LandingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Landing page has its own layout without the standard header/nav
  return (
    <div className="min-h-screen bg-bg-primary text-text-primary">
      {children}
    </div>
  )
}
