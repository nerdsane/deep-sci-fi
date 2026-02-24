import { test, expect } from '@playwright/test'
import { setupTestAspect, AspectSetup } from './fixtures/test-world'

/**
 * E2E tests for aspect detail page.
 * Route: /aspect/[id]
 */

test.describe('Aspect Detail (/aspect/[id])', () => {
  let setup: AspectSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestAspect(request)
  })

  test('page loads with aspect title', async ({ page }) => {
    await page.goto(`/aspect/${setup.aspectId}`)

    await expect(page.getByText(new RegExp(setup.aspectTitle, 'i'))).toBeVisible()
  })

  test('status badge shows approved', async ({ page }) => {
    await page.goto(`/aspect/${setup.aspectId}`)

    await expect(page.getByText(/APPROVED/i).first()).toBeVisible()
  })

  test('type label is visible', async ({ page }) => {
    await page.goto(`/aspect/${setup.aspectId}`)

    await expect(page.getByText(/technology/i).first()).toBeVisible()
  })

  test('content is rendered', async ({ page }) => {
    await page.goto(`/aspect/${setup.aspectId}`)

    await expect(page.getByText(/neural dust/i).first()).toBeVisible()
  })

  test('back link to world works', async ({ page }) => {
    await page.goto(`/aspect/${setup.aspectId}`)

    const worldLink = page.locator(`a[href="/world/${setup.worldId}?tab=aspects"]`)
    await expect(worldLink).toBeVisible()
    await worldLink.click()

    await expect(page).toHaveURL(new RegExp(`/world/${setup.worldId}`))
  })
})
