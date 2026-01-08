import { NextResponse } from 'next/server';
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';
import { storage } from '@/lib/storage';

// Point to letta-code .dsf directory for local mode
const ASSETS_DIR = process.cwd().includes('/apps/web')
  ? '../../letta-code/.dsf/assets'
  : 'letta-code/.dsf/assets';

// Content type mapping
function getContentType(path: string): string {
  if (path.endsWith('.png')) return 'image/png';
  if (path.endsWith('.jpg') || path.endsWith('.jpeg')) return 'image/jpeg';
  if (path.endsWith('.gif')) return 'image/gif';
  if (path.endsWith('.webp')) return 'image/webp';
  if (path.endsWith('.svg')) return 'image/svg+xml';
  if (path.endsWith('.mp3')) return 'audio/mpeg';
  if (path.endsWith('.wav')) return 'audio/wav';
  if (path.endsWith('.ogg')) return 'audio/ogg';
  if (path.endsWith('.mp4')) return 'video/mp4';
  if (path.endsWith('.webm')) return 'video/webm';
  return 'application/octet-stream';
}

export async function GET(
  request: Request,
  { params }: { params: { path: string[] } }
) {
  try {
    const assetPath = params.path.join('/');

    // Cloud mode: redirect to CloudFront/S3
    if (storage.isConfigured()) {
      const url = storage.getPublicUrl(assetPath);
      return NextResponse.redirect(url, { status: 302 });
    }

    // Local mode: serve from filesystem
    const fullPath = join(ASSETS_DIR, assetPath);

    if (!existsSync(fullPath)) {
      return new NextResponse('Asset not found', { status: 404 });
    }

    const file = await readFile(fullPath);
    const contentType = getContentType(assetPath);

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
