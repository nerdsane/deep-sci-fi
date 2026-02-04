import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderTemplate } from '../template'

describe('renderTemplate', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('replaces all three tokens with defaults when env vars are unset', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', '')
    vi.stubEnv('NEXT_PUBLIC_API_URL', '')

    const result = renderTemplate('{{SITE_URL}} {{API_URL}} {{API_BASE}}')
    expect(result).toBe('http://localhost:3000 http://localhost:8000/api http://localhost:8000')
  })

  it('uses env vars when set', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', 'https://deep-sci-fi.world')
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.deep-sci-fi.world/api')

    const result = renderTemplate('Site: {{SITE_URL}}, API: {{API_URL}}, Base: {{API_BASE}}')
    expect(result).toBe(
      'Site: https://deep-sci-fi.world, API: https://api.deep-sci-fi.world/api, Base: https://api.deep-sci-fi.world'
    )
  })

  it('strips trailing slashes from env vars', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', 'https://example.com/')
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example.com/api/')

    const result = renderTemplate('{{SITE_URL}} {{API_URL}} {{API_BASE}}')
    expect(result).toBe('https://example.com https://api.example.com/api https://api.example.com')
  })

  it('replaces multiple occurrences of the same token', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', 'https://example.com')
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example.com/api')

    const result = renderTemplate('{{API_URL}}/heartbeat and {{API_URL}}/stories')
    expect(result).toBe(
      'https://api.example.com/api/heartbeat and https://api.example.com/api/stories'
    )
  })

  it('leaves non-token text unchanged', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', 'https://example.com')
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example.com/api')

    const input = 'Some text with no tokens at all.'
    expect(renderTemplate(input)).toBe(input)
  })

  it('derives API_BASE correctly when API_URL does not end in /api', () => {
    vi.stubEnv('NEXT_PUBLIC_SITE_URL', 'https://example.com')
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'https://api.example.com/v2')

    const result = renderTemplate('{{API_BASE}}')
    // /v2 does not match /api$ so API_BASE should equal the full API_URL
    expect(result).toBe('https://api.example.com/v2')
  })
})
