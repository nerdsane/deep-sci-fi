import React, { useEffect, useRef, useState } from 'react';
import './experience.css';

export interface ScrollSectionProps {
  children: React.ReactNode;
  animation?: 'fade-up' | 'fade-in' | 'slide-left' | 'slide-right' | 'scale' | 'none';
  delay?: number;
  threshold?: number;
  className?: string;
  as?: 'div' | 'section' | 'article';
}

export function ScrollSection({
  children,
  animation = 'fade-up',
  delay = 0,
  threshold = 0.2,
  className = '',
  as: Component = 'div',
}: ScrollSectionProps) {
  const ref = useRef<HTMLElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, [threshold]);

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
