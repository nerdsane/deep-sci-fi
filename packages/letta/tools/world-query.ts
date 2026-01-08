// TODO: Import actual Letta client type when implementing
// import type { Letta } from '@letta-ai/letta-client';

/**
 * Create a world_query tool for story agents to query world agents
 *
 * This tool allows story agents to:
 * 1. Check if story elements contradict world rules
 * 2. Query for existing world elements (characters, locations, tech, etc.)
 * 3. Verify consistency of proposed story content
 *
 * TODO: Implement with @letta-ai/letta-client
 */
export function createWorldQueryTool(worldAgentId: string, lettaClient: any) {
  return async (params: {
    query_type: 'rules' | 'elements' | 'consistency_check';
    query: string;
    context?: any;
  }) => {
    const { query_type, query, context } = params;

    // Construct query message for world agent
    let queryMessage = '';

    switch (query_type) {
      case 'rules':
        queryMessage = `Please provide all world rules relevant to: ${query}`;
        if (context) {
          queryMessage += `\n\nContext: ${JSON.stringify(context, null, 2)}`;
        }
        break;

      case 'elements':
        queryMessage = `Please search for world elements matching: ${query}`;
        if (context) {
          queryMessage += `\n\nAdditional context: ${JSON.stringify(context, null, 2)}`;
        }
        break;

      case 'consistency_check':
        queryMessage = `Please check if the following is consistent with world rules: ${query}`;
        if (context) {
          queryMessage += `\n\nProposed element details: ${JSON.stringify(context, null, 2)}`;
        }
        break;

      default:
        throw new Error(`Unknown query_type: ${query_type}`);
    }

    try {
      // Send query to world agent
      const response = await lettaClient.agents.messages.send({
        agentId: worldAgentId,
        message: queryMessage,
        streamSteps: false,
      });

      // Extract response content
      const content = response.messages?.[0]?.content || 'No response from world agent';

      // Parse any function calls from world agent
      const functionCalls = response.function_calls || [];

      return {
        success: true,
        response: content,
        function_calls: functionCalls,
        query_type,
        original_query: query,
      };
    } catch (error) {
      console.error('Error querying world agent:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        query_type,
        original_query: query,
      };
    }
  };
}

/**
 * Tool definitions for world agents
 */
export const worldAgentTools = [
  {
    name: 'update_world_rules',
    description: 'Update or add new rules to the world foundation or surface',
    parameters: {
      type: 'object',
      properties: {
        rule_category: {
          type: 'string',
          description: 'Category of rule (physics, society, technology, magic, etc.)',
        },
        rule_content: {
          type: 'string',
          description: 'The rule to add or update',
        },
        scope: {
          type: 'string',
          enum: ['foundation', 'surface'],
          description: 'Whether this is a foundational rule or surface-level detail',
        },
      },
      required: ['rule_category', 'rule_content', 'scope'],
    },
  },
  {
    name: 'check_consistency',
    description: 'Check if a proposed element contradicts existing world rules',
    parameters: {
      type: 'object',
      properties: {
        element_type: {
          type: 'string',
          description: 'Type of element (character, location, technology, species, etc.)',
        },
        element_description: {
          type: 'string',
          description: 'Description of the element to check',
        },
        element_properties: {
          type: 'object',
          description: 'Specific properties of the element',
        },
      },
      required: ['element_type', 'element_description'],
    },
  },
  {
    name: 'query_world_elements',
    description: 'Search for existing world elements',
    parameters: {
      type: 'object',
      properties: {
        element_type: {
          type: 'string',
          description: 'Type of element to search for',
        },
        search_query: {
          type: 'string',
          description: 'Natural language search query',
        },
      },
      required: ['search_query'],
    },
  },
  {
    name: 'create_world_element',
    description: 'Create a new canonical world element',
    parameters: {
      type: 'object',
      properties: {
        element_type: {
          type: 'string',
          enum: ['character', 'location', 'technology', 'species', 'organization', 'artifact'],
          description: 'Type of element to create',
        },
        name: {
          type: 'string',
          description: 'Name of the element',
        },
        description: {
          type: 'string',
          description: 'Detailed description',
        },
        properties: {
          type: 'object',
          description: 'Additional properties specific to the element type',
        },
      },
      required: ['element_type', 'name', 'description'],
    },
  },
];

/**
 * Tool definitions for story agents
 */
export const storyAgentTools = [
  {
    name: 'create_story_segment',
    description: 'Create a new narrative segment',
    parameters: {
      type: 'object',
      properties: {
        content: {
          type: 'string',
          description: 'The narrative content',
        },
        segment_type: {
          type: 'string',
          enum: ['narrative', 'dialogue', 'action', 'exposition'],
          description: 'Type of narrative segment',
        },
        metadata: {
          type: 'object',
          description: 'Additional metadata (characters involved, location, etc.)',
        },
      },
      required: ['content', 'segment_type'],
    },
  },
  {
    name: 'generate_vn_scene',
    description: 'Create a visual novel scene with dialogue, characters, and background',
    parameters: {
      type: 'object',
      properties: {
        background: {
          type: 'string',
          description: 'Scene background description or image path',
        },
        characters: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string' },
              sprite: { type: 'string' },
              position: { type: 'string', enum: ['left', 'center', 'right'] },
              expression: { type: 'string' },
            },
          },
          description: 'Characters in the scene',
        },
        dialogue: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              speaker: { type: 'string' },
              text: { type: 'string' },
              expression: { type: 'string' },
              type: { type: 'string', enum: ['dialogue', 'narration', 'thought'] },
            },
          },
          description: 'Dialogue and narration lines',
        },
      },
      required: ['background', 'dialogue'],
    },
  },
  {
    name: 'create_ui_component',
    description: 'Generate agent-driven UI component for immersive experience',
    parameters: {
      type: 'object',
      properties: {
        component_type: {
          type: 'string',
          enum: [
            'button', 'text', 'image', 'gallery', 'card', 'timeline',
            'callout', 'stats', 'badge', 'hero', 'scroll_section',
            'progress_bar', 'action_bar', 'stack', 'grid'
          ],
          description: 'Type of UI component to create',
        },
        props: {
          type: 'object',
          description: 'Component properties based on component type',
        },
      },
      required: ['component_type', 'props'],
    },
  },
  {
    name: 'check_story_consistency',
    description: 'Check if new story content is consistent with previous narrative',
    parameters: {
      type: 'object',
      properties: {
        new_content: {
          type: 'string',
          description: 'The new story content to check',
        },
        check_against: {
          type: 'string',
          enum: ['previous_segments', 'world_rules', 'both'],
          description: 'What to check consistency against',
        },
      },
      required: ['new_content'],
    },
  },
];
