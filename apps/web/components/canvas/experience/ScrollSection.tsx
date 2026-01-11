import React, { useEffect, useRef, useState } from 'react';
import './experience.css';

// Global cache to remember which elements have been animated (persists across re-renders)
const animatedElements = new Set<string>();

export interface ScrollSectionProps {
  children: React.ReactNode;
  animation?: 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right' | 'scale' | 'none';
  delay?: number;
  threshold?: number;
  className?: string;
  as?: 'div' | 'section' | 'article';
  /** Unique key to persist animation state across re-renders. If provided, element won't re-animate. */
  persistKey?: string;
}

export function ScrollSection({
  children,
  animation = 'fade-up',
  delay = 0,
  threshold = 0.2,
  className = '',
  as: Component = 'div',
  persistKey,
}: ScrollSectionProps) {
  const ref = useRef<HTMLElement>(null);
  // If persistKey exists and was already animated, start visible
  const wasAlreadyAnimated = persistKey ? animatedElements.has(persistKey) : false;
  const [isVisible, setIsVisible] = useState(wasAlreadyAnimated);

  useEffect(() => {
    // If already visible (from cache), skip observer
    if (isVisible) return;

    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            // Remember this element was animated
            if (persistKey) {
              animatedElements.add(persistKey);
            }
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold, isVisible, persistKey]);

  const animationClass = animation !== 'none' ? `exp-scroll--${animation}` : '';
  const visibleClass = isVisible ? 'exp-scroll--visible' : '';

  return (
    <Component
      ref={ref as any}
      className={`exp-scroll ${animationClass} ${visibleClass} ${className}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </Component>
  );
}
