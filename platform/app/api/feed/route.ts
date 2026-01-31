import { NextRequest, NextResponse } from 'next/server'
import { db, worlds, stories, conversations, dwellers, conversationMessages, users } from '@/lib/db'
import { desc, eq, and, gte } from 'drizzle-orm'

export const dynamic = 'force-dynamic'

/**
 * GET /api/feed
 * Returns mixed feed of stories, conversations, and new worlds
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const cursor = searchParams.get('cursor')
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 50)

    // Get recent activity cutoff
    const cutoff = cursor
      ? new Date(cursor)
      : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000) // Last 7 days

    // Fetch recent stories
    const recentStories = await db
      .select()
      .from(stories)
      .innerJoin(worlds, eq(stories.worldId, worlds.id))
      .where(gte(stories.createdAt, cutoff))
      .orderBy(desc(stories.createdAt))
      .limit(limit)

    // Fetch active conversations
    const activeConversations = await db
      .select()
      .from(conversations)
      .innerJoin(worlds, eq(conversations.worldId, worlds.id))
      .where(and(eq(conversations.isActive, true), gte(conversations.updatedAt, cutoff)))
      .orderBy(desc(conversations.updatedAt))
      .limit(limit)

    // Fetch new worlds
    const newWorlds = await db
      .select()
      .from(worlds)
      .where(and(eq(worlds.isActive, true), gte(worlds.createdAt, cutoff)))
      .orderBy(desc(worlds.createdAt))
      .limit(10)

    // Get messages for conversations
    const conversationIds = activeConversations.map((c) => c.platform_conversations.id)
    const messages =
      conversationIds.length > 0
        ? await db
            .select()
            .from(conversationMessages)
            .where(
              // Get last 5 messages for each conversation
              // In production, use a subquery or lateral join
              eq(conversationMessages.conversationId, conversationIds[0])
            )
            .orderBy(desc(conversationMessages.timestamp))
            .limit(5 * conversationIds.length)
        : []

    // Get dwellers for conversations
    const allParticipants = activeConversations.flatMap(
      (c) => c.platform_conversations.participants as string[]
    )
    const conversationDwellers =
      allParticipants.length > 0
        ? await db.select().from(dwellers).where(eq(dwellers.id, allParticipants[0]))
        : []

    // Build feed items
    type FeedItem = {
      type: 'story' | 'conversation' | 'world_created'
      sortDate: Date
      data: unknown
    }

    const feedItems: FeedItem[] = [
      ...recentStories.map((row) => ({
        type: 'story' as const,
        sortDate: row.platform_stories.createdAt,
        data: {
          story: {
            id: row.platform_stories.id,
            worldId: row.platform_stories.worldId,
            type: row.platform_stories.type,
            title: row.platform_stories.title,
            description: row.platform_stories.description,
            videoUrl: row.platform_stories.videoUrl,
            thumbnailUrl: row.platform_stories.thumbnailUrl,
            durationSeconds: row.platform_stories.durationSeconds,
            createdAt: row.platform_stories.createdAt,
            viewCount: row.platform_stories.viewCount,
            reactionCounts: row.platform_stories.reactionCounts,
          },
          world: {
            id: row.platform_worlds.id,
            name: row.platform_worlds.name,
            yearSetting: row.platform_worlds.yearSetting,
          },
        },
      })),
      ...activeConversations.map((row) => ({
        type: 'conversation' as const,
        sortDate: row.platform_conversations.updatedAt,
        data: {
          conversation: {
            id: row.platform_conversations.id,
            worldId: row.platform_conversations.worldId,
            participants: row.platform_conversations.participants,
            messages: messages
              .filter((m) => m.conversationId === row.platform_conversations.id)
              .slice(0, 5),
            updatedAt: row.platform_conversations.updatedAt,
          },
          world: {
            id: row.platform_worlds.id,
            name: row.platform_worlds.name,
            yearSetting: row.platform_worlds.yearSetting,
          },
          dwellers: conversationDwellers.filter((d) =>
            (row.platform_conversations.participants as string[]).includes(d.id)
          ),
        },
      })),
      ...newWorlds.map((world) => ({
        type: 'world_created' as const,
        sortDate: world.createdAt,
        data: {
          world: {
            id: world.id,
            name: world.name,
            premise: world.premise,
            yearSetting: world.yearSetting,
            causalChain: world.causalChain,
            createdAt: world.createdAt,
            dwellerCount: world.dwellerCount,
            followerCount: world.followerCount,
          },
        },
      })),
    ]

    // Sort by date and paginate
    feedItems.sort((a, b) => b.sortDate.getTime() - a.sortDate.getTime())
    const paginatedItems = feedItems.slice(0, limit)

    // Get next cursor
    const nextCursor =
      paginatedItems.length === limit
        ? paginatedItems[paginatedItems.length - 1].sortDate.toISOString()
        : undefined

    return NextResponse.json({
      items: paginatedItems.map((item) => ({
        type: item.type,
        ...(item.data as Record<string, unknown>),
      })),
      nextCursor,
    })
  } catch (error) {
    console.error('Feed API error:', error)
    return NextResponse.json({ error: 'Failed to fetch feed' }, { status: 500 })
  }
}
