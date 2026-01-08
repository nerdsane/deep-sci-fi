import { NextResponse } from 'next/server';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { db, isCloudMode } from '@/lib/db';
import { storage } from '@/lib/storage';

// Point to letta-code .dsf directory for local mode
const WORLDS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/worlds'
  : 'letta-code/.dsf/worlds';
const ASSETS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/assets'
  : 'letta-code/.dsf/assets';

interface WorldAsset {
  id: string;
  type: string;
  path: string;
  url?: string;
  description: string;
}

// Load worlds from local filesystem (development mode)
async function loadLocalWorlds() {
  if (!existsSync(WORLDS_DIR)) {
    return [];
  }

  const worlds = [];
  const files = await readdir(WORLDS_DIR);

  for (const file of files) {
    if (file.endsWith('.json')) {
      const content = await readFile(join(WORLDS_DIR, file), 'utf-8');
      const world = JSON.parse(content);
      const checkpoint = file.replace('.json', '');

      world.checkpoint_name = checkpoint;

      // Auto-discover cover image
      if (!world.asset) {
        const coverPath = join(ASSETS_DIR, 'worlds', checkpoint, 'cover.png');
        if (existsSync(coverPath)) {
          world.asset = {
            id: `cover_${checkpoint}`,
            type: 'image',
            path: `worlds/${checkpoint}/cover.png`,
            description: 'World cover image',
          };
        }
      }

      worlds.push(world);
    }
  }

  // Sort by last modified (most recent first)
  worlds.sort((a, b) =>
    new Date(b.development.last_modified).getTime() -
    new Date(a.development.last_modified).getTime()
  );

  return worlds;
}

// Load worlds from database (cloud mode)
async function loadCloudWorlds() {
  const worlds = await db.world.findMany({
    include: {
      assets: {
        where: { category: 'cover' },
        take: 1,
      },
      owner: {
        select: { id: true, name: true },
      },
    },
    orderBy: { updatedAt: 'desc' },
  });

  // Transform to match frontend expectations
  return worlds.map((world) => {
    const coverAsset = world.assets[0];

    return {
      id: world.id,
      name: world.name,
      checkpoint_name: world.id,
      foundation: world.foundation,
      surface: world.surface,
      constraints: world.constraints,
      development: {
        state: world.state,
        version: world.version,
        last_modified: world.updatedAt.toISOString(),
        created: world.createdAt.toISOString(),
      },
      changelog: world.changelog,
      owner: world.owner,
      visibility: world.visibility,
      asset: coverAsset
        ? {
            id: coverAsset.id,
            type: coverAsset.type,
            path: coverAsset.storagePath,
            url: storage.getPublicUrl(coverAsset.storagePath),
            description: coverAsset.description || 'World cover image',
          } as WorldAsset
        : undefined,
    };
  });
}

export async function GET() {
  try {
    const worlds = isCloudMode()
      ? await loadCloudWorlds()
      : await loadLocalWorlds();

    return NextResponse.json(worlds);
  } catch (error) {
    console.error('Error loading worlds:', error);
    return NextResponse.json({ error: 'Failed to load worlds' }, { status: 500 });
  }
}
