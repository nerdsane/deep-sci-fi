/**
 * World Draft Generator Tool
 *
 * Generates world concept drafts from user prompts using Claude API
 * Used by User Agent (Orchestrator) to help users create new worlds
 */

import Anthropic from '@anthropic-ai/sdk';

/**
 * Generate world concept drafts from a user prompt
 *
 * @param params - Tool parameters
 * @param context - Tool execution context
 * @returns Array of world draft concepts
 */
export async function world_draft_generator(params: {
  prompt: string;
  count?: number;
}, context: { userId: string }): Promise<Array<{
  name: string;
  summary: string;
  foundation: {
    premise: string;
    technology: string;
    society: string;
    physics?: string;
    history?: string;
  };
}>> {
  const { prompt, count = 3 } = params;

  console.log(`[world_draft_generator] Generating ${count} world drafts for prompt: "${prompt}"`);
  console.log(`[world_draft_generator] User: ${context.userId}`);

  // Check for Anthropic API key
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      'world_draft_generator: ANTHROPIC_API_KEY is required. ' +
      'Set it in your environment variables.'
    );
  }

  // Initialize Anthropic client
  const anthropic = new Anthropic({ apiKey });

  // Generate world concepts using Claude
  const systemPrompt = `You are a creative science fiction world-building assistant. Your task is to generate compelling, diverse sci-fi world concepts.

Each world concept should have:
- A unique, memorable name
- A concise summary (2-3 sentences)
- Foundation details:
  - Premise: The core concept or "what if" that defines this world
  - Technology: The level and nature of technology in this world
  - Society: Social structures, governance, culture
  - Physics: Any unique physical laws or phenomena (optional)
  - History: Key historical events that shaped this world (optional)

Generate diverse concepts that explore different sci-fi subgenres and themes.
Return ONLY a valid JSON array, no other text.`;

  const userPrompt = `Generate ${count} distinct science fiction world concepts based on this prompt: "${prompt}"

Return a JSON array with this structure:
[
  {
    "name": "World Name",
    "summary": "Brief summary of the world...",
    "foundation": {
      "premise": "The core concept...",
      "technology": "Technology description...",
      "society": "Social structures...",
      "physics": "Unique physics (optional)",
      "history": "Historical background (optional)"
    }
  }
]`;

  try {
    const response = await anthropic.messages.create({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      system: systemPrompt,
      messages: [
        {
          role: 'user',
          content: userPrompt,
        },
      ],
    });

    // Extract text from response
    const content = response.content[0];
    if (content.type !== 'text') {
      throw new Error('Unexpected response type from Claude');
    }

    let textContent = content.text;

    // Handle potential markdown code blocks
    if (textContent.includes('```json')) {
      const jsonMatch = textContent.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        textContent = jsonMatch[1];
      }
    } else if (textContent.includes('```')) {
      const codeMatch = textContent.match(/```\s*([\s\S]*?)\s*```/);
      if (codeMatch) {
        textContent = codeMatch[1];
      }
    }

    // Parse the JSON response
    const drafts = JSON.parse(textContent.trim());

    if (!Array.isArray(drafts)) {
      throw new Error('Response is not an array');
    }

    console.log(`[world_draft_generator] Successfully generated ${drafts.length} world drafts`);

    // Validate and return drafts
    return drafts.map((draft, index) => {
      if (!draft.name || !draft.summary || !draft.foundation) {
        console.warn(`[world_draft_generator] Draft ${index} missing required fields`);
      }
      return {
        name: draft.name || `World ${index + 1}`,
        summary: draft.summary || 'No summary provided',
        foundation: {
          premise: draft.foundation?.premise || 'No premise provided',
          technology: draft.foundation?.technology || 'Technology level not specified',
          society: draft.foundation?.society || 'Society structure not specified',
          physics: draft.foundation?.physics,
          history: draft.foundation?.history,
        },
      };
    });
  } catch (error) {
    console.error('[world_draft_generator] Failed to generate world drafts:', error);
    throw new Error(
      `world_draft_generator failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}

/**
 * Tool definition for Letta agent registration
 */
export const worldDraftGeneratorTool = {
  name: 'world_draft_generator',
  description: 'Generate compelling sci-fi world concept drafts from a user prompt. Returns 3-4 diverse world concepts with names, summaries, and foundational details (premise, technology, society, physics, history).',
  parameters: {
    type: 'object',
    properties: {
      prompt: {
        type: 'string',
        description: 'The user\'s prompt describing what kind of world they want to create (e.g., "post-scarcity society", "dystopian Earth", "space opera universe")',
      },
      count: {
        type: 'number',
        description: 'Number of world drafts to generate (default: 3, max: 4)',
        minimum: 1,
        maximum: 4,
      },
    },
    required: ['prompt'],
  },
};
