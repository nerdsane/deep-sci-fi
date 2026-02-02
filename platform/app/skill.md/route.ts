import { NextResponse } from 'next/server'
import { readFileSync } from 'fs'
import { join } from 'path'

export async function GET() {
  try {
    const skillPath = join(process.cwd(), 'public', 'skill.md')
    const content = readFileSync(skillPath, 'utf-8')

    return new NextResponse(content, {
      status: 200,
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Cache-Control': 'public, max-age=3600',
        'X-Content-Type-Options': 'nosniff',
      },
    })
  } catch {
    return new NextResponse('# Error\n\nSkill file not found.', {
      status: 404,
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
      },
    })
  }
}
