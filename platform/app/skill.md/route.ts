import { readFile } from 'fs/promises'
import { join } from 'path'
import { createHash } from 'crypto'
import { renderTemplate } from '@/lib/template'

const SKILL_VERSION = '1.1.0'

export async function GET() {
  const filePath = join(process.cwd(), 'public', 'skill.md')

  try {
    const raw = await readFile(filePath, 'utf-8')
    const rendered = renderTemplate(raw)
    const etag = createHash('md5').update(rendered).digest('hex')

    return new Response(rendered, {
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'X-Skill-Version': SKILL_VERSION,
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
