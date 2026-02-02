#!/usr/bin/env npx tsx
/**
 * Schema Sync Check
 *
 * Compares the hand-maintained Drizzle schema against the actual database schema.
 * This catches drift between the Next.js Drizzle schema and the SQLAlchemy/Alembic
 * schema that is the source of truth.
 *
 * Usage:
 *   DATABASE_URL=... npx tsx scripts/check-schema-sync.ts
 *
 * In CI:
 *   bun run db:check-schema
 */

import postgres from 'postgres'
import * as schema from '../lib/db/schema'

interface ColumnInfo {
  column_name: string
  data_type: string
  is_nullable: string
  column_default: string | null
}

interface TableInfo {
  table_name: string
}

async function main() {
  const databaseUrl = process.env.DATABASE_URL
  if (!databaseUrl) {
    console.error('DATABASE_URL environment variable is required')
    process.exit(1)
  }

  const sql = postgres(databaseUrl, { max: 1 })

  try {
    // Get all platform_ tables from the database
    const dbTables = await sql<TableInfo[]>`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name LIKE 'platform_%'
      ORDER BY table_name
    `

    // Get columns for each table
    const dbSchema: Record<string, Set<string>> = {}
    for (const table of dbTables) {
      const columns = await sql<ColumnInfo[]>`
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = ${table.table_name}
        ORDER BY ordinal_position
      `
      dbSchema[table.table_name] = new Set(columns.map((c) => c.column_name))
    }

    // Extract tables and columns from Drizzle schema
    const drizzleSchema: Record<string, Set<string>> = {}

    // Get all exported tables from schema
    const schemaExports = schema as Record<string, unknown>
    for (const [key, value] of Object.entries(schemaExports)) {
      // Check if it's a table (has a Symbol with the table name)
      if (
        value &&
        typeof value === 'object' &&
        '_' in value &&
        'name' in (value as { _: { name: string } })._
      ) {
        const tableDef = value as {
          _: { name: string; columns: Record<string, { name: string }> }
        }
        const tableName = tableDef._.name
        const columns = Object.values(tableDef._.columns || {}).map((c) => c.name)
        drizzleSchema[tableName] = new Set(columns)
      }
    }

    // Compare schemas
    let hasErrors = false
    const errors: string[] = []
    const warnings: string[] = []

    // Check for tables in DB but not in Drizzle
    for (const tableName of Object.keys(dbSchema)) {
      if (!drizzleSchema[tableName]) {
        warnings.push(`Table '${tableName}' exists in DB but not in Drizzle schema`)
      }
    }

    // Check for tables in Drizzle but not in DB
    for (const tableName of Object.keys(drizzleSchema)) {
      if (!dbSchema[tableName]) {
        errors.push(`Table '${tableName}' in Drizzle schema but missing from DB`)
        hasErrors = true
      }
    }

    // Check columns for each table that exists in both
    for (const tableName of Object.keys(drizzleSchema)) {
      if (!dbSchema[tableName]) continue

      const drizzleCols = drizzleSchema[tableName]
      const dbCols = dbSchema[tableName]

      // Columns in DB but not in Drizzle
      Array.from(dbCols).forEach((col) => {
        if (!drizzleCols.has(col)) {
          errors.push(`Column '${tableName}.${col}' exists in DB but missing from Drizzle schema`)
          hasErrors = true
        }
      })

      // Columns in Drizzle but not in DB
      Array.from(drizzleCols).forEach((col) => {
        if (!dbCols.has(col)) {
          errors.push(`Column '${tableName}.${col}' in Drizzle schema but missing from DB`)
          hasErrors = true
        }
      })
    }

    // Report results
    console.log('\n=== Schema Sync Check ===\n')

    if (warnings.length > 0) {
      console.log('Warnings (tables in DB not tracked by Drizzle):')
      for (const w of warnings) {
        console.log(`  ⚠️  ${w}`)
      }
      console.log()
    }

    if (errors.length > 0) {
      console.log('Errors (schema mismatch):')
      for (const e of errors) {
        console.log(`  ❌ ${e}`)
      }
      console.log()
    }

    if (hasErrors) {
      console.log('Schema sync check FAILED')
      console.log('\nTo fix:')
      console.log('  1. Update lib/db/schema.ts to match the database')
      console.log('  2. Or run: bun run db:pull to introspect the DB')
      process.exit(1)
    } else {
      console.log('✅ Schema sync check passed')
      console.log(`   ${Object.keys(drizzleSchema).length} tables verified`)
    }
  } finally {
    await sql.end()
  }
}

main().catch((err) => {
  if (err.code === 'ECONNREFUSED') {
    console.error('Schema check failed: Could not connect to database')
    console.error('Make sure PostgreSQL is running and DATABASE_URL is correct')
  } else {
    console.error('Schema check failed:', err.message || err)
  }
  process.exit(1)
})
