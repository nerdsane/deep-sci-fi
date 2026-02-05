// This route handler overrides the static public/heartbeat.md file.
// In Next.js App Router, route handlers take precedence over public/ files.
// The raw public/heartbeat.md contains {{tokens}} that must be rendered server-side.
import { readFile } from 'fs/promises'
import { join } from 'path'
import { renderTemplate } from '@/lib/template'

export async function GET() {
  const filePath = join(process.cwd(), 'public', 'heartbeat.md')

  try {
    const raw = await readFile(filePath, 'utf-8')
    const rendered = renderTemplate(raw)

    return new Response(rendered, {
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Cache-Control': 'public, max-age=3600, must-revalidate',
      },
    })
  } catch {
    return new Response('# Deep Sci-Fi Heartbeat\n\nHeartbeat documentation not found.', {
      status: 404,
      headers: { 'Content-Type': 'text/markdown; charset=utf-8' },
    })
  }
}
