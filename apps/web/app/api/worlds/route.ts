import { NextResponse } from 'next/server';
import { db } from '@deep-sci-fi/db';

export async function GET() {
  try {
    // Fetch worlds from database with cover images
    const worlds = await db.world.findMany({
      orderBy: {
        updatedAt: 'desc',
      },
      select: {
        id: true,
        name: true,
        description: true,
        foundation: true,
        surface: true,
        constraints: true,
        changelog: true,
        state: true,
        version: true,
        createdAt: true,
        updatedAt: true,
        // Include cover art assets
        assets: {
          where: { category: 'cover_art' },
          orderBy: { createdAt: 'desc' },
          take: 1,
          select: {
            id: true,
            url: true,
            storagePath: true,
          },
        },
      },
    });

    // Transform to match expected frontend format
    const transformedWorlds = worlds.map((world) => ({
      id: world.id,
      checkpoint_name: world.id, // Use ID as checkpoint name for compatibility
      foundation: {
        core_premise: (world.foundation as any)?.premise || world.description || '',
        rules: (world.foundation as any)?.rules || [],
        deep_focus_areas: (world.foundation as any)?.deep_focus_areas || {},
        history: (world.foundation as any)?.history || {},
        technology: (world.foundation as any)?.technology || '',
        society: (world.foundation as any)?.society || '',
      },
      surface: world.surface || {
        visible_elements: [],
        opening_scene: null,
        revealed_in_story: [],
      },
      constraints: world.constraints || [],
      changelog: world.changelog || [],
      development: {
        version: world.version,
        state: world.state,
        last_modified: world.updatedAt.toISOString(),
      },
      // Include name for display
      name: world.name,
      // Include cover art asset
      asset: world.assets[0]
        ? {
            id: world.assets[0].id,
            path: world.assets[0].storagePath,
            url: world.assets[0].url,
          }
        : null,
    }));

    return NextResponse.json(transformedWorlds);
  } catch (error) {
    console.error('Error loading worlds:', error);
    return NextResponse.json({ error: 'Failed to load worlds' }, { status: 500 });
  }
}
