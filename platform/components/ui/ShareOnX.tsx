'use client'

interface ShareOnXProps {
  text: string
  url?: string
  hashtags?: string[]
}

export function ShareOnX({ text, url, hashtags }: ShareOnXProps) {
  const handleShare = () => {
    const params = new URLSearchParams()
    params.append('text', text)
    params.append('url', url || window.location.href)
    if (hashtags?.length) params.append('hashtags', hashtags.join(','))
    window.open(
      `https://twitter.com/intent/tweet?${params}`,
      '_blank',
      'noopener,noreferrer'
    )
  }

  return (
    <button
      onClick={handleShare}
      className="
        px-3 py-1.5 font-display text-[10px] tracking-wider uppercase
        border border-neon-cyan/30 text-neon-cyan/70
        hover:text-neon-cyan hover:border-neon-cyan hover:bg-neon-cyan/10
        hover:shadow-[0_0_12px_var(--neon-cyan)/20]
        transition-all cursor-pointer
        flex items-center gap-1.5
      "
    >
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-3 h-3"
        aria-hidden="true"
      >
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
      SHARE
    </button>
  )
}
