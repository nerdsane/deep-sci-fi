'use client';

import Tilt from 'react-parallax-tilt';
import type { ReactNode } from 'react';

export interface TiltCardProps {
  children: ReactNode;
  className?: string;
  tiltMaxAngleX?: number;
  tiltMaxAngleY?: number;
  scale?: number;
  glareEnable?: boolean;
  glareMaxOpacity?: number;
  glareColor?: string;
  glareBorderRadius?: string;
  transitionSpeed?: number;
  disabled?: boolean;
}

export function TiltCard({
  children,
  className = '',
  tiltMaxAngleX = 8,
  tiltMaxAngleY = 8,
  scale = 1.02,
  glareEnable = true,
  glareMaxOpacity = 0.15,
  glareColor = '#00ffcc',
  glareBorderRadius = '4px',
  transitionSpeed = 400,
  disabled = false,
}: TiltCardProps) {
  // Check for reduced motion preference
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

  if (disabled || prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <Tilt
      className={className}
      tiltMaxAngleX={tiltMaxAngleX}
      tiltMaxAngleY={tiltMaxAngleY}
      scale={scale}
      glareEnable={glareEnable}
      glareMaxOpacity={glareMaxOpacity}
      glareColor={glareColor}
      glareBorderRadius={glareBorderRadius}
      transitionSpeed={transitionSpeed}
      perspective={1000}
      gyroscope={false}
    >
      {children}
    </Tilt>
  );
}

export default TiltCard;
