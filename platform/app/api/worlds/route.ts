import { NextRequest, NextResponse } from 'next/server'
import { db, worlds, dwellers, stories } from '@/lib/db'
import { desc, eq, count } from 'drizzle-orm'

export const dynamic = 'force-dynamic'

/**
 * GET /api/worlds
 * Returns list of active worlds for catalog browsing
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = Math.min(parseInt(searchParams.get('limit') || '20'), 50)
    const offset = parseInt(searchParams.get('offset') || '0')
    const sort = searchParams.get('sort') || 'recent' // recent, popular, active

    // Build query based on sort
    let orderBy
    switch (sort) {
      case 'popular':
        orderBy = desc(worlds.followerCount)
        break
      case 'active':
        orderBy = desc(worlds.updatedAt)
        break
      default:
        orderBy = desc(worlds.createdAt)
    }

    const worldList = await db
      .select()
      .from(worlds)
      .where(eq(worlds.isActive, true))
      .orderBy(orderBy)
      .limit(limit)
      .offset(offset)

    // Get total count for pagination
    const totalResult = await db
      .select({ count: count() })
      .from(worlds)
      .where(eq(worlds.isActive, true))

    return NextResponse.json({
      worlds: worldList.map((w) => ({
        id: w.id,
        name: w.name,
        premise: w.premise,
        yearSetting: w.yearSetting,
        causalChain: w.causalChain,
        createdAt: w.createdAt,
        dwellerCount: w.dwellerCount,
        storyCount: w.storyCount,
        followerCount: w.followerCount,
      })),
      total: totalResult[0]?.count || 0,
      hasMore: offset + limit < (totalResult[0]?.count || 0),
    })
  } catch (error) {
    console.error('Worlds API error:', error)
    return NextResponse.json({ error: 'Failed to fetch worlds' }, { status: 500 })
  }
}
