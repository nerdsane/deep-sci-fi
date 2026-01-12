'use client';

import { Suspense, useRef, useState, useCallback, useEffect, useMemo } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import type { World } from '@/types/dsf';
import { WorldOrb } from './WorldOrb';
import { StarField, NebulaClouds } from './StarField';
import { WarpTunnel } from './WarpTunnel';
import { AgentPresence } from './AgentPresence';
import { useObservatoryCamera, type CameraState } from './useObservatoryCamera';
import './observatory.css';

// Track if we're on the client - R3F requires this for proper initialization
const useIsClient = () => {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);
  return isClient;
};

export interface ObservatoryProps {
  worlds: World[];
  onSelectWorld: (world: World) => void;
  onHoverWorld?: (world: World | null) => void;
}

// Inner scene component that has access to Three.js context
function ObservatoryScene({
  worlds,
  onSelectWorld,
  onHoverWorld,
  cameraState,
  hoverTarget,
  onWorldClick,
}: {
  worlds: World[];
  onSelectWorld: (world: World) => void;
  onHoverWorld?: (world: World | null, position?: THREE.Vector3) => void;
  cameraState: CameraState;
  hoverTarget: { position: THREE.Vector3; lookAt: THREE.Vector3 } | null;
  onWorldClick: (world: World, position: THREE.Vector3) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { camera } = useThree();
  const startPositionRef = useRef<THREE.Vector3 | null>(null);
  const defaultCameraPos = useRef(new THREE.Vector3(0, 2, 15));

  // Animate camera based on state with easing
  useFrame((state, delta) => {
    if (cameraState.target && cameraState.isTransitioning) {
      // Store start position on first frame
      if (!startPositionRef.current) {
        startPositionRef.current = camera.position.clone();
      }

      // Use progress for smoother animation with easing
      const progress = cameraState.progress;
      const easedProgress = easeInOutQuart(progress);

      // Interpolate position based on eased progress
      if (startPositionRef.current) {
        camera.position.lerpVectors(
          startPositionRef.current,
          cameraState.target,
          easedProgress
        );
      }

      if (cameraState.lookAt) {
        camera.lookAt(cameraState.lookAt);
      }

      // Add slight FOV change during warp for zoom effect
      const baseFov = 60;
      const warpFovBoost = cameraState.warpIntensity * 15;
      (camera as THREE.PerspectiveCamera).fov = baseFov + warpFovBoost;
      (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
    } else {
      // Reset start position when not transitioning
      startPositionRef.current = null;

      // Handle hover zoom (gentle, non-blocking)
      if (hoverTarget) {
        // Gently move camera toward hover target
        camera.position.lerp(hoverTarget.position, delta * 2);
        // Gently look toward the hovered world
        const currentLookAt = new THREE.Vector3(0, 0, 0);
        currentLookAt.lerp(hoverTarget.lookAt, delta * 3);
      } else {
        // Return to default position when not hovering
        camera.position.lerp(defaultCameraPos.current, delta * 1.5);
      }
    }
  });

  // Easing function for smooth animation
  function easeInOutQuart(t: number): number {
    return t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2;
  }

  // Calculate world positions in a constellation pattern
  const getWorldPosition = useCallback((index: number, total: number): [number, number, number] => {
    if (total === 1) return [0, 0, 0];

    // Spiral galaxy pattern
    const angle = (index / total) * Math.PI * 4; // Two full rotations
    const radius = 3 + (index / total) * 5; // Expanding radius
    const height = Math.sin(index * 0.5) * 2; // Vertical variation

    return [
      Math.cos(angle) * radius,
      height,
      Math.sin(angle) * radius,
    ];
  }, []);

  return (
    <>
      {/* Soft ambient lighting */}
      <ambientLight intensity={0.15} color="#8080ff" />

      {/* Soft point lights for atmospheric glow */}
      <pointLight position={[0, 10, 15]} intensity={0.5} color="#ffffff" distance={50} decay={2} />
      <pointLight position={[-10, -5, 10]} intensity={0.3} color="#00ffcc" distance={40} decay={2} />
      <pointLight position={[10, 5, -10]} intensity={0.2} color="#ff88ff" distance={40} decay={2} />

      {/* Atmospheric fog for depth - reduced during warp */}
      <fog attach="fog" args={['#000011', 30 + cameraState.warpIntensity * 50, 120]} />

      {/* Background nebula clouds - fade during warp */}
      {cameraState.warpIntensity < 0.5 && <NebulaClouds />}

      {/* Soft star field - fade during warp */}
      <StarField count={2500} radius={80} />

      {/* Warp tunnel effect - visible during transition */}
      <WarpTunnel
        intensity={cameraState.warpIntensity}
        active={cameraState.isTransitioning}
      />

      {/* World orbs - fade during warp */}
      <group ref={groupRef}>
        {worlds.map((world, index) => {
          const position = getWorldPosition(index, worlds.length);
          return (
            <WorldOrb
              key={(world as any).id || index}
              world={world}
              position={position}
              onClick={(worldObj, pos) => onWorldClick(worldObj, pos)}
              onHover={(worldObj) => {
                if (worldObj) {
                  onHoverWorld?.(worldObj, new THREE.Vector3(...position));
                } else {
                  onHoverWorld?.(null);
                }
              }}
            />
          );
        })}
      </group>

      {/* Agent presence - AI glyph floating in space */}
      {!cameraState.isTransitioning && (
        <AgentPresence
          position={[-8, 3, -5]}
          isThinking={false}
        />
      )}
    </>
  );
}

// Loading fallback
function LoadingFallback() {
  return (
    <mesh>
      <sphereGeometry args={[0.5, 16, 16]} />
      <meshBasicMaterial color="#00ffcc" wireframe />
    </mesh>
  );
}

export function Observatory({ worlds, onSelectWorld, onHoverWorld }: ObservatoryProps) {
  const [hoveredWorld, setHoveredWorld] = useState<World | null>(null);
  const [hoveredPosition, setHoveredPosition] = useState<THREE.Vector3 | null>(null);
  const { cameraState, hoverTarget, zoomToWorld, resetCamera, zoomToHover } = useObservatoryCamera();
  const [isEntering, setIsEntering] = useState(false);
  const isClient = useIsClient();

  // World positions for hover lookup
  const worldPositions = useMemo(() => {
    return worlds.map((_, index) => {
      const total = worlds.length;
      if (total === 1) return new THREE.Vector3(0, 0, 0);
      const angle = (index / total) * Math.PI * 4;
      const radius = 3 + (index / total) * 5;
      const height = Math.sin(index * 0.5) * 2;
      return new THREE.Vector3(
        Math.cos(angle) * radius,
        height,
        Math.sin(angle) * radius
      );
    });
  }, [worlds.length]);

  // Handle world click - zoom in with warp effect then navigate
  const handleWorldClick = useCallback((world: World, position: THREE.Vector3) => {
    if (isEntering) return;

    setIsEntering(true);

    // Calculate camera target - fly INTO the world (past it slightly)
    const direction = position.clone().normalize();
    const targetPosition = position.clone().add(direction.multiplyScalar(0.5)); // Go into/past the world

    // Start the warp animation with onComplete callback
    zoomToWorld(targetPosition, position, () => {
      // Animation complete - navigate to world
      onSelectWorld(world);
      setIsEntering(false);
      resetCamera();
    });
  }, [isEntering, zoomToWorld, onSelectWorld, resetCamera]);

  // Handle hover with camera zoom
  const handleHover = useCallback((world: World | null, position?: THREE.Vector3) => {
    setHoveredWorld(world);
    setHoveredPosition(position || null);
    onHoverWorld?.(world);

    // Trigger camera zoom toward hovered world
    if (world && position && !isEntering) {
      zoomToHover(position);
    } else {
      zoomToHover(null);
    }
  }, [onHoverWorld, zoomToHover, isEntering]);

  // Get world name for hover display
  const getWorldName = (world: World): string => {
    if ((world as any).name) return (world as any).name;
    const premise = world.foundation?.core_premise || 'Untitled World';
    return premise.split(' ').slice(0, 4).join(' ') + '...';
  };

  // Only render Canvas on client side - R3F requires this
  if (!isClient) {
    return (
      <div className="observatory">
        <div className="loading-screen">
          <div className="loading-spinner"></div>
          <p>Initializing 3D Observatory...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="observatory">
      {/* 3D Canvas */}
      <Canvas
        className="observatory__canvas"
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
        }}
        dpr={[1, 2]}
        frameloop="always"
      >
        {/* Deep space blue-black background */}
        <color attach="background" args={['#030308']} />

        <PerspectiveCamera
          makeDefault
          position={[0, 2, 15]}
          fov={60}
          near={0.1}
          far={200}
        />

        <Suspense fallback={<LoadingFallback />}>
          <ObservatoryScene
            worlds={worlds}
            onSelectWorld={onSelectWorld}
            onHoverWorld={handleHover}
            cameraState={cameraState}
            hoverTarget={hoverTarget}
            onWorldClick={handleWorldClick}
          />
        </Suspense>

        {/* Orbit controls for exploration (disabled during transition) */}
        <OrbitControls
          enabled={!cameraState.isTransitioning && !isEntering}
          enablePan={false}
          enableZoom={true}
          minDistance={5}
          maxDistance={30}
          autoRotate={!hoveredWorld}
          autoRotateSpeed={0.3}
        />

      </Canvas>

      {/* Hover info overlay */}
      {hoveredWorld && !isEntering && (
        <div className="observatory__hover-info">
          <h3 className="observatory__world-name">{getWorldName(hoveredWorld)}</h3>
          <p className="observatory__world-premise">
            {hoveredWorld.foundation?.core_premise?.slice(0, 100)}...
          </p>
          <span className="observatory__hint">Click to enter</span>
        </div>
      )}

      {/* Entering transition overlay with warp effect */}
      {isEntering && (
        <div className="observatory__entering">
          <div className="observatory__entering-vignette" />
          <div className="observatory__entering-text">
            {cameraState.phase === 'approach' && 'Initiating...'}
            {cameraState.phase === 'warp' && 'Entering...'}
            {cameraState.phase === 'arrive' && 'Arriving...'}
          </div>
        </div>
      )}

      {/* Empty state */}
      {worlds.length === 0 && (
        <div className="observatory__empty">
          <div className="observatory__empty-icon">◇</div>
          <h3 className="observatory__empty-title">The Observatory Awaits</h3>
          <p className="observatory__empty-text">
            Create your first world to see it appear as a star in this space.
          </p>
        </div>
      )}
    </div>
  );
}
