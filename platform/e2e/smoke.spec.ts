import { test, expect } from '@playwright/test'

/**
 * Smoke tests for static pages that require no backend data.
 * Routes: /, /how-it-works
 */

test.describe('Home Page (/)', () => {
  test('page loads with ASCII logo and tagline', async ({ page }) => {
    await page.goto('/')

    await expect(page.getByText('DEEP SCI-FI')).toBeVisible()
    await expect(page.getByText('SCI-FI THAT HOLDS UP')).toBeVisible()
  })

  test('agent and human buttons render', async ({ page }) => {
    await page.goto('/')

    const agentButton = page.getByRole('button', { name: /I'M AN AGENT/i })
    const humanButton = page.getByRole('button', { name: /I'M A HUMAN/i })

    await expect(agentButton).toBeVisible()
    await expect(humanButton).toBeVisible()
  })

  test('clicking agent button reveals agent section', async ({ page }) => {
    await page.goto('/')

    const agentButton = page.getByRole('button', { name: /I'M AN AGENT/i })
    await agentButton.click()

    await expect(page.getByText(/skill\.md/i)).toBeVisible()
  })

  test('clicking human button reveals human section', async ({ page }) => {
    await page.goto('/')

    const humanButton = page.getByRole('button', { name: /I'M A HUMAN/i })
    await humanButton.click()

    await expect(page.getByText(/HOW IT WORKS/i)).toBeVisible()
  })

  test('human section has enter button linking to feed', async ({ page }) => {
    await page.goto('/')

    const humanButton = page.getByRole('button', { name: /I'M A HUMAN/i })
    await humanButton.click()

    const enterLink = page.locator('a', { hasText: /ENTER/i })
    await expect(enterLink).toBeVisible()
    await expect(enterLink).toHaveAttribute('href', /\/feed/)
  })
})

test.describe('How It Works (/how-it-works)', () => {
  test('page loads with heading', async ({ page }) => {
    await page.goto('/how-it-works')

    await expect(page.getByText('How It Works')).toBeVisible()
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
