import React, { useEffect, useState } from 'react';
import './experience.css';

export interface ProgressBarProps {
  /** Container element to track scroll progress within. Defaults to document */
  containerId?: string;
  /** Position of the progress bar */
  position?: 'top' | 'bottom';
  /** Height of the bar in pixels */
  height?: number;
  /** Show percentage label */
  showLabel?: boolean;
}

export function ProgressBar({
  containerId,
  position = 'top',
  height = 2,
  showLabel = false,
}: ProgressBarProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const calculateProgress = () => {
      let scrollTop: number;
      let scrollHeight: number;
      let clientHeight: number;

      if (containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        scrollTop = container.scrollTop;
        scrollHeight = container.scrollHeight;
        clientHeight = container.clientHeight;
      } else {
        scrollTop = window.scrollY;
        scrollHeight = document.documentElement.scrollHeight;
        clientHeight = window.innerHeight;
      }

      const maxScroll = scrollHeight - clientHeight;
      const currentProgress = maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
      setProgress(Math.min(100, Math.max(0, currentProgress)));
    };

    const target = containerId
      ? document.getElementById(containerId)
      : window;

    if (!target) return;

    target.addEventListener('scroll', calculateProgress, { passive: true });
    calculateProgress(); // Initial calculation

    return () => target.removeEventListener('scroll', calculateProgress);
  }, [containerId]);

  return (
    <div
      className={`exp-progress exp-progress--${position}`}
      style={{ height: `${height}px` }}
    >
      <div
        className="exp-progress__bar"
        style={{ transform: `scaleX(${progress / 100})` }}
      />
      {showLabel && (
        <span className="exp-progress__label">{Math.round(progress)}%</span>
      )}
    </div>
  );
}
