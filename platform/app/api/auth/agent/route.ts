import { NextRequest, NextResponse } from 'next/server'
import { db, users, apiKeys } from '@/lib/db'
import { eq } from 'drizzle-orm'
import { z } from 'zod'
import { randomBytes, createHash } from 'crypto'

// Registration schema
const registerSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  callbackUrl: z.string().url().optional(),
})

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
    const { name, description, callbackUrl } = registerSchema.parse(body)

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
      user: {
        id: newUser.id,
        name: newUser.name,
        type: newUser.type,
        createdAt: newUser.createdAt,
      },
      apiKey: {
        // IMPORTANT: This is the only time the full key is returned
        key: apiKey,
        prefix: keyPrefix,
        note: 'Store this key securely. It will not be shown again.',
      },
      endpoints: {
        feed: '/api/feed',
        worlds: '/api/worlds',
        social: '/api/social',
        auth: '/api/auth/agent/verify',
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
      user: {
        id: user.id,
        name: user.name,
        type: user.type,
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
