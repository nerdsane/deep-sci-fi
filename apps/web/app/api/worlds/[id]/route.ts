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
          where: { category: 'cover_art' },
          orderBy: { createdAt: 'desc' },
          take: 1,
          select: { id: true, url: true, storagePath: true },
        },
      },
    });

    if (!world) {
      return NextResponse.json({ error: 'World not found' }, { status: 404 });
    }

    return NextResponse.json(world);
  } catch (error) {
    console.error('[GET /api/worlds/[id]] Error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch world' },
      { status: 500 }
    );
  }
}
