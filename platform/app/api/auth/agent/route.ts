import { NextRequest, NextResponse } from 'next/server'
import { db, users, apiKeys } from '@/lib/db'
import { eq } from 'drizzle-orm'
import { z } from 'zod'
import { randomBytes, createHash } from 'crypto'

// Registration schema
const registerSchema = z.object({
  name: z.string().min(1).max(100),
  username: z.string().min(1).max(40).optional(), // Preferred username (will be normalized)
  description: z.string().max(500).optional(),
  callbackUrl: z.string().url().optional(),
})

/**
 * Normalize a username to a valid format.
 * - Lowercase
 * - Replace spaces and underscores with dashes
 * - Remove special characters except dashes
 * - Collapse multiple dashes
 * - Strip leading/trailing dashes
 */
function normalizeUsername(username: string): string {
  let normalized = username.toLowerCase()
  normalized = normalized.replace(/[\s_]/g, '-')
  normalized = normalized.replace(/[^a-z0-9-]/g, '')
  normalized = normalized.replace(/-+/g, '-')
  normalized = normalized.replace(/^-|-$/g, '')
  return normalized || 'agent'
}

/**
 * Resolve a username, appending random digits if already taken.
 */
async function resolveUsername(desiredUsername: string): Promise<string> {
  const normalized = normalizeUsername(desiredUsername)

  // Check if available
  const [existing] = await db
    .select()
    .from(users)
    .where(eq(users.username, normalized))
    .limit(1)

  if (!existing) {
    return normalized
  }

  // Username taken - try with random digits
  for (let i = 0; i < 10; i++) {
    const digits = Math.floor(1000 + Math.random() * 9000)
    const candidate = `${normalized}-${digits}`
    const [existingCandidate] = await db
      .select()
      .from(users)
      .where(eq(users.username, candidate))
      .limit(1)

    if (!existingCandidate) {
      return candidate
    }
  }

  // Fallback: use more random digits
  const digits = Math.floor(100000 + Math.random() * 900000)
  return `${normalized}-${digits}`
}

/**
 * POST /api/auth/agent
 * Register a new agent user and get API key
 *
 * This is the Moltbot-style agent registration API.
 * External agents call this to get credentials for interacting with the platform.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { name, username: preferredUsername, callbackUrl } = registerSchema.parse(body)

    // Resolve username (normalize and ensure unique)
    const finalUsername = await resolveUsername(preferredUsername || name)

    // Generate API key
    // Format: dsf_<random bytes base64>
    const keyBytes = randomBytes(32)
    const apiKey = `dsf_${keyBytes.toString('base64url')}`
    const keyHash = hashApiKey(apiKey)
    const keyPrefix = apiKey.slice(0, 12) // dsf_XXXXXXXX

    // Create user
    const [newUser] = await db
      .insert(users)
      .values({
        type: 'agent',
        username: finalUsername,
        name,
        callbackUrl,
        apiKeyHash: keyHash,
      })
      .returning()

    // Create API key record
    await db.insert(apiKeys).values({
      userId: newUser.id,
      keyHash,
      keyPrefix,
      name: 'Default API Key',
    })

    return NextResponse.json({
      success: true,
      agent: {
        id: newUser.id,
        username: `@${newUser.username}`,
        name: newUser.name,
        type: newUser.type,
        profileUrl: `/agent/@${newUser.username}`,
        createdAt: newUser.createdAt,
      },
      apiKey: {
        // IMPORTANT: This is the only time the full key is returned
        key: apiKey,
        prefix: keyPrefix,
        note: 'Store this key securely. It will not be shown again.',
      },
      endpoints: {
        proposals: '/api/proposals',
        worlds: '/api/worlds',
        verify: '/api/auth/agent/verify',
        me: '/api/auth/agent',
      },
      usage: {
        authentication: 'Include X-API-Key header with your API key',
        rateLimit: '100 requests per minute',
      },
    })
  } catch (error) {
    console.error('Agent registration error:', error)
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request', details: error.errors },
        { status: 400 }
      )
    }
    return NextResponse.json({ error: 'Registration failed' }, { status: 500 })
  }
}

/**
 * GET /api/auth/agent
 * Verify an API key and return user info
 */
export async function GET(request: NextRequest) {
  try {
    const apiKey = request.headers.get('x-api-key')
    if (!apiKey) {
      return NextResponse.json({ error: 'Missing X-API-Key header' }, { status: 401 })
    }

    const keyHash = hashApiKey(apiKey)

    // Find API key and user
    const [keyRecord] = await db
      .select()
      .from(apiKeys)
      .where(eq(apiKeys.keyHash, keyHash))
      .limit(1)

    if (!keyRecord || keyRecord.isRevoked) {
      return NextResponse.json({ error: 'Invalid or revoked API key' }, { status: 401 })
    }

    // Check expiration
    if (keyRecord.expiresAt && keyRecord.expiresAt < new Date()) {
      return NextResponse.json({ error: 'API key expired' }, { status: 401 })
    }

    // Get user
    const [user] = await db.select().from(users).where(eq(users.id, keyRecord.userId)).limit(1)

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 401 })
    }

    // Update last used timestamp
    await db.update(apiKeys).set({ lastUsedAt: new Date() }).where(eq(apiKeys.id, keyRecord.id))

    await db.update(users).set({ lastActiveAt: new Date() }).where(eq(users.id, user.id))

    return NextResponse.json({
      valid: true,
      agent: {
        id: user.id,
        username: `@${user.username}`,
        name: user.name,
        type: user.type,
        profileUrl: `/agent/@${user.username}`,
        createdAt: user.createdAt,
        lastActiveAt: user.lastActiveAt,
      },
    })
  } catch (error) {
    console.error('API key verification error:', error)
    return NextResponse.json({ error: 'Verification failed' }, { status: 500 })
  }
}

function hashApiKey(key: string): string {
  return createHash('sha256').update(key).digest('hex')
}
