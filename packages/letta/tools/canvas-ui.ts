/**
 * canvas_ui - Agent tool for creating dynamic UI components in the canvas
 *
 * Allows agents to create inline visualizations, interactive elements, and
 * multimedia enhancements for stories and worlds displayed in the canvas.
 */

import {
  sendCanvasUI,
  sendStateChange,
  type ComponentSpec,
} from '../websocket';

// ============================================================================
// Types
// ============================================================================

export interface CanvasUIParams {
  target: string;
  spec: ComponentSpec;
  action?: 'create' | 'update' | 'remove';
  mode?: 'overlay' | 'fullscreen' | 'inline';
}

export interface CanvasUIResult {
  success: boolean;
  message: string;
  componentId?: string;
}

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Create or update dynamic UI in the canvas.
 *
 * Use this to add inline visualizations, interactive elements, and multimedia
 * enhancements to stories and worlds. The UI will appear in the canvas at the
 * specified target location.
 */
export async function canvas_ui(params: CanvasUIParams): Promise<CanvasUIResult> {
  const { target, spec, action = 'create', mode = 'overlay' } = params;

  try {
    if (!target) {
      return {
        success: false,
        message: 'target is required (e.g., "story_segment_123", "world_overview")',
      };
    }

    if (!spec && action !== 'remove') {
      return {
        success: false,
        message: 'spec is required for create/update actions',
      };
    }

    const componentId = spec?.id || `canvas-${Date.now()}`;

    // Send the UI update via WebSocket manager
    sendCanvasUI(action, target, componentId, spec, mode);

    console.log(`[canvas_ui] Sent ${action} for ${componentId} at ${target}`);

    let message: string;
    if (action === 'remove') {
      message = `Removed component from ${target}`;
    } else {
      message = `Component ${componentId} ${action === 'update' ? 'updated' : 'created'} at ${target} (mode: ${mode})`;
    }

    return {
      success: true,
      message,
      componentId,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[canvas_ui] Error:', errorMsg);
    return {
      success: false,
      message: `Failed to ${action} UI component: ${errorMsg}`,
    };
  }
}

/**
 * Broadcast state change to all connected clients
 */
export async function broadcastStateChange(
  event:
    | 'story_started'
    | 'story_continued'
    | 'branch_selected'
    | 'world_entered'
    | 'image_generated'
    | 'agent_thinking'
    | 'agent_done',
  data: Record<string, any>
): Promise<void> {
  sendStateChange(event, data);
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const canvasUiTool = {
  name: 'canvas_ui',
  description:
    'Create dynamic UI components in the canvas. Use to add visualizations, interactive elements, and multimedia to stories and worlds.',
  parameters: {
    type: 'object',
    properties: {
      target: {
        type: 'string',
        description:
          'Target mount point for the component (e.g., "story_segment_123", "world_overview", "floating")',
      },
      spec: {
        type: 'object',
        description: 'Component specification with type, id, props, and children',
        properties: {
          type: {
            type: 'string',
            description:
              'Component type: Text, Button, Image, Card, Gallery, Timeline, Stats, Callout, Badge, Divider, Stack, Grid, Hero, ActionBar, Dialog',
          },
          id: {
            type: 'string',
            description: 'Unique component ID',
          },
          props: {
            type: 'object',
            description: 'Component-specific properties',
          },
          children: {
            description: 'Child components (for containers)',
          },
        },
        required: ['type'],
      },
      action: {
        type: 'string',
        enum: ['create', 'update', 'remove'],
        description: 'Action to perform (default: create)',
      },
      mode: {
        type: 'string',
        enum: ['overlay', 'fullscreen', 'inline'],
        description: 'Display mode (default: overlay)',
      },
    },
    required: ['target', 'spec'],
  },
};
