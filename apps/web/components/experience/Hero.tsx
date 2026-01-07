import React, { useEffect, useRef, useState } from 'react';
import './experience.css';

export interface HeroProps {
  title: string;
  subtitle?: string;
  backgroundImage?: string;
  badge?: string;
  meta?: string[];
  showScrollIndicator?: boolean;
  height?: 'full' | 'large' | 'medium' | 'compact';
  overlay?: 'dark' | 'gradient' | 'none';
  onBadgeClick?: () => void;
  onScrollClick?: () => void;
}

export function Hero({
  title,
  subtitle,
  backgroundImage,
  badge,
  meta,
  showScrollIndicator = true,
  height = 'full',
  overlay = 'gradient',
  onBadgeClick,
  onScrollClick,
}: HeroProps) {
  const heroRef = useRef<HTMLDivElement>(null);
  const [scrollY, setScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      if (heroRef.current) {
        const rect = heroRef.current.getBoundingClientRect();
        if (rect.bottom > 0) {
          setScrollY(window.scrollY);
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const parallaxOffset = scrollY * 0.3;
  const contentOpacity = Math.max(0, 1 - scrollY / 400);

  const heightClass = {
    full: 'exp-hero--full',
    large: 'exp-hero--large',
    medium: 'exp-hero--medium',
    compact: 'exp-hero--compact',
  }[height];

  const handleScrollClick = () => {
    if (onScrollClick) {
      onScrollClick();
    } else {
      // Default: scroll to next section
      window.scrollTo({
        top: window.innerHeight,
        behavior: 'smooth',
      });
    }
  };

  return (
    <section ref={heroRef} className={`exp-hero ${heightClass}`}>
      {backgroundImage && (
        <div
          className="exp-hero__bg"
          style={{ transform: `translateY(${parallaxOffset}px)` }}
        >
          <img src={backgroundImage} alt="" className="exp-hero__bg-image" />
          {overlay !== 'none' && (
            <div className={`exp-hero__overlay exp-hero__overlay--${overlay}`} />
          )}
        </div>
      )}

      <div
        className="exp-hero__content"
        style={{ opacity: contentOpacity, transform: `translateY(${scrollY * 0.1}px)` }}
      >
        {badge && (
          <button
            className="exp-hero__badge"
            onClick={onBadgeClick}
            type="button"
          >
            <span className="exp-hero__badge-icon">◈</span>
            {badge}
          </button>
        )}

        <h1 className="exp-hero__title">{title}</h1>

        {subtitle && <p className="exp-hero__subtitle">{subtitle}</p>}

        {meta && meta.length > 0 && (
          <div className="exp-hero__meta">
            {meta.map((item, i) => (
              <React.Fragment key={i}>
                {i > 0 && <span className="exp-hero__meta-dot">·</span>}
                <span>{item}</span>
              </React.Fragment>
            ))}
          </div>
        )}
      </div>

      {showScrollIndicator && (
        <button
          className="exp-hero__scroll"
          onClick={handleScrollClick}
          type="button"
          aria-label="Scroll down"
        >
          <span className="exp-hero__scroll-text">Scroll</span>
          <span className="exp-hero__scroll-arrow">↓</span>
        </button>
      )}
    </section>
  );
}
