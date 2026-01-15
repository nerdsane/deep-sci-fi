/**
 * MountPoint - Renders agent-created UI components at specific locations
 *
 * This component acts as a placeholder where agents can inject dynamic UI.
 * Multiple components can be mounted at the same target.
 *
 * Phase 0 Migration: Supports both legacy ComponentSpec and json-render tree format
 */

import type { ComponentSpec } from './types';
import type { JsonRenderTree } from '../../agent-bus/types';
import { DynamicRenderer } from './DynamicRenderer';
import { AgentUIRenderer } from '../../lib/agent-ui/renderer';

interface MountPointProps {
  /**
   * Target identifier for this mount point.
   * Examples: "story_header", "story_segment_abc123", "world_overview"
   */
  target: string;

  /**
   * Agent UI components for this target (from agentUI state)
   *
   * Phase 0 Migration: Supports both formats
   * - spec: Legacy ComponentSpec format (backwards compatibility)
   * - tree: New json-render format (preferred)
   */
  components: Array<{
    componentId: string;
    spec?: ComponentSpec; // Legacy format
    tree?: JsonRenderTree; // New json-render format
  }>;

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
      {components.map(({ componentId, spec, tree }) => (
        <div key={componentId} className="mount-point-item">
          {/* Phase 0 Migration: Prefer tree format, fallback to spec */}
          {tree ? (
            <AgentUIRenderer
              tree={tree}
              onAction={(action: string, params: any) => {
                // Convert json-render action to interaction message
                onInteraction(componentId, action, params);
              }}
            />
          ) : spec ? (
            <DynamicRenderer
              spec={spec}
              onInteraction={onInteraction}
            />
          ) : null}
        </div>
      ))}
    </div>
  );
}
