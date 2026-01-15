/**
 * Agent Bus - Message Protocol
 *
 * Bidirectional communication between Agent/CLI and Canvas UI
 *
 * Phase 0 Migration: Adding json-render tree format support
 * - spec: Legacy ComponentSpec format (backwards compatibility)
 * - tree: New json-render tree format (type-safe, validated by Zod)
 */

import type { ComponentSpec } from '../components/canvas/types';

/**
 * json-render tree format
 *
 * Standard format from Vercel's json-render framework
 * See: https://json-render.dev/
 */
export interface JsonRenderTree {
  type: string; // Component name from catalog
  props: Record<string, unknown>; // Validated by Zod schema
  key: string; // Unique identifier for this component instance
  children?: JsonRenderTree[]; // Nested children
}

// ============================================================================
// Message Types
// ============================================================================

/**
 * Agent → Canvas: Create or update UI components
 *
 * Phase 0 Migration:
 * - Supports both `spec` (legacy) and `tree` (json-render) formats
 * - During transition, renderer checks for `tree` first, then falls back to `spec`
 * - Once migration is complete, `spec` field will be removed
 */
export interface CanvasUIMessage {
  type: 'canvas_ui';
  action: 'create' | 'update' | 'remove';
  target: string; // Mount point: 'story_segment_123', 'world_overview', 'floating'
  componentId: string; // Unique ID for this component

  // Legacy format (Phase 0: backwards compatibility)
  spec?: ComponentSpec; // OLD: Custom ComponentSpec format

  // New format (Phase 0: json-render migration)
  tree?: JsonRenderTree; // NEW: json-render tree format with Zod validation

  mode?: 'overlay' | 'fullscreen' | 'inline'; // How to display
}

/**
 * Agent → Canvas/CLI: State change notifications
 */
export interface StateChangeMessage {
  type: 'state_change';
  event: 'story_started' | 'story_continued' | 'branch_selected' | 'world_entered' | 'image_generated' | 'agent_thinking' | 'agent_done';
  data: {
    storyId?: string;
    worldId?: string;
    segmentId?: string;
    branchId?: string;
    assetPath?: string;
    [key: string]: any;
  };
}

/**
 * Canvas → Agent: User interaction events
 */
export interface InteractionMessage {
  type: 'interaction';
  componentId: string;
  interactionType: string; // 'click', 'dialog_change', 'input_change', etc.
  data: any;
  target?: string; // Optional callback handler name from spec
}

/**
 * Connection lifecycle messages
 */
export interface ConnectionMessage {
  type: 'connect' | 'disconnect';
  clientType: 'agent' | 'canvas';
  clientId: string;
}

/**
 * Error messages
 */
export interface ErrorMessage {
  type: 'error';
  error: string;
  details?: any;
}

/**
 * Agent → Canvas: Proactive suggestion
 */
export interface SuggestionMessage {
  type: 'suggestion';
  payload: {
    id: string;
    priority: 'high' | 'medium' | 'low';
    title: string;
    description: string;
    actionId: string;
    actionLabel?: string;
    actionData?: any;
  };
}

/**
 * Union of all message types
 */
export type AgentBusMessage =
  | CanvasUIMessage
  | InteractionMessage
  | StateChangeMessage
  | ConnectionMessage
  | ErrorMessage
  | SuggestionMessage;
