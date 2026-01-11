'use client';

import { Suspense, useRef, useState, useCallback, useEffect } from 'react';
import { Canvas, useThree, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import { EffectComposer, Bloom, Noise, Vignette } from '@react-three/postprocessing';
import { BlendFunction } from 'postprocessing';
import * as THREE from 'three';
import type { World } from '@/types/dsf';
import { WorldOrb } from './WorldOrb';
import { StarField, NebulaClouds } from './StarField';
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
  onWorldClick,
}: {
  worlds: World[];
  onSelectWorld: (world: World) => void;
  onHoverWorld?: (world: World | null) => void;
  cameraState: CameraState;
  onWorldClick: (world: World, position: THREE.Vector3) => void;
}) {
  const groupRef = useRef<THREE.Group>(null);
  const { camera } = useThree();

  // Animate camera based on state
  useFrame((state, delta) => {
    if (cameraState.target && cameraState.isTransitioning) {
      // Smooth camera movement toward target
      camera.position.lerp(cameraState.target, delta * 2);

      if (cameraState.lookAt) {
        const currentLookAt = new THREE.Vector3();
        camera.getWorldDirection(currentLookAt);
        currentLookAt.add(camera.position);
        currentLookAt.lerp(cameraState.lookAt, delta * 3);
        camera.lookAt(currentLookAt);
      }
    }
  });

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

      {/* Atmospheric fog for depth */}
      <fog attach="fog" args={['#000011', 30, 120]} />

      {/* Background nebula clouds */}
      <NebulaClouds />

      {/* Soft star field */}
      <StarField count={2500} radius={80} />

      {/* World orbs */}
      <group ref={groupRef}>
        {worlds.map((world, index) => {
          const position = getWorldPosition(index, worlds.length);
          return (
            <WorldOrb
              key={(world as any).id || index}
              world={world}
              position={position}
              onClick={(worldObj, pos) => onWorldClick(worldObj, pos)}
              onHover={onHoverWorld}
            />
          );
        })}
      </group>
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
  const { cameraState, zoomToWorld, resetCamera } = useObservatoryCamera();
  const [isEntering, setIsEntering] = useState(false);
  const isClient = useIsClient();

  // Handle world click - zoom in then navigate
  const handleWorldClick = useCallback((world: World, position: THREE.Vector3) => {
    if (isEntering) return;

    setIsEntering(true);

    // Calculate camera position closer to the world
    const direction = position.clone().normalize();
    const targetPosition = position.clone().sub(direction.multiplyScalar(2));

    zoomToWorld(targetPosition, position);

    // After zoom animation, navigate to world
    setTimeout(() => {
      onSelectWorld(world);
      setIsEntering(false);
      resetCamera();
    }, 1200);
  }, [isEntering, zoomToWorld, onSelectWorld, resetCamera]);

  // Handle hover
  const handleHover = useCallback((world: World | null) => {
    setHoveredWorld(world);
    onHoverWorld?.(world);
  }, [onHoverWorld]);

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

        {/* Post-processing for soft, nebula-like glow */}
        <EffectComposer>
          <Bloom
            intensity={1.5}
            luminanceThreshold={0.1}
            luminanceSmoothing={0.9}
            mipmapBlur={true}
            radius={0.8}
          />
          <Noise
            opacity={0.02}
            blendFunction={BlendFunction.SOFT_LIGHT}
          />
          <Vignette
            offset={0.3}
            darkness={0.6}
            blendFunction={BlendFunction.NORMAL}
          />
        </EffectComposer>
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

      {/* Entering transition overlay */}
      {isEntering && (
        <div className="observatory__entering">
          <div className="observatory__entering-text">Entering world...</div>
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
