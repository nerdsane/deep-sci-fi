import { NextResponse } from 'next/server';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { db, isCloudMode } from '@/lib/db';

// Point to letta-code .dsf directory for local mode
const STORIES_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/stories'
  : 'letta-code/.dsf/stories';

// Load stories from local filesystem (development mode)
async function loadLocalStories(worldId?: string) {
  if (!existsSync(STORIES_DIR)) {
    return [];
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

  return stories;
}

// Load stories from database (cloud mode)
async function loadCloudStories(worldId?: string) {
  const stories = await db.story.findMany({
    where: worldId ? { worldId } : undefined,
    include: {
      segments: {
        orderBy: { createdAt: 'asc' },
      },
      author: {
        select: { id: true, name: true },
      },
      world: {
        select: { id: true, name: true },
      },
    },
    orderBy: { updatedAt: 'desc' },
  });

  // Transform to match frontend expectations
  return stories.map((story) => ({
    id: story.id,
    worldId: story.worldId,
    title: story.title,
    metadata: {
      ...((story.metadata as Record<string, unknown>) || {}),
      last_updated: story.updatedAt.toISOString(),
      created: story.createdAt.toISOString(),
    },
    worldContributions: story.worldContributions,
    segments: story.segments.map((segment) => ({
      id: segment.id,
      parentSegmentId: segment.parentSegmentId,
      content: segment.content,
      wordCount: segment.wordCount,
      worldEvolution: segment.worldEvolution,
      branches: segment.branches,
      vnScene: segment.vnScene,
      uiComponents: segment.uiComponents,
      audioTracks: segment.audioTracks,
      createdAt: segment.createdAt.toISOString(),
    })),
    author: story.author,
    world: story.world,
  }));
}

export async function GET(request: Request) {
  try {
    // Check for worldId filter in query params
    const { searchParams } = new URL(request.url);
    const worldId = searchParams.get('worldId') || undefined;

    const stories = isCloudMode()
      ? await loadCloudStories(worldId)
      : await loadLocalStories(worldId);

    return NextResponse.json(stories);
  } catch (error) {
    console.error('Error loading stories:', error);
    return NextResponse.json({ error: 'Failed to load stories' }, { status: 500 });
  }
}
