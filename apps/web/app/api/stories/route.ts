import { NextResponse } from 'next/server';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

// Point to letta-code .dsf directory for local mode
const STORIES_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/stories'
  : 'letta-code/.dsf/stories';

export async function GET(request: Request) {
  try {
    // Check for worldId filter in query params
    const { searchParams } = new URL(request.url);
    const worldId = searchParams.get('worldId') || undefined;

    // In production, this would fetch from Letta's API
    // For now, read from local filesystem
    if (!existsSync(STORIES_DIR)) {
      return NextResponse.json([]);
    }

    const stories = [];
    const worldDirs = await readdir(STORIES_DIR);

    for (const worldDir of worldDirs) {
      // If filtering by worldId, skip non-matching directories
      if (worldId && worldDir !== worldId) {
        continue;
      }

      const worldPath = join(STORIES_DIR, worldDir);
      try {
        const files = await readdir(worldPath);
        for (const file of files) {
          if (file.endsWith('.json')) {
            const content = await readFile(join(worldPath, file), 'utf-8');
            const story = JSON.parse(content);
            story.worldId = worldDir;
            stories.push(story);
          }
        }
      } catch {
        // Skip if not a directory
        continue;
      }
    }

    // Sort by last updated (most recent first)
    stories.sort((a, b) =>
      new Date(b.metadata.last_updated).getTime() -
      new Date(a.metadata.last_updated).getTime()
    );

    return NextResponse.json(stories);
  } catch (error) {
    console.error('Error loading stories:', error);
    return NextResponse.json({ error: 'Failed to load stories' }, { status: 500 });
  }
}
