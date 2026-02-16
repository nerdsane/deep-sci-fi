'use client'

interface ShareOnXProps {
  text: string
  url?: string
  hashtags?: string[]
  xPostId?: string
}

const buttonClass = `
  px-3 py-1.5 font-display text-[10px] tracking-wider uppercase
  border border-neon-cyan/30 text-neon-cyan/70
  hover:text-neon-cyan hover:border-neon-cyan hover:bg-neon-cyan/10
  hover:shadow-[0_0_12px_var(--neon-cyan)/20]
  transition-all cursor-pointer
  flex items-center gap-1.5
`

function XIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className="w-3 h-3"
      aria-hidden="true"
    >
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  )
}

export function ShareOnX({ text, url, hashtags, xPostId }: ShareOnXProps) {
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

  const handleRepost = () => {
    window.open(
      `https://twitter.com/intent/retweet?tweet_id=${xPostId}`,
      '_blank',
      'noopener,noreferrer'
    )
  }

  return (
    <div className="flex items-center gap-2">
      <button onClick={handleShare} className={buttonClass}>
        <XIcon />
        SHARE
      </button>
      {xPostId && (
        <button onClick={handleRepost} className={buttonClass}>
          <svg
            viewBox="0 0 24 24"
            fill="currentColor"
            className="w-3 h-3"
            aria-hidden="true"
          >
            <path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2h6v2h-6c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H10.5V4h6c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z" />
          </svg>
          REPOST
        </button>
      )}
    </div>
  )
}
