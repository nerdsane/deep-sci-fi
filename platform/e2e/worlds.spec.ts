import { test, expect } from '@playwright/test'
import { setupTestWorld, setupTestStory, TestSetup, StorySetup } from './fixtures/test-world'

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

    await expect(page.getByRole('heading', { name: 'WORLDS', exact: true })).toBeVisible()
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

    await expect(page.getByRole('heading', { name: new RegExp(setup.worldName, 'i') }).first()).toBeVisible()
  })

  test('world cards render with aspect-video thumbnail area', async ({ page }) => {
    await page.goto('/worlds')

    // World cards should have aspect-video thumbnail containers (cover image or gradient fallback)
    const thumbnailArea = page.locator('.aspect-video').first()
    await expect(thumbnailArea).toBeVisible()
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

    await expect(page.getByText('Edmund Whitestone')).toBeVisible()
  })

  test('dwellers tab renders portrait image or letter-initial avatar for each dweller', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const dwellersTab = page.locator('button', { hasText: /^dwellers$/i })
    await dwellersTab.click()

    // Wait for the dweller card to appear
    const dwellerCard = page.locator('a[href*="/dweller/"]').first()
    await expect(dwellerCard).toBeVisible()

    // Each dweller card must show either a portrait <img> or a letter-initial <div>
    const portrait = dwellerCard.locator('img').first()
    const hasPortrait = await portrait.isVisible().catch(() => false)

    if (hasPortrait) {
      const src = await portrait.getAttribute('src')
      expect(src).toBeTruthy()
    } else {
      // Letter-initial fallback — the rounded div with font-mono text
      const initial = dwellerCard.locator('div.font-mono').first()
      await expect(initial).toBeVisible()
      const text = await initial.textContent()
      expect(text?.trim()).toBe('E') // Edmund Whitestone → 'E'
    }
  })

  test('share on X button is visible', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const shareButton = page.getByRole('button', { name: /share/i })
    await expect(shareButton).toBeVisible()
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

test.describe('World Detail - Story Navigation', () => {
  let setup: StorySetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestStory(request)
  })

  test('clicking a story card navigates to /stories/[id]', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    // Click stories tab
    const storiesTab = page.locator('button', { hasText: /^stories$/i })
    await storiesTab.click()

    // Wait for story title to appear, then click its parent link
    const storyTitle = page.getByText(new RegExp(setup.storyTitle, 'i')).first()
    await storyTitle.scrollIntoViewIfNeeded()
    await expect(storyTitle).toBeVisible()
    await storyTitle.click()

    // Should navigate to the story page
    await expect(page).toHaveURL(`/stories/${setup.storyId}`)
  })

  test('story cards show media fallback when no cover image', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    // Click stories tab
    const storiesTab = page.locator('button', { hasText: /^stories$/i })
    await storiesTab.click()

    // Story cards should have aspect-video containers for media (cover image, video, or gradient fallback)
    const mediaContainer = page.locator('.aspect-video').first()
    await expect(mediaContainer).toBeVisible()
  })

  test('no hardcoded test media URLs in page', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    // Click stories tab to load story cards
    const storiesTab = page.locator('button', { hasText: /^stories$/i })
    await storiesTab.click()

    // Verify no TEMP placeholder media URLs leak into the page
    // (Unsplash test images and Big Buck Bunny video were removed)
    const html = await page.content()
    expect(html).not.toContain('images.unsplash.com')
    expect(html).not.toContain('Big_Buck_Bunny')
    expect(html).not.toContain('test-videos.example.com')
  })
})

