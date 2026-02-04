/**
 * Render template tokens in markdown content with environment-aware URLs.
 *
 * Tokens:
 *   {{SITE_URL}} - Frontend URL, no trailing slash (e.g. https://deep-sci-fi.world)
 *   {{API_URL}}  - Full API URL with /api (e.g. https://api.deep-sci-fi.world/api)
 *   {{API_BASE}} - API domain without /api (e.g. https://api.deep-sci-fi.world)
 */
export function renderTemplate(template: string): string {
  const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000').replace(/\/$/, '')
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api').replace(/\/$/, '')
  const apiBase = apiUrl.replace(/\/api$/, '')

  return template
    .replaceAll('{{SITE_URL}}', siteUrl)
    .replaceAll('{{API_URL}}', apiUrl)
    .replaceAll('{{API_BASE}}', apiBase)
}
