import { test, expect } from '@playwright/test'
import { setupTestProposal, ProposalSetup } from './fixtures/test-world'

/**
 * E2E tests for proposals listing and detail pages.
 * Routes: /proposals, /proposal/[id]
 */

test.describe('Proposals Listing (/proposals)', () => {
  let setup: ProposalSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestProposal(request)
  })

  test('page loads with heading', async ({ page }) => {
    await page.goto('/proposals')

    await expect(page.getByText('PROPOSALS')).toBeVisible()
  })

  test('status filter tabs render', async ({ page }) => {
    await page.goto('/proposals')

    const filters = ['ALL', 'PENDING', 'APPROVED', 'REJECTED']
    for (const filter of filters) {
      await expect(
        page.locator('button', { hasText: new RegExp(`^${filter}$`, 'i') })
      ).toBeVisible()
    }
  })

  test('clicking filter changes list', async ({ page }) => {
    await page.goto('/proposals')

    const pendingFilter = page.locator('button', { hasText: /^PENDING$/i })
    await pendingFilter.click()

    // Test proposal should be visible under PENDING
    await expect(page.getByText(new RegExp(setup.proposalName, 'i'))).toBeVisible()
  })

  test('test proposal card is visible', async ({ page }) => {
    await page.goto('/proposals')

    await expect(page.getByText(new RegExp(setup.proposalName, 'i'))).toBeVisible()
  })
})

test.describe('Proposal Detail (/proposal/[id])', () => {
  let setup: ProposalSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestProposal(request)
  })

  test('page loads with proposal name', async ({ page }) => {
    await page.goto(`/proposal/${setup.proposalId}`)

    await expect(page.getByText(new RegExp(setup.proposalName, 'i'))).toBeVisible()
  })

  test('status badge is visible', async ({ page }) => {
    await page.goto(`/proposal/${setup.proposalId}`)

    await expect(page.getByText(/PENDING/i).first()).toBeVisible()
  })

  test('causal chain is rendered', async ({ page }) => {
    await page.goto(`/proposal/${setup.proposalId}`)

    // The causal chain should show the year markers
    await expect(page.getByText('2030')).toBeVisible()
    await expect(page.getByText(/brain-computer interface/i)).toBeVisible()
  })

  test('premise section is visible', async ({ page }) => {
    await page.goto(`/proposal/${setup.proposalId}`)

    await expect(page.getByText(/quantum entanglement/i)).toBeVisible()
  })

  test('review status or legacy validation info is shown', async ({ page }) => {
    await page.goto(`/proposal/${setup.proposalId}`)

    // Should show either new review status (for critical_review) or legacy validation (for legacy)
    // For now, legacy proposals show "VALIDATION" section, new ones show "REVIEW STATUS"
    const hasValidationSection = await page.getByText('VALIDATION').isVisible().catch(() => false)
    const hasReviewSection = await page.getByText('REVIEW STATUS').isVisible().catch(() => false)

    expect(hasValidationSection || hasReviewSection).toBeTruthy()
  })
})
