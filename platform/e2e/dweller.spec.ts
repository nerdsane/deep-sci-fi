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

    await expect(page.getByText('Edmund Whitestone').first()).toBeVisible()
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

  test('avatar area renders portrait image or letter-initial fallback', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    // Either a portrait <img> or the letter-initial <div> must be visible in the header
    const header = page.locator('.glass-cyan').first()
    await expect(header).toBeVisible()

    const portrait = header.locator('img').first()
    const hasPortrait = await portrait.isVisible().catch(() => false)

    if (hasPortrait) {
      // Portrait loaded — verify it has a src
      const src = await portrait.getAttribute('src')
      expect(src).toBeTruthy()
    } else {
      // Fallback letter-initial div must show the first character of the name
      const initial = header.locator('div.font-mono').first()
      await expect(initial).toBeVisible()
      const text = await initial.textContent()
      expect(text?.trim()).toBe('E') // Edmund Whitestone → 'E'
    }
  })
})
