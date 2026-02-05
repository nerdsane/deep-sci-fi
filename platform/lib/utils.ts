/**
 * Utility functions for the Deep Sci-Fi platform.
 */

/**
 * Parse date strings as UTC.
 * Backend returns ISO dates without timezone, so we append Z to treat as UTC.
 */
export function parseUtcDate(dateStr: string | undefined | null): Date {
  if (!dateStr) return new Date()
  // Append Z if no timezone specified to treat as UTC
  const normalized = dateStr.endsWith('Z') || dateStr.includes('+') || dateStr.includes('-', 10)
    ? dateStr
    : dateStr + 'Z'
  return new Date(normalized)
}

/**
 * Format a date string as relative time (e.g., "2h ago", "3d ago").
 */
export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Invalid date'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}
