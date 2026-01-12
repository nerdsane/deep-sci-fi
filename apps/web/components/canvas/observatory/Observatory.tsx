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
import { FloatingSuggestions, useSuggestions, type Suggestion } from './FloatingSuggestions';
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

// Agent position constant
const AGENT_POSITION: [number, number, number] = [-8, 3, -5];

// Inner scene component that has access to Three.js context
function ObservatoryScene({
  worlds,
  onSelectWorld,
  onHoverWorld,
  cameraState,
  hoverTarget,
  onWorldClick,
  suggestions,
  isAgentThinking,
  onSuggestionClick,
  onSuggestionDismiss,
}: {
  worlds: World[];
  onSelectWorld: (world: World) => void;
  onHoverWorld?: (world: World | null, position?: THREE.Vector3) => void;
  cameraState: CameraState;
  hoverTarget: { position: THREE.Vector3; lookAt: THREE.Vector3 } | null;
  onWorldClick: (world: World, position: THREE.Vector3) => void;
  suggestions: Suggestion[];
  isAgentThinking: boolean;
  onSuggestionClick?: (suggestion: Suggestion) => void;
  onSuggestionDismiss?: (suggestion: Suggestion) => void;
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
          position={AGENT_POSITION}
          isThinking={isAgentThinking}
        />
      )}

      {/* Floating suggestions from the agent */}
      {!cameraState.isTransitioning && suggestions.length > 0 && (
        <FloatingSuggestions
          suggestions={suggestions}
          agentPosition={AGENT_POSITION}
          onSuggestionClick={onSuggestionClick}
          onDismiss={onSuggestionDismiss}
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

  // Suggestion system
  const {
    suggestions,
    isThinking: isAgentThinking,
    addSuggestion,
    removeSuggestion,
    generateSuggestion,
  } = useSuggestions();

  // Track user behavior for contextual prompts
  const hoverTimerRef = useRef<NodeJS.Timeout | null>(null);
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const hasShownWelcome = useRef(false);

  // Welcome suggestion on first load
  useEffect(() => {
    if (isClient && !hasShownWelcome.current) {
      hasShownWelcome.current = true;
      const timer = setTimeout(() => {
        if (worlds.length === 0) {
          generateSuggestion('explore', { worldCount: 0 });
        } else {
          addSuggestion({
            text: 'Hover over a world to peek inside, or click to enter.',
            type: 'explore',
            priority: 'low',
          });
        }
      }, 2000); // Show after 2 seconds
      return () => clearTimeout(timer);
    }
  }, [isClient, worlds.length]);

  // Idle detection - suggest after 15 seconds of no interaction
  useEffect(() => {
    const resetIdleTimer = () => {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
      idleTimerRef.current = setTimeout(() => {
        if (worlds.length > 0 && suggestions.length === 0) {
          generateSuggestion('discover', { worldCount: worlds.length });
        }
      }, 15000);
    };

    // Reset on any interaction
    const handleInteraction = () => resetIdleTimer();
    window.addEventListener('mousemove', handleInteraction);
    window.addEventListener('click', handleInteraction);

    resetIdleTimer();

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      window.removeEventListener('mousemove', handleInteraction);
      window.removeEventListener('click', handleInteraction);
    };
  }, [worlds.length, suggestions.length]);

  // Handle suggestion click
  const handleSuggestionClick = useCallback((suggestion: Suggestion) => {
    removeSuggestion(suggestion.id);

    // Handle different suggestion types
    if (suggestion.type === 'create') {
      // Could trigger world creation modal
      console.log('Create world suggestion clicked');
    } else if (suggestion.type === 'explore' && suggestion.worldId) {
      // Could highlight or zoom to specific world
      console.log('Explore world:', suggestion.worldId);
    }
  }, [removeSuggestion]);

  // Handle suggestion dismiss
  const handleSuggestionDismiss = useCallback((suggestion: Suggestion) => {
    removeSuggestion(suggestion.id);
  }, [removeSuggestion]);

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

  // Handle hover with camera zoom and lingering detection
  const handleHover = useCallback((world: World | null, position?: THREE.Vector3) => {
    setHoveredWorld(world);
    setHoveredPosition(position || null);
    onHoverWorld?.(world);

    // Clear any existing hover timer
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }

    // Trigger camera zoom toward hovered world
    if (world && position && !isEntering) {
      zoomToHover(position);

      // Lingering detection - show suggestion after 3 seconds of hovering
      hoverTimerRef.current = setTimeout(() => {
        if (suggestions.length < 3) { // Don't overwhelm with suggestions
          addSuggestion({
            text: `There's more to discover in this world. Want to dive deeper?`,
            type: 'explore',
            priority: 'medium',
            worldId: (world as any).id,
          });
        }
      }, 3000);
    } else {
      zoomToHover(null);
    }
  }, [onHoverWorld, zoomToHover, isEntering, suggestions.length, addSuggestion]);

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
            suggestions={suggestions}
            isAgentThinking={isAgentThinking}
            onSuggestionClick={handleSuggestionClick}
            onSuggestionDismiss={handleSuggestionDismiss}
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
