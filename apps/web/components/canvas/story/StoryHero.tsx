interface StoryHeroProps {
  title: string;
  subtitle?: string;
  heroImage?: string;
  worldName?: string;
  chapterInfo?: string;
  readTime?: string;
  scrollProgress: number;
  onWorldClick?: () => void;
}

export function StoryHero({
  title,
  subtitle,
  heroImage,
  worldName,
  chapterInfo,
  readTime,
  scrollProgress,
  onWorldClick
}: StoryHeroProps) {
  // Parallax calculations - hero moves slower than scroll
  const parallaxOffset = scrollProgress * 150;
  const opacity = Math.max(0, 1 - scrollProgress * 2);
  const scale = 1 + scrollProgress * 0.1;
  const blur = scrollProgress * 8;

  return (
    <div className="story-hero">
      {/* Background image with parallax */}
      {heroImage && (
        <div
          className="hero-image-container"
          style={{
            transform: `translateY(${parallaxOffset}px) scale(${scale})`,
            opacity: Math.max(0.3, opacity),
            filter: `blur(${blur}px)`
          }}
        >
          <img src={heroImage} alt="" className="hero-image" />
          <div className="hero-image-overlay" />
        </div>
      )}

      {/* Gradient overlay for readability */}
      <div className="hero-gradient" />

      {/* Content */}
      <div
        className="hero-content"
        style={{
          opacity,
          transform: `translateY(${parallaxOffset * 0.5}px)`
        }}
      >
        {/* World badge */}
        {worldName && (
          <button
            className="hero-world-badge"
            onClick={onWorldClick}
            type="button"
          >
            <span className="world-icon">◈</span>
            <span className="world-name">{worldName}</span>
          </button>
        )}

        {/* Title */}
        <h1 className="hero-title">{title}</h1>

        {/* Subtitle */}
        {subtitle && <p className="hero-subtitle">{subtitle}</p>}

        {/* Meta info */}
        <div className="hero-meta">
          {chapterInfo && <span className="meta-chapter">{chapterInfo}</span>}
          {chapterInfo && readTime && <span className="meta-dot">•</span>}
          {readTime && <span className="meta-time">{readTime}</span>}
        </div>

        {/* Scroll indicator */}
        <div className="hero-scroll-indicator">
          <span className="scroll-text">Scroll to begin</span>
          <div className="scroll-arrow">
            <span>↓</span>
          </div>
        </div>
      </div>
    </div>
  );
}
