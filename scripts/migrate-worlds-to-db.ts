#!/usr/bin/env npx ts-node
/**
 * Migration Script: Worlds from JSON files to PostgreSQL
 *
 * Reads world JSON files from letta-code/.dsf/worlds/ and inserts them
 * into the database using Prisma.
 *
 * Usage:
 *   DATABASE_URL=postgresql://... npx ts-node scripts/migrate-worlds-to-db.ts
 *
 * Prerequisites:
 *   - DATABASE_URL environment variable set
 *   - Database schema applied (prisma migrate deploy)
 */

import { PrismaClient } from '@prisma/client';
import { readdir, readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

const WORLDS_DIR = './letta-code/.dsf/worlds';

interface WorldJson {
  name?: string;
  title?: string;
  foundation?: object;
  surface?: object;
  constraints?: unknown[];
  changelog?: unknown[];
  development?: {
    state?: string;
    version?: number;
    last_modified?: string;
    created?: string;
  };
}

async function main() {
  console.log('=== World Migration Script ===\n');

  // Check prerequisites
  if (!process.env.DATABASE_URL) {
    console.error('ERROR: DATABASE_URL environment variable not set');
    process.exit(1);
  }

  if (!existsSync(WORLDS_DIR)) {
    console.error(`ERROR: Worlds directory not found: ${WORLDS_DIR}`);
    process.exit(1);
  }

  const db = new PrismaClient();

  try {
    await db.$connect();
    console.log('Connected to database\n');

    // Create or get system user for ownership
    let systemUser = await db.user.findFirst({
      where: { email: 'system@deep-sci-fi.local' },
    });

    if (!systemUser) {
      console.log('Creating system user for world ownership...');
      systemUser = await db.user.create({
        data: {
          email: 'system@deep-sci-fi.local',
          name: 'System',
          provider: 'system',
        },
      });
      console.log(`Created system user: ${systemUser.id}\n`);
    }

    // Read and process world files
    const files = await readdir(WORLDS_DIR);
    const jsonFiles = files.filter((f) => f.endsWith('.json'));

    console.log(`Found ${jsonFiles.length} world files to migrate\n`);

    let migrated = 0;
    let skipped = 0;
    let errors = 0;

    for (const file of jsonFiles) {
      const checkpointName = file.replace('.json', '');
      console.log(`Processing: ${checkpointName}`);

      try {
        // Check if world already exists
        const existing = await db.world.findFirst({
          where: {
            OR: [
              { name: checkpointName },
              { id: checkpointName },
            ],
          },
        });

        if (existing) {
          console.log(`  - Skipped (already exists): ${existing.id}`);
          skipped++;
          continue;
        }

        // Read and parse world JSON
        const content = await readFile(join(WORLDS_DIR, file), 'utf-8');
        const worldData: WorldJson = JSON.parse(content);

        // Extract world name
        const worldName =
          worldData.name ||
          worldData.title ||
          (worldData.foundation as { core_premise?: { title?: string } })?.core_premise?.title ||
          checkpointName;

        // Create world in database
        const world = await db.world.create({
          data: {
            name: worldName,
            ownerId: systemUser.id,
            visibility: 'public', // Make migrated worlds public
            foundation: worldData.foundation || {},
            surface: worldData.surface || {},
            constraints: worldData.constraints || [],
            changelog: worldData.changelog || [],
            state: worldData.development?.state || 'sketch',
            version: worldData.development?.version || 1,
            createdAt: worldData.development?.created
              ? new Date(worldData.development.created)
              : new Date(),
            updatedAt: worldData.development?.last_modified
              ? new Date(worldData.development.last_modified)
              : new Date(),
          },
        });

        console.log(`  - Created: ${world.id}`);
        migrated++;
      } catch (err) {
        console.error(`  - Error: ${err instanceof Error ? err.message : String(err)}`);
        errors++;
      }
    }

    console.log('\n=== Migration Summary ===');
    console.log(`Migrated: ${migrated}`);
    console.log(`Skipped:  ${skipped}`);
    console.log(`Errors:   ${errors}`);
    console.log(`Total:    ${jsonFiles.length}`);
  } finally {
    await db.$disconnect();
  }
}

main().catch((err) => {
  console.error('Migration failed:', err);
  process.exit(1);
});
