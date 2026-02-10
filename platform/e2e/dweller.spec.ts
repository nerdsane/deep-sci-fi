import { test, expect } from '@playwright/test'
import { setupTestWorld, TestSetup } from './fixtures/test-world'

/**
 * E2E tests for dweller detail page.
 * Route: /dweller/[id]
 */

test.describe('Dweller Detail (/dweller/[id])', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('page loads with dweller name', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText('Kenji Tanaka').first()).toBeVisible()
  })

  test('role is visible', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText(/memory broker/i).first()).toBeVisible()
  })

  test('personality section renders', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText(/cautious but curious/i)).toBeVisible()
  })

  test('background section renders', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText(/grew up in the shadow/i)).toBeVisible()
  })

  test('back link to world works', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    const worldLink = page.locator('a', { hasText: new RegExp(setup.worldName, 'i') })
    await expect(worldLink).toBeVisible()
    await worldLink.click()

    await expect(page).toHaveURL(new RegExp(`/world/${setup.worldId}`))
  })
})
