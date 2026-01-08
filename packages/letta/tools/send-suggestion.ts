/**
 * send_suggestion - Agent tool for sending proactive suggestions to canvas
 *
 * Allows agents to send contextual suggestions that appear in the
 * AgentSuggestions panel in the canvas UI.
 */

import { sendSuggestion } from '../websocket';

// ============================================================================
// Types
// ============================================================================

export interface SendSuggestionParams {
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  action_id: string;
  action_label?: string;
  action_data?: any;
}

export interface SendSuggestionResult {
  success: boolean;
  message: string;
}

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Send a proactive suggestion to the canvas UI.
 *
 * Use this to offer contextual suggestions based on current state,
 * unused elements, story opportunities, or any other insights.
 */
export async function send_suggestion(
  params: SendSuggestionParams
): Promise<SendSuggestionResult> {
  const { title, description, priority, action_id, action_label, action_data } = params;

  try {
    if (!title) {
      return {
        success: false,
        message: 'title is required',
      };
    }

    if (!description) {
      return {
        success: false,
        message: 'description is required',
      };
    }

    if (!action_id) {
      return {
        success: false,
        message: 'action_id is required',
      };
    }

    // Send suggestion via WebSocket manager
    sendSuggestion(title, description, priority || 'medium', action_id, action_label, action_data);

    console.log(`[send_suggestion] Sent suggestion: ${title} (${priority})`);

    return {
      success: true,
      message: `Suggestion "${title}" sent to canvas`,
    };
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : String(error);
    console.error('[send_suggestion] Error:', errorMsg);
    return {
      success: false,
      message: `Failed to send suggestion: ${errorMsg}`,
    };
  }
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const sendSuggestionTool = {
  name: 'send_suggestion',
  description:
    'Send a proactive suggestion to the canvas UI. Use to offer contextual insights, story opportunities, or actions.',
  parameters: {
    type: 'object',
    properties: {
      title: {
        type: 'string',
        description: 'Short title for the suggestion',
      },
      description: {
        type: 'string',
        description: 'Detailed description of what the suggestion is about',
      },
      priority: {
        type: 'string',
        enum: ['high', 'medium', 'low'],
        description: 'Suggestion priority (affects display prominence)',
      },
      action_id: {
        type: 'string',
        description: 'Unique identifier for the action (used when user accepts)',
      },
      action_label: {
        type: 'string',
        description: 'Label for the action button (e.g., "Try it", "Apply")',
      },
      action_data: {
        description: 'Additional data to pass when action is triggered',
      },
    },
    required: ['title', 'description', 'action_id'],
  },
};
