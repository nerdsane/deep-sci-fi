/**
 * Immersive World Space - TypeScript Types
 *
 * Types for the 3D immersive world exploration experience.
 */

import type { World, Story, Rule, Element } from '@/types/dsf';
import * as THREE from 'three';

// ============================================================================
// Main Component Props
// ============================================================================

export interface ImmersiveWorldSpaceProps {
  world: World;
  stories: Story[];
  onSelectStory: (story: Story) => void;
  onExploreElement?: (elementId: string, elementType: string) => void;
  onBack: () => void;
}

export interface WorldSpaceSceneProps {
  world: World;
  stories: Story[];
  selectedNode: string | null;
  onSelectNode: (nodeId: string | null) => void;
  onSelectStory: (story: Story) => void;
  onExploreElement?: (elementId: string, elementType: string) => void;
}

// ============================================================================
// Central Hub
// ============================================================================

export interface CentralHubProps {
  rules: Rule[];
  onRuleClick?: (rule: Rule) => void;
  onRuleHover?: (rule: Rule | null) => void;
}

export interface RulePanelProps {
  rule: Rule;
  position: THREE.Vector3;
  index: number;
  isHovered: boolean;
  onClick?: () => void;
  onHover?: (hovered: boolean) => void;
}

// ============================================================================
// Location Nodes
// ============================================================================

export interface LocationNodeProps {
  location: WorldLocation;
  position: [number, number, number];
  isSelected: boolean;
  onSelect: (locationId: string) => void;
  onFlyTo: (position: THREE.Vector3, lookAt: THREE.Vector3) => void;
}

export interface WorldLocation {
  id: string;
  name: string;
  description: string;
  type: 'city' | 'facility' | 'landmark' | 'natural' | 'unknown';
  icon?: string;
  discovered?: boolean;
  locked?: boolean;
}

// ============================================================================
// Technology Artifacts
// ============================================================================

export interface TechnologyArtifact3DProps {
  tech: WorldTechnology;
  position: [number, number, number];
  onInspect: (tech: WorldTechnology) => void;
}

export interface WorldTechnology {
  id: string;
  name: string;
  description: string;
  category?: 'device' | 'vehicle' | 'weapon' | 'infrastructure' | 'material' | 'technology';
  specifications?: TechSpecification[];
  discovered?: boolean;
  locked?: boolean;
}

export interface TechSpecification {
  name: string;
  value: string | number;
  unit?: string;
}

// ============================================================================
// Story Portals
// ============================================================================

export interface StoryPortal3DProps {
  story: Story;
  position: [number, number, number];
  onEnter: (story: Story) => void;
}

// ============================================================================
// Environment
// ============================================================================

export interface WorldEnvironmentProps {
  coverImage?: string;
  mood?: 'dark' | 'mysterious' | 'hopeful' | 'tense' | 'neutral';
}

// ============================================================================
// Connection Streams
// ============================================================================

export interface ConnectionStreamProps {
  from: [number, number, number];
  to: [number, number, number];
  type?: 'route' | 'road' | 'connection';
  intensity?: number;
}

// ============================================================================
// Camera Navigation
// ============================================================================

export interface CameraTarget {
  position: THREE.Vector3;
  lookAt: THREE.Vector3;
}

export interface UseWorldSpaceCameraReturn {
  flyTo: (position: THREE.Vector3, lookAt: THREE.Vector3) => void;
  returnToHub: () => void;
  isFlying: boolean;
  currentTarget: CameraTarget | null;
}

// ============================================================================
// Inspection Modal
// ============================================================================

export interface InspectionModalProps {
  nodeId: string;
  nodeType: 'location' | 'technology' | 'rule';
  world: World;
  onClose: () => void;
}

// ============================================================================
// Spatial Layout
// ============================================================================

export interface SpatialLayout {
  hub: THREE.Vector3;
  locations: Map<string, THREE.Vector3>;
  technologies: Map<string, THREE.Vector3>;
  portals: Map<string, THREE.Vector3>;
}

// ============================================================================
// Utility Types
// ============================================================================

export type Position3D = [number, number, number];

export interface HoverState {
  nodeId: string | null;
  nodeType: 'location' | 'technology' | 'rule' | 'portal' | null;
}
