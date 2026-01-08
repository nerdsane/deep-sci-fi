import type { PrismaClient } from '@deep-sci-fi/db';

/**
 * User Preferences Tool
 *
 * Saves and retrieves user preferences (writing style, favorite themes, etc.)
 * Used by User Agent (Orchestrator) to remember user preferences
 */

/**
 * Save user preferences
 *
 * @param params - Tool parameters with preferences to save
 * @param context - Tool execution context with database client
 * @returns Updated preferences
 */
export async function user_preferences(params: {
  operation: 'save' | 'get';
  preferences?: {
    writingStyle?: string;
    favoriteThemes?: string[];
    preferredGenres?: string[];
    worldBuildingStyle?: string;
    [key: string]: any;
  };
}, context: {
  userId: string;
  db: PrismaClient;
}): Promise<{
  success: boolean;
  preferences: any;
}> {
  const { operation, preferences } = params;
  const { userId, db } = context;

  console.log(`[user_preferences] Operation: ${operation}, User: ${userId}`);

  try {
    if (operation === 'save') {
      if (!preferences) {
        throw new Error('Preferences required for save operation');
      }

      // Update user preferences in database
      const user = await db.user.update({
        where: { id: userId },
        data: {
          preferences: preferences as any, // Prisma Json type
        },
      });

      return {
        success: true,
        preferences: user.preferences,
      };
    }

    if (operation === 'get') {
      // Get current user preferences
      const user = await db.user.findUnique({
        where: { id: userId },
        select: { preferences: true },
      });

      return {
        success: true,
        preferences: user?.preferences || {},
      };
    }

    throw new Error(`Invalid operation: ${operation}`);
  } catch (error) {
    throw new Error(
      'user_preferences: Operation failed. ' +
      'Make sure Prisma client is passed in context. ' +
      `Error: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

/**
 * Tool definition for Letta agent registration
 */
export const userPreferencesTool = {
  name: 'user_preferences',
  description: 'Save or retrieve user preferences for world building and writing. Includes writing style, favorite themes, preferred genres, and world-building style. Use this to remember user preferences across sessions.',
  parameters: {
    type: 'object',
    properties: {
      operation: {
        type: 'string',
        enum: ['save', 'get'],
        description: 'Operation to perform: "save" to update preferences, "get" to retrieve current preferences',
      },
      preferences: {
        type: 'object',
        description: 'Preferences object to save (required for "save" operation). Can include writingStyle, favoriteThemes, preferredGenres, worldBuildingStyle, and custom fields.',
        properties: {
          writingStyle: {
            type: 'string',
            description: 'User\'s preferred writing style (e.g., "descriptive", "concise", "dialogue-heavy")',
          },
          favoriteThemes: {
            type: 'array',
            items: { type: 'string' },
            description: 'List of favorite sci-fi themes (e.g., ["space exploration", "post-apocalyptic", "AI consciousness"])',
          },
          preferredGenres: {
            type: 'array',
            items: { type: 'string' },
            description: 'List of preferred genres (e.g., ["hard sci-fi", "space opera", "cyberpunk"])',
          },
          worldBuildingStyle: {
            type: 'string',
            description: 'Preferred world-building approach (e.g., "detailed", "emergent", "character-driven")',
          },
        },
      },
    },
    required: ['operation'],
  },
};
