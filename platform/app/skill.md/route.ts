// This route handler overrides the static public/skill.md file.
// In Next.js App Router, route handlers take precedence over public/ files.
// The raw public/skill.md contains {{tokens}} that must be rendered server-side.
import { readFile } from 'fs/promises'
import { join } from 'path'
import { createHash } from 'crypto'
import { renderTemplate } from '@/lib/template'

/** Extract version from skill.md header line: `> Version: X.Y.Z | ...` */
function extractVersion(content: string): string {
  const match = content.match(/^>\s*Version:\s*([\d.]+)/m)
  return match?.[1] ?? '0.0.0'
}

export async function GET() {
  const filePath = join(process.cwd(), 'public', 'skill.md')

  try {
    const raw = await readFile(filePath, 'utf-8')
    const rendered = renderTemplate(raw)
    const version = extractVersion(raw)
    const etag = createHash('md5').update(rendered).digest('hex')

    return new Response(rendered, {
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'X-Skill-Version': version,
        'ETag': `"${etag}"`,
        'Cache-Control': 'public, max-age=3600, must-revalidate',
      },
    })
  } catch {
    return new Response('# Deep Sci-Fi\n\nSkill documentation not found.', {
      status: 404,
      headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
    })
  }
}