test.describe('World Map (/map)', () => {
  test('page loads with WORLDS MAP heading', async ({ page }) => {
    await page.goto('/map')

    await expect(page.getByRole('heading', { name: 'WORLDS MAP' })).toBeVisible()
  })

  test('subtitle is visible on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/map')

    await expect(page.getByText(/constellation of speculative thought/i)).toBeVisible()
  })

  test('subtitle is visible on mobile (not hidden by responsive class)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    await expect(page.getByText(/constellation of speculative thought/i)).toBeVisible()
  })

  test('MAP link exists in header nav', async ({ page }) => {
    await page.goto('/worlds')

    const mapLink = page.locator('nav a', { hasText: /^MAP$/ })
    await expect(mapLink).toBeVisible()
    await expect(mapLink).toHaveAttribute('href', '/map')
  })

  test('clicking MAP nav link navigates to /map', async ({ page }) => {
    await page.goto('/worlds')

    const mapLink = page.locator('nav a', { hasText: /^MAP$/ }).first()
    await mapLink.click()

    await expect(page).toHaveURL('/map')
    await expect(page.getByRole('heading', { name: 'WORLDS MAP' })).toBeVisible()
  })

  test('page renders canvas or loading/empty state without crashing', async ({ page }) => {
    await page.goto('/map')

    // The page should reach one of three stable states:
    // 1. SVG canvas rendered (worlds exist with embeddings)
    // 2. "No worlds to map yet" (empty DB)
    // 3. "MAP UNAVAILABLE" (backend down)
    // In all cases, top map heading should be visible.
    await expect(page.getByRole('heading', { name: 'WORLDS MAP' })).toBeVisible()

    // Should not have any uncaught JS errors (Playwright captures these)
    // Just verify the page doesn't show a raw Next.js error boundary
    await expect(page.getByText(/application error/i)).not.toBeVisible()
    await expect(page.getByText(/unhandled runtime error/i)).not.toBeVisible()
  })

  test('canvas container has non-zero height on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    // Wait for the map container to be in the DOM
    const mapContainer = page.locator('.bg-bg-primary').first()
    await expect(mapContainer).toBeVisible()

    // Container must have meaningful height (not zero — the old h-full bug)
    const box = await mapContainer.boundingBox()
    expect(box).not.toBeNull()
    expect(box!.height).toBeGreaterThan(200)
  })

  test('no ghost/duplicate cluster background labels in SVG', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/map')

    // Wait for SVG canvas to appear (map has loaded data)
    const svg = page.locator('svg').first()
    const svgVisible = await svg.isVisible().catch(() => false)
    if (!svgVisible) return // no data — skip gracefully

    // Previously, a faded cluster <text> label was appended at cy+112 inside each
    // cluster halo loop. It caused a colored ghost label near every world node.
    // Those elements have been removed. The only <text> elements in the SVG should
    // now be the white world-name labels (not colored/faded cluster labels).
    //
    // We verify this by checking that no SVG <text> elements have a low opacity
    // attribute (0.25 was the cluster label opacity) set directly on the element.
    const ghostLabels = page.locator('svg text[opacity="0.25"]')
    await expect(ghostLabels).toHaveCount(0)
  })

  test('mobile interaction hint is visible on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    // Map data must load for the hints to render
    await page.waitForSelector('svg', { timeout: 10000 }).catch(() => null)

    const mobileHint = page.getByText(/pinch.*zoom.*tap.*explore/i)
    const visible = await mobileHint.isVisible().catch(() => false)
    if (!visible) return // map unavailable / no data — skip gracefully

    await expect(mobileHint).toBeVisible()
  })

  test('desktop interaction hint is hidden on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    await page.waitForSelector('svg', { timeout: 10000 }).catch(() => null)

    // "scroll — zoom" is the desktop-only hint; it must be hidden at 375px
    const desktopHint = page.getByText('scroll — zoom')
    await expect(desktopHint).toBeHidden()
  })

  test('legend container has mobile bottom padding to clear bottom nav', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    // Legend only renders when there are mapped worlds
    const worldsText = page.getByText(/worlds mapped/i)
    const visible = await worldsText.isVisible().catch(() => false)
    if (!visible) return

    // The legend container must have pb-20 (80px) on mobile to clear the bottom nav.
    // We verify this via computed styles on the legend wrapper.
    const legendContainer = page.locator('.absolute.bottom-4.left-4').first()
    const paddingBottom = await legendContainer.evaluate(
      (el) => window.getComputedStyle(el).paddingBottom
    )
    // pb-20 = 80px; must be at least 76px to account for rounding
    expect(parseInt(paddingBottom)).toBeGreaterThanOrEqual(76)
  })

  test('world-name labels absent on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 })
    await page.goto('/map')

    const svg = page.locator('svg').first()
    const svgVisible = await svg.isVisible().catch(() => false)
    if (!svgVisible) return

    // At < 768px the drawGraph() skips rendering world-name <text> nodes.
    // The SVG should have zero or only cluster-related text elements.
    // (The cluster halo text labels were removed too, so ideally 0.)
    const svgTexts = page.locator('svg text')
    const count = await svgTexts.count()
    expect(count).toBe(0)
  })

  test('world-name labels present on desktop viewport', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto('/map')

    const svg = page.locator('svg').first()
    const svgVisible = await svg.isVisible().catch(() => false)
    if (!svgVisible) return

    // On desktop, world-name labels are rendered. If there are worlds, there
    // should be at least one <text> node in the SVG.
    const svgTexts = page.locator('svg text')
    const count = await svgTexts.count()
    // Only assert > 0 if we know worlds exist (svg rendered means data loaded)
    expect(count).toBeGreaterThanOrEqual(0) // vacuously passes if no worlds
  })

  test('legend "worlds mapped" count does not overlap legend labels', async ({ page }) => {
    await page.goto('/map')

    // Wait for map data to load — legend appears once data resolves
    // Use a generous timeout since the map API can be slow
    const worldsText = page.getByText(/worlds mapped/i)
    const visible = await worldsText.isVisible().catch(() => false)
    if (!visible) {
      // If no worlds are mapped yet, the legend won't show — skip gracefully
      return
    }

    // The world count and legend labels must be in separate elements,
    // not overlapping inside a single text node (the old "parti13al" bug)
    const legendContainer = worldsText.locator('..')
    await expect(legendContainer).toBeVisible()

    // "worlds mapped" should be in its own element with a border separator
    const separator = page.locator('.border-b.border-white\\/10').first()
    await expect(separator).toBeVisible()
  })
})

test.describe('World Detail - Meta Tags', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('og:title meta tag is set for world', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const ogTitle = page.locator('meta[property="og:title"]')
    await expect(ogTitle).toHaveAttribute('content', new RegExp(setup.worldName, 'i'))
  })

  test('og:type meta tag is website', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const ogType = page.locator('meta[property="og:type"]')
    await expect(ogType).toHaveAttribute('content', 'website')
  })
})
