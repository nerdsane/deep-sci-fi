import { NextRequest, NextResponse } from 'next/server';
import { db } from '@deep-sci-fi/db';

/**
 * DELETE /api/worlds/[id]
 * Delete a world and all its related data (stories, assets, messages, etc.)
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id) {
      return NextResponse.json({ error: 'World ID is required' }, { status: 400 });
    }

    // Check if world exists
    const world = await db.world.findUnique({
      where: { id },
      select: { id: true, name: true },
    });

    if (!world) {
      return NextResponse.json({ error: 'World not found' }, { status: 404 });
    }

    // Delete the world (cascades to stories, assets, messages, etc.)
    await db.world.delete({
      where: { id },
    });

    console.log(`[DELETE /api/worlds/${id}] Deleted world: ${world.name}`);

    return NextResponse.json({
      success: true,
      message: `World "${world.name}" has been deleted`,
      deletedId: id,
    });
  } catch (error) {
    console.error('[DELETE /api/worlds/[id]] Error:', error);
    return NextResponse.json(
      { error: 'Failed to delete world' },
      { status: 500 }
    );
  }
}

/**
 * GET /api/worlds/[id]
 * Get a single world by ID
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id) {
      return NextResponse.json({ error: 'World ID is required' }, { status: 400 });
    }

    const world = await db.world.findUnique({
      where: { id },
      include: {
        stories: {
          select: { id: true, title: true },
          orderBy: { updatedAt: 'desc' },
        },
        assets: {
          where: { type: 'image' },
          orderBy: { createdAt: 'desc' },
          take: 1,
          select: { id: true, url: true, storagePath: true },
        },
      },
    });

    if (!world) {
      return NextResponse.json({ error: 'World not found' }, { status: 404 });
    }

    // Transform to match frontend contract (same as list endpoint)
    const transformed = {
      id: world.id,
      checkpoint_name: world.id,
      name: world.name,
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
      asset: world.assets[0]
        ? {
            id: world.assets[0].id,
            path: world.assets[0].storagePath,
            url: world.assets[0].url,
          }
        : null,
      stories: world.stories,
    };

    return NextResponse.json(transformed);
  } catch (error) {
    console.error('[GET /api/worlds/[id]] Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch world' },
      { status: 500 }
    );
  }
}
