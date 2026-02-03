'use client'

import { useState, useRef, useEffect } from 'react'

interface VideoPlayerProps {
  src: string
  poster?: string
  autoPlay?: boolean
  muted?: boolean
  loop?: boolean
  className?: string
  onEnded?: () => void
}

export function VideoPlayer({
  src,
  poster,
  autoPlay = false,
  muted = true,
  loop = false,
  className = '',
  onEnded,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)
  const [isPlaying, setIsPlaying] = useState(autoPlay)
  const [isMuted, setIsMuted] = useState(muted)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const [showControls, setShowControls] = useState(true)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const controlsTimeoutRef = useRef<NodeJS.Timeout>()

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const togglePlay = () => {
    if (!videoRef.current) return

    if (isPlaying) {
      videoRef.current.pause()
    } else {
      videoRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  const toggleMute = () => {
    if (!videoRef.current) return
    videoRef.current.muted = !isMuted
    setIsMuted(!isMuted)
  }

  const toggleFullscreen = async () => {
    const container = videoRef.current?.parentElement
    if (!container) return

    if (!isFullscreen) {
      await container.requestFullscreen?.()
    } else {
      await document.exitFullscreen?.()
    }
  }

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current || !progressRef.current) return

    const rect = progressRef.current.getBoundingClientRect()
    const pos = (e.clientX - rect.left) / rect.width
    videoRef.current.currentTime = pos * videoRef.current.duration
  }

  const handleMouseMove = () => {
    setShowControls(true)
    if (controlsTimeoutRef.current) {
      clearTimeout(controlsTimeoutRef.current)
    }
    controlsTimeoutRef.current = setTimeout(() => {
      if (isPlaying) {
        setShowControls(false)
      }
    }, 3000)
  }

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      setProgress((video.currentTime / video.duration) * 100)
    }

    const handleLoadedMetadata = () => {
      setDuration(video.duration)
    }

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    const handleEnded = () => {
      setIsPlaying(false)
      onEnded?.()
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('loadedmetadata', handleLoadedMetadata)
    video.addEventListener('ended', handleEnded)
    document.addEventListener('fullscreenchange', handleFullscreenChange)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      video.removeEventListener('ended', handleEnded)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      if (controlsTimeoutRef.current) {
        clearTimeout(controlsTimeoutRef.current)
      }
    }
  }, [onEnded])

  return (
    <div
      className={`relative bg-black group ${className}`}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => isPlaying && setShowControls(false)}
    >
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        autoPlay={autoPlay}
        muted={muted}
        loop={loop}
        playsInline
        className="w-full h-full object-cover"
        onClick={togglePlay}
      />

      {/* Play overlay (when paused) */}
      {!isPlaying && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-black/40 cursor-pointer"
          onClick={togglePlay}
        >
          <div className="w-16 h-16 flex items-center justify-center bg-neon-cyan/20 border border-neon-cyan/50 text-neon-cyan text-3xl hover:bg-neon-cyan/30 transition-colors">
            ▶
          </div>
        </div>
      )}

      {/* Controls */}
      <div
        className={`
          absolute bottom-0 left-0 right-0
          bg-gradient-to-t from-black/80 to-transparent
          p-3
          transition-opacity duration-200
          ${showControls || !isPlaying ? 'opacity-100' : 'opacity-0'}
        `}
      >
        {/* Progress bar */}
        <div
          ref={progressRef}
          className="video-progress h-1 mb-3 cursor-pointer group/progress"
          onClick={handleProgressClick}
        >
          <div
            className="video-progress-fill h-full relative"
            style={{ width: `${progress}%` }}
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-neon-cyan opacity-0 group-hover/progress:opacity-100 transition-opacity" />
          </div>
        </div>

        {/* Control buttons */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {/* Play/Pause */}
            <button
              onClick={togglePlay}
              className="text-text-primary hover:text-neon-cyan transition-colors"
              aria-label={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5,3 19,12 5,21" />
                </svg>
              )}
            </button>

            {/* Mute/Unmute */}
            <button
              onClick={toggleMute}
              className="text-text-primary hover:text-neon-cyan transition-colors"
              aria-label={isMuted ? 'Unmute' : 'Mute'}
            >
              {isMuted ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor" />
                  <line x1="23" y1="9" x2="17" y2="15" />
                  <line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
              )}
            </button>

            {/* Time */}
            <span className="text-text-secondary text-xs font-mono">
              {formatTime(videoRef.current?.currentTime || 0)} / {formatTime(duration)}
            </span>
          </div>

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="text-text-primary hover:text-neon-cyan transition-colors"
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

interface VideoPreviewProps {
  src: string
  poster?: string
  className?: string
}

export function VideoPreview({ src, poster, className = '' }: VideoPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isHovering, setIsHovering] = useState(false)

  useEffect(() => {
    if (!videoRef.current) return

    if (isHovering) {
      videoRef.current.currentTime = 0
      videoRef.current.play().catch(() => {})
    } else {
      videoRef.current.pause()
    }
  }, [isHovering])

  return (
    <div
      className={`relative ${className}`}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
    >
      {/* Poster image */}
      {poster && !isHovering && (
        <img
          src={poster}
          alt=""
          className="absolute inset-0 w-full h-full object-cover"
        />
      )}

      {/* Video (preloaded, plays on hover) */}
      <video
        ref={videoRef}
        src={src}
        muted
        loop
        playsInline
        preload="metadata"
        className={`
          w-full h-full object-cover
          transition-opacity duration-200
          ${isHovering ? 'opacity-100' : 'opacity-0'}
        `}
      />

      {/* Play indicator */}
      {!isHovering && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-6xl text-neon-cyan/20">▶</div>
        </div>
      )}
    </div>
  )
}
