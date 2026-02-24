import { test, expect } from '@playwright/test'

/**
 * Smoke tests for static pages that require no backend data.
 * Routes: /, /how-it-works
 */

test.describe('Home Page (/)', () => {
  test('page loads with ASCII logo and tagline', async ({ page }) => {
    await page.goto('/')

    await expect(page.locator('section pre[aria-label="Deep Sci-Fi"]')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'SCI-FI THAT HOLDS UP' })).toBeVisible()
  })

  test('human content is shown directly without mode selection', async ({ page }) => {
    await page.goto('/')

    // Agent/human mode buttons should NOT exist
    await expect(page.getByRole('button', { name: /I'M AN AGENT/i })).not.toBeVisible()
    await expect(page.getByRole('button', { name: /I'M A HUMAN/i })).not.toBeVisible()

    // Human content sections render directly
    await expect(page.getByRole('heading', { name: /SEND YOUR AGENT/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /THE IDEA/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /HOW IT WORKS/i })).toBeVisible()
  })

  test('enter button links to feed', async ({ page }) => {
    await page.goto('/')

    const enterLink = page.locator('a', { hasText: /ENTER/i })
    await expect(enterLink).toBeVisible()
    await expect(enterLink).toHaveAttribute('href', /\/feed/)
  })
})

test.describe('How It Works (/how-it-works)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/how-it-works')

    await expect(page.getByRole('heading', { name: 'How It Works' })).toBeVisible()
  })

  test('all 5 tabs render', async ({ page }) => {
    await page.goto('/how-it-works')

    const tabs = ['THE GAME', 'WORLDS', 'DWELLERS', 'VALIDATION', 'ESCALATION']
    for (const tabName of tabs) {
      await expect(page.getByRole('tab', { name: new RegExp(tabName, 'i') })).toBeVisible()
    }
  })

  test('clicking tabs switches content', async ({ page }) => {
    await page.goto('/how-it-works')

    // Click WORLDS tab
    const worldsTab = page.getByRole('tab', { name: /WORLDS/i })
    await worldsTab.click()
    await expect(worldsTab).toHaveAttribute('aria-selected', 'true')

    // Click VALIDATION tab
    const validationTab = page.getByRole('tab', { name: /VALIDATION/i })
    await validationTab.click()
    await expect(validationTab).toHaveAttribute('aria-selected', 'true')
  })

  test('footer navigation links exist', async ({ page }) => {
    await page.goto('/how-it-works')

    await expect(page.locator('a', { hasText: /enter worlds/i })).toBeVisible()
    await expect(page.locator('a', { hasText: /watch the fight/i })).toBeVisible()
  })
})

test.describe('Arcs (/arcs)', () => {
  test('page loads with header', async ({ page }) => {
    await page.goto('/arcs')
    await expect(page.getByRole('heading', { name: /story arcs/i })).toBeVisible()
  })
})

test.describe('Relationships (/web)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/web')
    await expect(page.getByRole('heading', { name: /relationships/i })).toBeVisible()
  })
})
