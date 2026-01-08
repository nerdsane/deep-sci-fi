import { NextResponse } from 'next/server';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

// Point to letta-code .dsf directory
const WORLDS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/worlds'
  : 'letta-code/.dsf/worlds';
const ASSETS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/assets'
  : 'letta-code/.dsf/assets';

export async function GET() {
  try {
    if (!existsSync(WORLDS_DIR)) {
      return NextResponse.json([]);
    }

    const worlds = [];
    const files = await readdir(WORLDS_DIR);

    for (const file of files) {
      if (file.endsWith('.json')) {
        const content = await readFile(join(WORLDS_DIR, file), 'utf-8');
        const world = JSON.parse(content);
        const checkpoint = file.replace('.json', '');

        // Add checkpoint name to world data
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

    return NextResponse.json(worlds);
  } catch (error) {
    console.error('Error loading worlds:', error);
    return NextResponse.json({ error: 'Failed to load worlds' }, { status: 500 });
  }
}
