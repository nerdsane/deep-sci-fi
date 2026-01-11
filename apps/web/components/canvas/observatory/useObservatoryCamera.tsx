'use client';

import { useState, useCallback } from 'react';
import * as THREE from 'three';

export interface CameraState {
  target: THREE.Vector3 | null;
  lookAt: THREE.Vector3 | null;
  isTransitioning: boolean;
}

const DEFAULT_POSITION = new THREE.Vector3(0, 2, 15);
const DEFAULT_LOOK_AT = new THREE.Vector3(0, 0, 0);

export function useObservatoryCamera() {
  const [cameraState, setCameraState] = useState<CameraState>({
    target: null,
    lookAt: null,
    isTransitioning: false,
  });

  // Zoom camera toward a world
  const zoomToWorld = useCallback((targetPosition: THREE.Vector3, lookAtPosition: THREE.Vector3) => {
    setCameraState({
      target: targetPosition,
      lookAt: lookAtPosition,
      isTransitioning: true,
    });
  }, []);

  // Reset camera to default position
  const resetCamera = useCallback(() => {
    setCameraState({
      target: DEFAULT_POSITION.clone(),
      lookAt: DEFAULT_LOOK_AT.clone(),
      isTransitioning: true,
    });

    // Clear transition after animation completes
    setTimeout(() => {
      setCameraState({
        target: null,
        lookAt: null,
        isTransitioning: false,
      });
    }, 1000);
  }, []);

  // Pan camera to a position without zooming
  const panTo = useCallback((position: THREE.Vector3) => {
    setCameraState({
      target: position,
      lookAt: DEFAULT_LOOK_AT.clone(),
      isTransitioning: true,
    });
  }, []);

  return {
    cameraState,
    zoomToWorld,
    resetCamera,
    panTo,
  };
}
