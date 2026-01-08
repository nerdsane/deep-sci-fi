import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

// Point to letta-code .dsf directory
const ASSETS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/assets'
  : 'letta-code/.dsf/assets';

export async function GET(
  request: Request,
  { params }: { params: { path: string[] } }
) {
  try {
    const assetPath = params.path.join('/');
    const fullPath = join(ASSETS_DIR, assetPath);

    if (!existsSync(fullPath)) {
      return new NextResponse('Asset not found', { status: 404 });
    }

    const file = await readFile(fullPath);

    // Determine content type
    let contentType = 'application/octet-stream';
    if (assetPath.endsWith('.png')) contentType = 'image/png';
    else if (assetPath.endsWith('.jpg') || assetPath.endsWith('.jpeg')) contentType = 'image/jpeg';
    else if (assetPath.endsWith('.gif')) contentType = 'image/gif';
    else if (assetPath.endsWith('.webp')) contentType = 'image/webp';
    else if (assetPath.endsWith('.svg')) contentType = 'image/svg+xml';

    return new NextResponse(file, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=31536000',
      },
    });
  } catch (error) {
    console.error('Error serving asset:', error);
    return new NextResponse('Error loading asset', { status: 500 });
  }
}
