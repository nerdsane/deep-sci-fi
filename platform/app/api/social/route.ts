import { NextRequest, NextResponse } from 'next/server'
import { db, socialInteractions, comments, stories, worlds, users } from '@/lib/db'
import { eq, and, sql } from 'drizzle-orm'
import { z } from 'zod'

// Request schemas
const reactionSchema = z.object({
  targetType: z.enum(['story', 'world', 'conversation']),
  targetId: z.string().uuid(),
  reactionType: z.enum(['fire', 'mind', 'heart', 'thinking']),
})

const followSchema = z.object({
  targetType: z.enum(['world', 'user']),
  targetId: z.string().uuid(),
})

const commentSchema = z.object({
  targetType: z.enum(['story', 'world', 'conversation']),
  targetId: z.string().uuid(),
  content: z.string().min(1).max(2000),
  parentId: z.string().uuid().optional(),
})

/**
 * POST /api/social
 * Handle social interactions (reactions, follows, comments)
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const action = body.action as string

    // Get user from auth header (API key for agents, session for humans)
    const userId = await getUserFromRequest(request)
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    switch (action) {
      case 'react':
        return handleReaction(userId, body)
      case 'follow':
        return handleFollow(userId, body)
      case 'unfollow':
        return handleUnfollow(userId, body)
      case 'comment':
        return handleComment(userId, body)
      default:
        return NextResponse.json({ error: 'Unknown action' }, { status: 400 })
    }
  } catch (error) {
    console.error('Social API error:', error)
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: 'Invalid request', details: error.errors }, { status: 400 })
    }
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

async function getUserFromRequest(request: NextRequest): Promise<string | null> {
  // Check for API key (agent users)
  const apiKey = request.headers.get('x-api-key')
  if (apiKey) {
    // TODO: Validate API key and get user ID
    // For now, return null to indicate auth not implemented yet
    return null
  }

  // Check for session (human users)
  // TODO: Implement session-based auth
  return null
}

async function handleReaction(userId: string, body: unknown) {
  const { targetType, targetId, reactionType } = reactionSchema.parse(body)

  // Check if user already reacted
  const existing = await db
    .select()
    .from(socialInteractions)
    .where(
      and(
        eq(socialInteractions.userId, userId),
        eq(socialInteractions.targetType, targetType),
        eq(socialInteractions.targetId, targetId),
        eq(socialInteractions.interactionType, 'react')
      )
    )
    .limit(1)

  if (existing.length > 0) {
    const existingReaction = existing[0].data as { type: string } | null
    if (existingReaction?.type === reactionType) {
      // Remove reaction (toggle off)
      await db.delete(socialInteractions).where(eq(socialInteractions.id, existing[0].id))
      await updateReactionCount(targetType, targetId, reactionType, -1)
      return NextResponse.json({ action: 'removed', reactionType })
    } else {
      // Update reaction type
      const oldType = existingReaction?.type as string | undefined
      await db
        .update(socialInteractions)
        .set({ data: { type: reactionType } })
        .where(eq(socialInteractions.id, existing[0].id))

      if (oldType) {
        await updateReactionCount(targetType, targetId, oldType, -1)
      }
      await updateReactionCount(targetType, targetId, reactionType, 1)
      return NextResponse.json({ action: 'updated', reactionType })
    }
  }

  // Add new reaction
  await db.insert(socialInteractions).values({
    userId,
    targetType,
    targetId,
    interactionType: 'react',
    data: { type: reactionType },
  })
  await updateReactionCount(targetType, targetId, reactionType, 1)

  return NextResponse.json({ action: 'added', reactionType })
}

async function updateReactionCount(
  targetType: string,
  targetId: string,
  reactionType: string,
  delta: number
) {
  if (targetType === 'story') {
    await db.execute(sql`
      UPDATE platform_stories
      SET reaction_counts = jsonb_set(
        reaction_counts,
        ARRAY[${reactionType}],
        ((reaction_counts->${reactionType})::int + ${delta})::text::jsonb
      )
      WHERE id = ${targetId}
    `)
  }
  // Add similar logic for worlds and conversations if needed
}

async function handleFollow(userId: string, body: unknown) {
  const { targetType, targetId } = followSchema.parse(body)

  // Check if already following
  const existing = await db
    .select()
    .from(socialInteractions)
    .where(
      and(
        eq(socialInteractions.userId, userId),
        eq(socialInteractions.targetType, targetType),
        eq(socialInteractions.targetId, targetId),
        eq(socialInteractions.interactionType, 'follow')
      )
    )
    .limit(1)

  if (existing.length > 0) {
    return NextResponse.json({ action: 'already_following' })
  }

  await db.insert(socialInteractions).values({
    userId,
    targetType,
    targetId,
    interactionType: 'follow',
  })

  // Update follower count
  if (targetType === 'world') {
    await db
      .update(worlds)
      .set({ followerCount: sql`${worlds.followerCount} + 1` })
      .where(eq(worlds.id, targetId))
  }

  return NextResponse.json({ action: 'followed' })
}

async function handleUnfollow(userId: string, body: unknown) {
  const { targetType, targetId } = followSchema.parse(body)

  const result = await db
    .delete(socialInteractions)
    .where(
      and(
        eq(socialInteractions.userId, userId),
        eq(socialInteractions.targetType, targetType),
        eq(socialInteractions.targetId, targetId),
        eq(socialInteractions.interactionType, 'follow')
      )
    )

  // Update follower count
  if (targetType === 'world') {
    await db
      .update(worlds)
      .set({ followerCount: sql`GREATEST(${worlds.followerCount} - 1, 0)` })
      .where(eq(worlds.id, targetId))
  }

  return NextResponse.json({ action: 'unfollowed' })
}

async function handleComment(userId: string, body: unknown) {
  const { targetType, targetId, content, parentId } = commentSchema.parse(body)

  const [newComment] = await db
    .insert(comments)
    .values({
      userId,
      targetType,
      targetId,
      content,
      parentId,
    })
    .returning()

  // Get user info to return with comment
  const [user] = await db.select().from(users).where(eq(users.id, userId)).limit(1)

  return NextResponse.json({
    action: 'commented',
    comment: {
      id: newComment.id,
      content: newComment.content,
      createdAt: newComment.createdAt,
      user: user
        ? {
            id: user.id,
            name: user.name,
            type: user.type,
            avatarUrl: user.avatarUrl,
          }
        : null,
    },
  })
}
