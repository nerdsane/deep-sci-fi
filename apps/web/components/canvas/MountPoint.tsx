/**
 * MountPoint - Renders agent-created UI components at specific locations
 *
 * This component acts as a placeholder where agents can inject dynamic UI.
 * Multiple components can be mounted at the same target.
 */

import type { ComponentSpec } from './types';
import { DynamicRenderer } from './DynamicRenderer';

interface MountPointProps {
  /**
   * Target identifier for this mount point.
   * Examples: "story_header", "story_segment_abc123", "world_overview"
   */
  target: string;

  /**
   * Agent UI components for this target (from agentUI state)
   */
  components: Array<{ componentId: string; spec: ComponentSpec }>;

  /**
   * Callback for user interactions
   */
  onInteraction: (componentId: string, interactionType: string, data: any, target?: string) => void;

  /**
   * Optional CSS class for styling the mount point container
   */
  className?: string;

  /**
   * Layout direction for multiple components
   */
  layout?: 'vertical' | 'horizontal';

  /**
   * Spacing between components (px)
   */
  spacing?: number;
}

/**
 * MountPoint component renders agent-created UI at a specific location.
 *
 * Usage:
 * ```tsx
 * <MountPoint
 *   target="story_segment_123"
 *   components={agentUIForTarget}
 *   onInteraction={handleInteraction}
 * />
 * ```
 */
export function MountPoint({
  target,
  components,
  onInteraction,
  className = '',
  layout = 'vertical',
  spacing = 16,
}: MountPointProps) {
  if (components.length === 0) {
    return null; // No components to render
  }

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: layout === 'vertical' ? 'column' : 'row',
    gap: `${spacing}px`,
    margin: `${spacing}px 0`,
  };

  return (
    <div
      className={`mount-point mount-point-${target} ${className}`}
      data-target={target}
      style={containerStyle}
    >
      {components.map(({ componentId, spec }) => (
        <div key={componentId} className="mount-point-item">
          <DynamicRenderer
            spec={spec}
            onInteraction={onInteraction}
          />
        </div>
      ))}
    </div>
  );
}
