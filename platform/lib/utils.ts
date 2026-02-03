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
