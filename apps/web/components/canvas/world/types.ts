/**
 * Phase 3 World Component Types
 *
 * TypeScript interfaces for all interactive world exploration components.
 * These types are used by Agent A to create Zod schemas for the json-render catalog.
 *
 * Components:
 * - InteractiveWorldMap - Locations as visual points on illustrated map
 * - TechArtifact - 3D rotatable objects with inspection
 * - CharacterReveal - Silhouettes → dramatic reveals
 * - StoryPortal - Visual gateways to narratives
 */

// ============================================================================
// Interactive World Map
// ============================================================================

export interface Location {
  id: string;
  name: string;
  description?: string;
  position: [number, number]; // x, y coordinates on map (0-1 normalized)
  type?: 'city' | 'landmark' | 'facility' | 'natural' | 'unknown';
  discovered?: boolean;
  locked?: boolean;
  icon?: string; // Icon name or emoji
  metadata?: Record<string, unknown>;
}

export interface Connection {
  id: string;
  from: string; // Location ID
  to: string; // Location ID
  type?: 'road' | 'route' | 'connection' | 'passage';
  bidirectional?: boolean;
  discovered?: boolean;
  metadata?: Record<string, unknown>;
}

export interface InteractiveWorldMapProps {
  worldId: string;
  locations: Location[];
  connections?: Connection[];
  selectedLocation?: string;
  hoveredLocation?: string;
  mapImageUrl?: string; // Background map illustration
  viewBox?: [number, number, number, number]; // SVG viewBox [x, y, width, height]
  showLabels?: boolean;
  showConnections?: boolean;
  allowZoom?: boolean;
  allowPan?: boolean;
  onLocationClick?: (locationId: string) => void;
  onLocationHover?: (locationId: string | null) => void;
  onConnectionClick?: (connectionId: string) => void;
  style?: React.CSSProperties;
}

// ============================================================================
// Tech Artifact
// ============================================================================

export interface ArtifactSpecification {
  name: string;
  value: string | number;
  unit?: string;
  category?: 'dimensions' | 'performance' | 'materials' | 'capabilities';
}

export interface TechArtifactProps {
  artifactId: string;
  name: string;
  description: string;
  category?: 'technology' | 'device' | 'vehicle' | 'structure' | 'weapon' | 'tool';
  model3dUrl?: string; // URL to 3D model (GLB/GLTF)
  imageUrl?: string; // Fallback 2D image
  specifications?: ArtifactSpecification[];
  discovered?: boolean;
  locked?: boolean;
  rotationSpeed?: number; // Auto-rotation speed (0 = no rotation)
  allowManualRotation?: boolean;
  scale?: number;
  initialRotation?: [number, number, number]; // Euler angles
  onInspect?: () => void;
  onRotate?: (rotation: [number, number, number]) => void;
  style?: React.CSSProperties;
}

// ============================================================================
// Character Reveal
// ============================================================================

export interface CharacterAttribute {
  label: string;
  value: string;
  icon?: string;
  category?: 'physical' | 'mental' | 'social' | 'skill' | 'background';
}

export interface CharacterRevealProps {
  characterId: string;
  name: string;
  title?: string;
  description: string;
  imageUrl?: string; // Character portrait
  silhouetteOnly?: boolean; // Show as silhouette until revealed
  revealed?: boolean;
  attributes?: CharacterAttribute[];
  quote?: string;
  voicelineUrl?: string; // Audio file for character voice
  revealAnimation?: 'fade' | 'slide' | 'dramatic' | 'none';
  revealDelay?: number; // Delay in ms before auto-reveal
  onReveal?: () => void;
  onClick?: () => void;
  style?: React.CSSProperties;
}

// ============================================================================
// Story Portal
// ============================================================================

export interface PortalBadge {
  label: string;
  variant?: 'new' | 'continued' | 'branch' | 'complete';
  color?: string;
}

export interface StoryPortalProps {
  portalId: string;
  storyId: string;
  title: string;
  subtitle?: string;
  description?: string;
  imageUrl?: string; // Portal/story preview image
  worldId?: string;
  badges?: PortalBadge[];
  locked?: boolean;
  progress?: number; // 0-100 percentage
  segmentCount?: number;
  lastAccessedAt?: string; // ISO timestamp
  portalType?: 'gateway' | 'door' | 'rift' | 'entrance';
  glowColor?: string; // Portal glow/accent color
  animated?: boolean;
  onEnter?: () => void;
  onClick?: () => void;
  style?: React.CSSProperties;
}

// ============================================================================
// Atmosphere Components (Week 3)
// ============================================================================

export interface WorldAmbienceProps {
  worldId: string;
  audioUrl?: string; // Ambient audio loop
  volume?: number; // 0-1
  fadeIn?: boolean;
  fadeInDuration?: number; // ms
  autoPlay?: boolean;
  loop?: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  style?: React.CSSProperties;
}

export interface DynamicShaderMoodProps {
  mood: 'mysterious' | 'tense' | 'peaceful' | 'adventurous' | 'melancholic' | 'epic';
  intensity?: number; // 0-1
  colors?: {
    primary?: string;
    secondary?: string;
    accent?: string;
  };
  animated?: boolean;
  animationSpeed?: number;
  blendMode?: 'normal' | 'multiply' | 'screen' | 'overlay';
  style?: React.CSSProperties;
}
