#!/usr/bin/env npx ts-node
/**
 * Migration Script: Assets from local files to S3
 *
 * Reads asset files from letta-code/.dsf/assets/ and uploads them to S3,
 * creating corresponding records in the database.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... \
 *   AWS_S3_BUCKET=deep-sci-fi-assets-... \
 *   AWS_REGION=us-east-1 \
 *   npx ts-node scripts/migrate-assets-to-s3.ts
 *
 * Prerequisites:
 *   - DATABASE_URL, AWS_S3_BUCKET, AWS_REGION environment variables set
 *   - AWS credentials configured (via environment or ~/.aws/credentials)
 *   - Database schema applied (prisma migrate deploy)
 *   - Worlds already migrated (migrate-worlds-to-db.ts)
 */

import { PrismaClient } from '@prisma/client';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { readdir, readFile, stat } from 'fs/promises';
import { existsSync } from 'fs';
import { join, extname } from 'path';

const ASSETS_DIR = './letta-code/.dsf/assets';

// Content type mapping
function getContentType(filename: string): string {
  const ext = extname(filename).toLowerCase();
  const types: Record<string, string> = {
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
  };
  return types[ext] || 'application/octet-stream';
}

// Get asset type from content type
function getAssetType(contentType: string): string {
  if (contentType.startsWith('image/')) return 'image';
  if (contentType.startsWith('audio/')) return 'audio';
  if (contentType.startsWith('video/')) return 'video';
  return 'file';
}

// Recursively walk directory
async function* walkDir(dir: string): AsyncGenerator<{ path: string; relativePath: string }> {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      yield* walkDir(fullPath);
    } else {
      yield {
        path: fullPath,
        relativePath: fullPath.replace(ASSETS_DIR + '/', ''),
      };
    }
  }
}

async function main() {
  console.log('=== Asset Migration Script ===\n');

  // Check prerequisites
  if (!process.env.DATABASE_URL) {
    console.error('ERROR: DATABASE_URL environment variable not set');
    process.exit(1);
  }
  if (!process.env.AWS_S3_BUCKET) {
    console.error('ERROR: AWS_S3_BUCKET environment variable not set');
    process.exit(1);
  }
  if (!process.env.AWS_REGION) {
    console.error('ERROR: AWS_REGION environment variable not set');
    process.exit(1);
  }

  if (!existsSync(ASSETS_DIR)) {
    console.error(`ERROR: Assets directory not found: ${ASSETS_DIR}`);
    process.exit(1);
  }

  const bucket = process.env.AWS_S3_BUCKET;
  const region = process.env.AWS_REGION;
  const cloudfrontDomain = process.env.CLOUDFRONT_DOMAIN;

  const db = new PrismaClient();
  const s3 = new S3Client({ region });

  try {
    await db.$connect();
    console.log('Connected to database');
    console.log(`S3 Bucket: ${bucket}`);
    console.log(`Region: ${region}`);
    if (cloudfrontDomain) {
      console.log(`CloudFront: ${cloudfrontDomain}`);
    }
    console.log('');

    // Get world mapping (checkpoint name -> database ID)
    const worlds = await db.world.findMany({
      select: { id: true, name: true },
    });
    const worldMap = new Map<string, string>();
    for (const world of worlds) {
      worldMap.set(world.name, world.id);
    }
    console.log(`Found ${worlds.length} worlds in database\n`);

    let uploaded = 0;
    let skipped = 0;
    let errors = 0;

    // Walk assets directory
    for await (const { path: filePath, relativePath } of walkDir(ASSETS_DIR)) {
      console.log(`Processing: ${relativePath}`);

      try {
        // Parse path structure: worlds/<world-name>/filename or stories/<world>/<story>/filename
        const parts = relativePath.split('/');
        const category = parts[0]; // 'worlds', 'stories', etc.

        // Check if asset already exists
        const existing = await db.asset.findFirst({
          where: { storagePath: relativePath },
        });

        if (existing) {
          console.log(`  - Skipped (already exists): ${existing.id}`);
          skipped++;
          continue;
        }

        // Read file
        const fileContent = await readFile(filePath);
        const fileStat = await stat(filePath);
        const contentType = getContentType(filePath);
        const assetType = getAssetType(contentType);

        // Upload to S3
        await s3.send(
          new PutObjectCommand({
            Bucket: bucket,
            Key: relativePath,
            Body: fileContent,
            ContentType: contentType,
            CacheControl: 'public, max-age=31536000',
          })
        );

        // Generate CDN URL
        const url = cloudfrontDomain
          ? `https://${cloudfrontDomain}/${relativePath}`
          : `https://${bucket}.s3.amazonaws.com/${relativePath}`;

        // Determine world association
        let worldId: string | null = null;
        let assetCategory: string | null = null;

        if (category === 'worlds' && parts.length >= 2) {
          const worldName = parts[1];
          worldId = worldMap.get(worldName) || null;
          assetCategory = parts[2] === 'cover.png' ? 'cover' : 'world';
        }

        // Create asset record
        const asset = await db.asset.create({
          data: {
            worldId,
            type: assetType,
            category: assetCategory,
            storagePath: relativePath,
            url,
            description: `Migrated from ${relativePath}`,
            metadata: {
              size: fileStat.size,
              contentType,
              migratedAt: new Date().toISOString(),
            },
            generated: false,
          },
        });

        console.log(`  - Uploaded: ${asset.id}`);
        uploaded++;
      } catch (err) {
        console.error(`  - Error: ${err instanceof Error ? err.message : String(err)}`);
        errors++;
      }
    }

    console.log('\n=== Migration Summary ===');
    console.log(`Uploaded: ${uploaded}`);
    console.log(`Skipped:  ${skipped}`);
    console.log(`Errors:   ${errors}`);
  } finally {
    await db.$disconnect();
  }
}

main().catch((err) => {
  console.error('Migration failed:', err);
  process.exit(1);
});
