/**
 * ImmersiveWorldSpace - Main 3D World Exploration Component
 *
 * The immersive world experience where users explore a world
 * from within, flying between locations, examining technologies,
 * and entering story portals.
 */

'use client';

import { Suspense, useState, useCallback, useEffect, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import * as THREE from 'three';
import type { World, Story, Rule } from '@/types/dsf';
import type {
  ImmersiveWorldSpaceProps,
  WorldSpaceSceneProps,
  WorldLocation,
  WorldTechnology,
} from './types';
import { WorldEnvironment } from './WorldEnvironment';
import { CentralHub } from './CentralHub';
import { LocationNode } from './LocationNode';
import { TechnologyArtifact3D } from './TechnologyArtifact3D';
import { StoryPortal3D } from './StoryPortal3D';
import { useWorldSpaceCamera, WORLD_SPACE_CAMERA } from './useWorldSpaceCamera';
import './immersive-world-space.css';

// Track if we're on the client - R3F requires this
const useIsClient = () => {
  const [isClient, setIsClient] = useState(false);
  useEffect(() => {
    setIsClient(true);
  }, []);
  return isClient;
};

// ============================================================================
// Layout Calculation
// ============================================================================

/**
 * Calculate spatial positions for all elements
 */
function calculateLayout(
  locations: WorldLocation[],
  technologies: WorldTechnology[],
  stories: Story[]
) {
  // Locations arranged in an arc in front of the hub
  const locationPositions: Map<string, [number, number, number]> = new Map();
  const locRadius = 12;
  const locArc = Math.PI * 0.6;
  const locStartAngle = -locArc / 2;

  locations.forEach((loc, i) => {
    const angle = locStartAngle + (locArc / (locations.length + 1)) * (i + 1);
    locationPositions.set(loc.id, [
      Math.sin(angle) * locRadius,
      1 + (i % 2) * 1.5, // Alternate heights
      Math.cos(angle) * locRadius - 8,
    ]);
  });

  // Technologies floating around the hub
  const techPositions: Map<string, [number, number, number]> = new Map();
  const techRadius = 8;

  technologies.forEach((tech, i) => {
    const angle = ((Math.PI * 2) / technologies.length) * i - Math.PI / 2;
    const height = 2 + Math.sin(i * 1.5) * 1.5;
    techPositions.set(tech.id, [
      Math.sin(angle) * techRadius,
      height,
      Math.cos(angle) * techRadius * 0.6,
    ]);
  });

  // Story portals at the sides
  const portalPositions: Map<string, [number, number, number]> = new Map();
  const portalSpacing = 5;

  stories.forEach((story, i) => {
    const side = i % 2 === 0 ? -1 : 1;
    const row = Math.floor(i / 2);
    portalPositions.set(story.id, [
      side * 15,
      2 + row * 0.5,
      -5 - row * 4,
    ]);
  });

  return { locationPositions, techPositions, portalPositions };
}

// ============================================================================
// Inner Scene Component
// ============================================================================

function WorldSpaceScene({
  world,
  stories,
  selectedNode,
  onSelectNode,
  onSelectStory,
  onExploreElement,
}: WorldSpaceSceneProps) {
  const { flyTo, returnToHub, isFlying } = useWorldSpaceCamera();

  // Extract and transform data from world
  const foundation = world?.foundation || { core_premise: 'Unknown World', rules: [] };
  const surface = world?.surface || { visible_elements: [] };
  const visibleElements = Array.isArray(surface.visible_elements)
    ? surface.visible_elements
    : [];

  // Transform elements to typed data
  const locations: WorldLocation[] = useMemo(
    () =>
      visibleElements
        .filter((e) => e.type === 'location')
        .map((e) => ({
          id: e.id,
          name: e.name || e.id,
          description: e.description || '',
          type: (e.properties?.locationType as WorldLocation['type']) || 'unknown',
          icon: e.properties?.icon as string | undefined,
          discovered: e.properties?.discovered !== false,
          locked: e.properties?.locked === true,
        })),
    [visibleElements]
  );

  const technologies: WorldTechnology[] = useMemo(
    () =>
      visibleElements
        .filter((e) => e.type === 'technology')
        .map((e) => ({
          id: e.id,
          name: e.name || e.id,
          description: e.description || '',
          category: (e.properties?.category as WorldTechnology['category']) || 'technology',
          specifications: e.properties?.specifications as WorldTechnology['specifications'],
          discovered: e.properties?.discovered !== false,
          locked: e.properties?.locked === true,
        })),
    [visibleElements]
  );

  // Calculate spatial layout
  const layout = useMemo(
    () => calculateLayout(locations, technologies, stories),
    [locations, technologies, stories]
  );

  // Handlers
  const handleLocationSelect = useCallback(
    (locationId: string) => {
      onSelectNode(locationId);
      onExploreElement?.(locationId, 'location');
    },
    [onSelectNode, onExploreElement]
  );

  const handleTechInspect = useCallback(
    (tech: WorldTechnology) => {
      onSelectNode(tech.id);
      onExploreElement?.(tech.id, 'technology');
    },
    [onSelectNode, onExploreElement]
  );

  const handleRuleClick = useCallback(
    (rule: Rule) => {
      onSelectNode(rule.id);
      onExploreElement?.(rule.id, 'rule');
    },
    [onSelectNode, onExploreElement]
  );

  const handleFlyTo = useCallback(
    (position: THREE.Vector3, lookAt: THREE.Vector3) => {
      flyTo(position, lookAt);
    },
    [flyTo]
  );

  return (
    <>
      {/* Environment (fog, lights, stars) */}
      <WorldEnvironment mood="neutral" />

      {/* Central hub with foundation rules */}
      <CentralHub rules={foundation.rules || []} onRuleClick={handleRuleClick} />

      {/* Location nodes */}
      {locations.map((location) => {
        const pos = layout.locationPositions.get(location.id);
        if (!pos) return null;
        return (
          <LocationNode
            key={location.id}
            location={location}
            position={pos}
            isSelected={selectedNode === location.id}
            onSelect={handleLocationSelect}
            onFlyTo={handleFlyTo}
          />
        );
      })}

      {/* Technology artifacts */}
      {technologies.map((tech) => {
        const pos = layout.techPositions.get(tech.id);
        if (!pos) return null;
        return (
          <TechnologyArtifact3D
            key={tech.id}
            tech={tech}
            position={pos}
            onInspect={handleTechInspect}
          />
        );
      })}

      {/* Story portals */}
      {stories.map((story) => {
        const pos = layout.portalPositions.get(story.id);
        if (!pos) return null;
        return (
          <StoryPortal3D
            key={story.id}
            story={story}
            position={pos}
            onEnter={onSelectStory}
          />
        );
      })}

      {/* Orbit controls for camera - disabled during flight */}
      <OrbitControls
        enabled={!isFlying}
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        minDistance={5}
        maxDistance={40}
        minPolarAngle={Math.PI * 0.1}
        maxPolarAngle={Math.PI * 0.7}
        target={[0, 0, 0]}
      />
    </>
  );
}

// ============================================================================
// Loading Screen
// ============================================================================

function LoadingScreen() {
  return (
    <div className="immersive-loading">
      <div className="immersive-loading__content">
        <div className="immersive-loading__spinner" />
        <div className="immersive-loading__text">Entering World Space...</div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ImmersiveWorldSpace({
  world,
  stories,
  onSelectStory,
  onExploreElement,
  onBack,
}: ImmersiveWorldSpaceProps) {
  const isClient = useIsClient();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Derive world title
  const worldTitle = useMemo(() => {
    if ((world as any).name) return (world as any).name;
    const premise = world?.foundation?.core_premise || 'Unknown World';
    return premise.split(' ').slice(0, 4).join(' ') + '...';
  }, [world]);

  // Don't render Canvas on server
  if (!isClient) {
    return <LoadingScreen />;
  }

  return (
    <div className="immersive-world-space">
      {/* 3D Canvas */}
      <Canvas
        camera={{
          position: [
            WORLD_SPACE_CAMERA.hubPosition.x,
            WORLD_SPACE_CAMERA.hubPosition.y,
            WORLD_SPACE_CAMERA.hubPosition.z,
          ],
          fov: 60,
          near: 0.1,
          far: 200,
        }}
        gl={{
          antialias: true,
          alpha: false,
          powerPreference: 'high-performance',
        }}
      >
        <Suspense fallback={null}>
          <WorldSpaceScene
            world={world}
            stories={stories}
            selectedNode={selectedNode}
            onSelectNode={setSelectedNode}
            onSelectStory={onSelectStory}
            onExploreElement={onExploreElement}
          />
        </Suspense>
      </Canvas>

      {/* Header overlay */}
      <div className="immersive-header">
        <button className="immersive-back" onClick={onBack}>
          <span className="immersive-back__icon">←</span>
          <span className="immersive-back__text">Observatory</span>
        </button>

        <div className="immersive-title">
          <span className="immersive-title__label">EXPLORING</span>
          <h1 className="immersive-title__name">{worldTitle}</h1>
        </div>

        <div className="immersive-controls">
          <button
            className="immersive-control"
            onClick={() => setSelectedNode(null)}
            title="Return to hub"
          >
            ⌂
          </button>
        </div>
      </div>

      {/* Instructions overlay (shown briefly on first visit) */}
      <div className="immersive-instructions">
        <div className="immersive-instructions__item">
          <span className="immersive-instructions__key">Click</span>
          <span className="immersive-instructions__desc">locations to fly there</span>
        </div>
        <div className="immersive-instructions__item">
          <span className="immersive-instructions__key">Drag</span>
          <span className="immersive-instructions__desc">to look around</span>
        </div>
        <div className="immersive-instructions__item">
          <span className="immersive-instructions__key">Scroll</span>
          <span className="immersive-instructions__desc">to zoom</span>
        </div>
      </div>
    </div>
  );
}

export default ImmersiveWorldSpace;
