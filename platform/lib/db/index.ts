import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import * as schema from './schema'

// Connection string from environment
const connectionString = process.env.DATABASE_URL!

// Detect if running in serverless/edge environment (Vercel)
const isServerless = process.env.VERCEL === '1' || process.env.VERCEL_ENV

// Create postgres client with settings optimized for the environment
const client = postgres(connectionString, {
  // Fewer connections in serverless to avoid pool exhaustion
  max: isServerless ? 1 : 10,
  idle_timeout: isServerless ? 0 : 20,
  connect_timeout: 10,
  // Required for Supabase pooler (pgbouncer in transaction mode)
  prepare: false,
})

// Create drizzle instance with schema
export const db = drizzle(client, { schema })

// Export schema for use elsewhere
export * from './schema'
