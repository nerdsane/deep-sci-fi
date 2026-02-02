import type { Config } from 'drizzle-kit'

export default {
  schema: './lib/db/schema.ts',
  out: './drizzle',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  // Introspection outputs to a separate directory for comparison
  introspect: {
    casing: 'camel',
  },
} satisfies Config
