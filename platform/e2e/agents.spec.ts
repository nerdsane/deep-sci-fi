import { test, expect } from '@playwright/test'
import { setupTestWorld, TestSetup } from './fixtures/test-world'

/**
 * E2E tests for agent listing and profile pages.
 * Routes: /agents, /agent/[id]
 */

test.describe('Agents Listing (/agents)', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('page loads with heading', async ({ page }) => {
    await page.goto('/agents')

    await expect(page.getByRole('heading', { name: 'AGENTS', exact: true })).toBeVisible()
  })

  test('platform stats banner is visible', async ({ page }) => {
    await page.goto('/agents')

    // Stats banner shows aggregate counts
    await expect(page.getByText(/Agents/i).first()).toBeVisible()
    await expect(page.getByText(/Worlds/i).first()).toBeVisible()
  })

  test('agent cards render', async ({ page }) => {
    await page.goto('/agents')

    // Our test creator agent should appear
    await expect(page.getByText(/e2e test creator/i).first()).toBeVisible()
  })
})

test.describe('Agent Profile (/agent/[id])', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('agent name is visible', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    await expect(page.getByTestId('agent-name')).toBeVisible()
    await expect(page.getByText(/e2e test creator/i)).toBeVisible()
  })

  test('username is displayed', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    await expect(page.getByText(/@e2e-/i)).toBeVisible()
  })

  test('stats overview renders', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    // Should show stat cards
    await expect(page.getByText(/WORLDS/i).first()).toBeVisible()
  })

  test('proposals section shows created world', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    await expect(page.getByTestId('agent-proposals')).toBeVisible()
    await expect(page.getByText(new RegExp(setup.worldName, 'i'))).toBeVisible()
  })

  test('dwellers section shows inhabited dweller', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    await expect(page.getByText('Edmund Whitestone')).toBeVisible()
  })
})
