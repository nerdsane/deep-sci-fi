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

    await expect(page.getByRole('heading', { name: 'STORIES', exact: true })).toBeVisible()
  })

  test('story rows render', async ({ page }) => {
    await page.goto('/stories')

    // Should have Netflix-style rows
    await expect(page.getByText('TRENDING')).toBeVisible()
    await expect(page.getByText('NEW')).toBeVisible()
  })

  test('test story appears', async ({ page }) => {
    await page.goto('/stories')

    await expect(page.getByText(new RegExp(setup.storyTitle, 'i')).first()).toBeVisible()
  })
})

test.describe('Story Detail (/stories/[id])', () => {
  let setup: StorySetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestStory(request)
  })

  test('page loads with story title', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    await expect(page.getByRole('heading', { name: new RegExp(setup.storyTitle, 'i') })).toBeVisible()
  })

  test('story content is rendered', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    await expect(page.getByText(/memory trading floor hummed/i)).toBeVisible()
  })

  test('share on X button is visible', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const shareButton = page.getByRole('button', { name: /share/i })
    await expect(shareButton).toBeVisible()
  })

  test('back link to world works', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const backLink = page.locator(`a[href="/world/${setup.worldId}?tab=stories"]`)
    await expect(backLink).toBeVisible()
    await backLink.click()

    await expect(page).toHaveURL(new RegExp(`/world/${setup.worldId}`))
  })

  test('og:title meta tag is set for story', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const ogTitle = page.locator('meta[property="og:title"]')
    await expect(ogTitle).toHaveAttribute('content', new RegExp(setup.storyTitle, 'i'))
  })

  test('og:type meta tag is article', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const ogType = page.locator('meta[property="og:type"]')
    await expect(ogType).toHaveAttribute('content', 'article')
  })

  test('twitter card meta tag is set', async ({ page }) => {
    await page.goto(`/stories/${setup.storyId}`)

    const twitterCard = page.locator('meta[name="twitter:card"]')
    // Without cover image, should be 'summary'; with cover, 'summary_large_image'
    await expect(twitterCard).toHaveAttribute('content', /summary/)
  })
})
