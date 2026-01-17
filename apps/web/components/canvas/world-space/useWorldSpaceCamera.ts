/**
 * useWorldSpaceCamera - Camera Navigation Hook
 *
 * Handles smooth camera transitions between points of interest
 * in the immersive world space.
 */

import { useCallback, useRef, useState } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { UseWorldSpaceCameraReturn, CameraTarget } from './types';

// Easing function for smooth camera movement
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

// Default hub position (where user lands on entry)
const HUB_CAMERA_POSITION = new THREE.Vector3(0, 3, 12);
const HUB_LOOK_AT = new THREE.Vector3(0, 0, 0);

// Animation speed (1 = 1 second for full transition)
const FLIGHT_SPEED = 0.7;

export function useWorldSpaceCamera(): UseWorldSpaceCameraReturn {
  const { camera } = useThree();

  // Animation state
  const targetRef = useRef<THREE.Vector3 | null>(null);
  const lookAtRef = useRef<THREE.Vector3 | null>(null);
  const startPositionRef = useRef<THREE.Vector3 | null>(null);
  const startLookAtRef = useRef<THREE.Vector3 | null>(null);
  const progressRef = useRef(0);
  const [isFlying, setIsFlying] = useState(false);
  const [currentTarget, setCurrentTarget] = useState<CameraTarget | null>(null);

  // Current look-at tracking for smooth rotation
  const currentLookAtRef = useRef(new THREE.Vector3(0, 0, 0));

  /**
   * Fly camera to a new position with smooth animation
   */
  const flyTo = useCallback(
    (position: THREE.Vector3, lookAt: THREE.Vector3) => {
      // Store start state
      startPositionRef.current = camera.position.clone();
      startLookAtRef.current = currentLookAtRef.current.clone();

      // Set target
      targetRef.current = position.clone();
      lookAtRef.current = lookAt.clone();

      // Reset progress and start animation
      progressRef.current = 0;
      setIsFlying(true);
      setCurrentTarget({ position: position.clone(), lookAt: lookAt.clone() });
    },
    [camera]
  );

  /**
   * Return camera to central hub
   */
  const returnToHub = useCallback(() => {
    flyTo(HUB_CAMERA_POSITION.clone(), HUB_LOOK_AT.clone());
  }, [flyTo]);

  /**
   * Animation frame - interpolate camera position and rotation
   */
  useFrame((_, delta) => {
    if (!isFlying || !targetRef.current || !lookAtRef.current) return;
    if (!startPositionRef.current || !startLookAtRef.current) return;

    // Advance progress
    progressRef.current += delta * FLIGHT_SPEED;
    const rawProgress = Math.min(progressRef.current, 1);
    const easedProgress = easeInOutCubic(rawProgress);

    // Interpolate position
    camera.position.lerpVectors(
      startPositionRef.current,
      targetRef.current,
      easedProgress
    );

    // Interpolate look-at for smooth rotation
    currentLookAtRef.current.lerpVectors(
      startLookAtRef.current,
      lookAtRef.current,
      easedProgress
    );
    camera.lookAt(currentLookAtRef.current);

    // Check if animation complete
    if (rawProgress >= 1) {
      setIsFlying(false);
      // Ensure final position is exact
      camera.position.copy(targetRef.current);
      camera.lookAt(lookAtRef.current);
      currentLookAtRef.current.copy(lookAtRef.current);
    }
  });

  return {
    flyTo,
    returnToHub,
    isFlying,
    currentTarget,
  };
}

/**
 * Calculate optimal camera position for viewing a target
 */
export function getViewingPosition(
  targetPosition: THREE.Vector3,
  distance: number = 5,
  height: number = 2
): THREE.Vector3 {
  // Position camera at an angle from the target
  const angle = Math.atan2(targetPosition.x, targetPosition.z) + Math.PI * 0.2;
  return new THREE.Vector3(
    targetPosition.x + Math.sin(angle) * distance,
    targetPosition.y + height,
    targetPosition.z + Math.cos(angle) * distance
  );
}

/**
 * Hub camera constants for external use
 */
export const WORLD_SPACE_CAMERA = {
  hubPosition: HUB_CAMERA_POSITION,
  hubLookAt: HUB_LOOK_AT,
  flightSpeed: FLIGHT_SPEED,
};
