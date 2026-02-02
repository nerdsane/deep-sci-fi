import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { parseUtcDate } from '../utils'

describe('parseUtcDate', () => {
  beforeEach(() => {
    // Use a fixed date for tests
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns current date for null input', () => {
    const result = parseUtcDate(null)
    expect(result.toISOString()).toBe('2024-01-15T12:00:00.000Z')
  })

  it('returns current date for undefined input', () => {
    const result = parseUtcDate(undefined)
    expect(result.toISOString()).toBe('2024-01-15T12:00:00.000Z')
  })

  it('returns current date for empty string', () => {
    const result = parseUtcDate('')
    expect(result.toISOString()).toBe('2024-01-15T12:00:00.000Z')
  })

  it('parses ISO string with Z timezone', () => {
    const result = parseUtcDate('2024-06-15T14:30:00Z')
    expect(result.toISOString()).toBe('2024-06-15T14:30:00.000Z')
  })

  it('parses ISO string with + timezone offset', () => {
    const result = parseUtcDate('2024-06-15T14:30:00+05:30')
    // 14:30 IST = 09:00 UTC
    expect(result.toISOString()).toBe('2024-06-15T09:00:00.000Z')
  })

  it('parses ISO string with - timezone offset', () => {
    const result = parseUtcDate('2024-06-15T14:30:00-05:00')
    // 14:30 EST = 19:30 UTC
    expect(result.toISOString()).toBe('2024-06-15T19:30:00.000Z')
  })

  it('appends Z to ISO string without timezone', () => {
    // Backend often returns dates without timezone
    const result = parseUtcDate('2024-06-15T14:30:00')
    expect(result.toISOString()).toBe('2024-06-15T14:30:00.000Z')
  })

  it('appends Z to ISO string with milliseconds but no timezone', () => {
    const result = parseUtcDate('2024-06-15T14:30:00.123')
    expect(result.toISOString()).toBe('2024-06-15T14:30:00.123Z')
  })

  it('does not double-append Z', () => {
    const result = parseUtcDate('2024-06-15T14:30:00Z')
    expect(result.toISOString()).toBe('2024-06-15T14:30:00.000Z')
  })

  it('handles date-only strings', () => {
    // Date-only strings have a - at position 4 and 7, but no time component
    // The function checks for - at position 10 (in the time component)
    const result = parseUtcDate('2024-06-15')
    // This will be treated as local time by default
    expect(result.getFullYear()).toBe(2024)
    expect(result.getMonth()).toBe(5) // June is month 5 (0-indexed)
    expect(result.getDate()).toBe(15)
  })
})
