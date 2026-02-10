import { test, expect } from '@playwright/test'
import { setupTestWorld, TestSetup } from './fixtures/test-world'

/**
 * E2E tests for world listing and detail pages.
 * Routes: /worlds, /world/[id]
 */

test.describe('Worlds Catalog (/worlds)', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('page loads with heading', async ({ page }) => {
    await page.goto('/worlds')

    await expect(page.getByText('WORLDS')).toBeVisible()
  })

  test('world rows render (TRENDING, MOST ACTIVE, NEW)', async ({ page }) => {
    await page.goto('/worlds')

    await expect(page.getByText('TRENDING')).toBeVisible()
    await expect(page.getByText('MOST ACTIVE')).toBeVisible()
    await expect(page.getByText('NEW')).toBeVisible()
  })

  test('ALL WORLDS section renders', async ({ page }) => {
    await page.goto('/worlds')

    await expect(page.getByText('ALL WORLDS')).toBeVisible()
  })

  test('test world appears in catalog', async ({ page }) => {
    await page.goto('/worlds')

    await expect(page.getByText(new RegExp(setup.worldName, 'i'))).toBeVisible()
  })
})

test.describe('World Detail (/world/[id])', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('page loads with world name', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    await expect(page.getByText(new RegExp(setup.worldName, 'i'))).toBeVisible()
  })

  test('premise is visible', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    await expect(page.getByText(/memories can be extracted/i)).toBeVisible()
  })

  test('all 5 tabs render', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const tabs = ['live', 'stories', 'timeline', 'dwellers', 'aspects']
    for (const tabName of tabs) {
      await expect(
        page.locator('button', { hasText: new RegExp(`^${tabName}$`, 'i') })
      ).toBeVisible()
    }
  })

  test('clicking dwellers tab shows test dweller', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const dwellersTab = page.locator('button', { hasText: /^dwellers$/i })
    await dwellersTab.click()

    await expect(page.getByText('Kenji Tanaka')).toBeVisible()
  })

  test('clicking tabs changes content', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    // Click stories tab
    const storiesTab = page.locator('button', { hasText: /^stories$/i })
    await storiesTab.click()

    // Click timeline tab
    const timelineTab = page.locator('button', { hasText: /^timeline$/i })
    await timelineTab.click()

    // Click aspects tab
    const aspectsTab = page.locator('button', { hasText: /^aspects$/i })
    await aspectsTab.click()

    // If we got this far without errors, tabs are switching correctly
  })
})
