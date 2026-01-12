'use client';

import { useState, useCallback, useRef } from 'react';
import * as THREE from 'three';

export type TransitionPhase = 'idle' | 'approach' | 'warp' | 'arrive';

export interface CameraState {
  target: THREE.Vector3 | null;
  lookAt: THREE.Vector3 | null;
  isTransitioning: boolean;
  phase: TransitionPhase;
  progress: number; // 0-1 progress through animation
  warpIntensity: number; // For visual effects
}

const DEFAULT_POSITION = new THREE.Vector3(0, 2, 15);
const DEFAULT_LOOK_AT = new THREE.Vector3(0, 0, 0);

export function useObservatoryCamera() {
  const [cameraState, setCameraState] = useState<CameraState>({
    target: null,
    lookAt: null,
    isTransitioning: false,
    phase: 'idle',
    progress: 0,
    warpIntensity: 0,
  });

  const animationRef = useRef<number | null>(null);

  // Zoom camera toward a world with dramatic warp effect
  const zoomToWorld = useCallback((targetPosition: THREE.Vector3, lookAtPosition: THREE.Vector3, onComplete?: () => void) => {
    // Cancel any existing animation
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    const startTime = performance.now();
    const duration = 1800; // Total animation time in ms

    // Phase timings (as percentage of total duration)
    const phases = {
      approach: { start: 0, end: 0.3 },      // 0-30%: Camera starts moving
      warp: { start: 0.3, end: 0.8 },        // 30-80%: Full warp speed
      arrive: { start: 0.8, end: 1.0 },      // 80-100%: Decelerate and arrive
    };

    const animate = () => {
      const elapsed = performance.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Determine current phase
      let phase: TransitionPhase = 'approach';
      let warpIntensity = 0;

      if (progress >= phases.arrive.start) {
        phase = 'arrive';
        // Ease out warp intensity
        const phaseProgress = (progress - phases.arrive.start) / (phases.arrive.end - phases.arrive.start);
        warpIntensity = 1 - easeOutCubic(phaseProgress);
      } else if (progress >= phases.warp.start) {
        phase = 'warp';
        // Full warp with slight pulse
        const phaseProgress = (progress - phases.warp.start) / (phases.warp.end - phases.warp.start);
        warpIntensity = 0.8 + Math.sin(phaseProgress * Math.PI * 3) * 0.2;
      } else {
        phase = 'approach';
        // Ease in warp intensity
        const phaseProgress = progress / phases.approach.end;
        warpIntensity = easeInCubic(phaseProgress);
      }

      setCameraState({
        target: targetPosition,
        lookAt: lookAtPosition,
        isTransitioning: true,
        phase,
        progress,
        warpIntensity,
      });

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        // Animation complete
        onComplete?.();
      }
    };

    animationRef.current = requestAnimationFrame(animate);
  }, []);

  // Reset camera to default position
  const resetCamera = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }

    setCameraState({
      target: DEFAULT_POSITION.clone(),
      lookAt: DEFAULT_LOOK_AT.clone(),
      isTransitioning: true,
      phase: 'approach',
      progress: 0,
      warpIntensity: 0,
    });

    // Clear transition after animation completes
    setTimeout(() => {
      setCameraState({
        target: null,
        lookAt: null,
        isTransitioning: false,
        phase: 'idle',
        progress: 0,
        warpIntensity: 0,
      });
    }, 1000);
  }, []);

  // Pan camera to a position without zooming
  const panTo = useCallback((position: THREE.Vector3) => {
    setCameraState(prev => ({
      ...prev,
      target: position,
      lookAt: DEFAULT_LOOK_AT.clone(),
      isTransitioning: true,
    }));
  }, []);

  return {
    cameraState,
    zoomToWorld,
    resetCamera,
    panTo,
  };
}

// Easing functions
function easeInCubic(t: number): number {
  return t * t * t;
}

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}
