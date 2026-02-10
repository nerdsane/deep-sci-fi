import { test, expect } from '@playwright/test'
import { setupTestStory, StorySetup } from './fixtures/test-world'

/**
 * E2E tests for story listing and detail pages.
 * Routes: /stories, /stories/[id]
 */

test.describe('Stories Catalog (/stories)', () => {
  let setup: StorySetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestStory(request)
  })

  test('page loads with heading', async ({ page }) => {
    await page.goto('/stories')

    await expect(page.getByText('STORIES')).toBeVisible()
  })

  test('story rows render', async ({ page }) => {
    await page.goto('/stories')

    // Should have Netflix-style rows
    await expect(page.getByText('TRENDING')).toBeVisible()
    await expect(page.getByText('NEW')).toBeVisible()
  })

  test('test story appears', async ({ page }) => {
    await page.goto('/stories')

    await expect(page.getByText(new RegExp(setup.storyTitle, 'i'))).toBeVisible()
  })
})

test.describe('Story Detail (/stories/[id])', () => {
  let setup: StorySetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestStory(request)
  })

  test('page loads with story title', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    await expect(page.getByText(new RegExp(setup.storyTitle, 'i'))).toBeVisible()
  })

  test('story content is rendered', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    await expect(page.getByText(/memory trading floor hummed/i)).toBeVisible()
  })

  test('back link to world works', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const worldLink = page.locator('a', { hasText: new RegExp(setup.worldName, 'i') })
    await expect(worldLink).toBeVisible()
    await worldLink.click()

    await expect(page).toHaveURL(new RegExp(`/world/${setup.worldId}`))
  })
})
