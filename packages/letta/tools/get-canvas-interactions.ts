/**
 * get_canvas_interactions - Agent tool for reading user interactions from canvas
 *
 * Allows agents to poll for user interactions with canvas UI components.
 * Interactions are queued when users click buttons, select options, etc.
 */

import {
  getInteractions,
  peekInteractions,
  getInteractionCount,
  type QueuedInteraction,
} from '../websocket';

// ============================================================================
// Types
// ============================================================================

export interface GetInteractionsParams {
  peek?: boolean;
  componentId?: string;
  interactionType?: string;
}

export interface GetInteractionsResult {
  success: boolean;
  message: string;
  interactions: QueuedInteraction[];
  count: number;
}

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Get pending user interactions from the canvas.
 *
 * Call this to see what buttons users have clicked, actions they've selected,
 * or other interactions with your UI components. By default, reading clears
 * the queue - set peek=true to look without clearing.
 */
export async function get_canvas_interactions(
  params: GetInteractionsParams = {}
): Promise<GetInteractionsResult> {
  const { peek = false, componentId, interactionType } = params;

  try {
    // Get interactions (either peek or consume)
    let interactions = peek ? peekInteractions() : getInteractions();

    // Apply filters if specified
    if (componentId) {
      interactions = interactions.filter((i) => i.componentId === componentId);
    }
    if (interactionType) {
      interactions = interactions.filter((i) => i.interactionType === interactionType);
    }

    const count = interactions.length;

    let message: string;
    if (count === 0) {
      message = 'No pending interactions';
    } else if (count === 1) {
      const i = interactions[0];
      message = `1 interaction: ${i.interactionType} on ${i.componentId}${i.data?.actionId ? ` (action: ${i.data.actionId})` : ''}`;
    } else {
      message = `${count} pending interactions:\n${interactions
        .map((i) => `  - ${i.interactionType} on ${i.componentId}`)
        .join('\n')}`;
    }

    return {
      success: true,
      message,
      interactions,
      count,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    return {
      success: false,
      message: `Failed to get interactions: ${errorMsg}`,
      interactions: [],
      count: 0,
    };
  }
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const getCanvasInteractionsTool = {
  name: 'get_canvas_interactions',
  description:
    'Get pending user interactions from canvas UI components. Call to see what buttons were clicked, options selected, etc.',
  parameters: {
    type: 'object',
    properties: {
      peek: {
        type: 'boolean',
        description: 'If true, look at interactions without clearing the queue (default: false)',
      },
      componentId: {
        type: 'string',
        description: 'Filter interactions by component ID',
      },
      interactionType: {
        type: 'string',
        description: 'Filter interactions by type (e.g., "click", "action")',
      },
    },
    required: [],
  },
};
