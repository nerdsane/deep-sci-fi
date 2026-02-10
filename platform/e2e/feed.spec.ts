import { test, expect } from '@playwright/test'
import { API_BASE, setupTestWorld, TestSetup } from './fixtures/test-world'

/**
 * E2E tests for the live feed page.
 * Route: /feed
 */

test.describe('Live Feed (/feed)', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)

    // Create activity so the feed has content
    await request.post(`${API_BASE}/dwellers/${setup.dwellerId}/act`, {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        action_type: 'observe',
        content: 'The neon signs of the trading district flicker in the rain.',
      },
    })
  })

  test('page loads with heading', async ({ page }) => {
    await page.goto('/feed')

    await expect(page.getByText('LIVE')).toBeVisible()
  })

  test('activity items render', async ({ page }) => {
    await page.goto('/feed')

    // Feed should have at least one activity item from our setup
    await expect(page.getByText(/neon signs.*trading district/i)).toBeVisible()
  })

  test('activity items link to worlds or dwellers', async ({ page }) => {
    await page.goto('/feed')

    // There should be links within the feed items
    const feedLinks = page.locator('a[href*="/world/"], a[href*="/dweller/"]')
    await expect(feedLinks.first()).toBeVisible()
  })
})
