import { test, expect } from '@playwright/test'
import { API_BASE, setupTestWorld, TestSetup, SAMPLE_CAUSAL_CHAIN } from './fixtures/test-world'

/**
 * E2E tests for agent visibility features.
 *
 * These tests verify that humans can see agent activity through the UI.
 * They combine API calls (simulating agent actions) with browser automation
 * (verifying human visibility).
 */

test.describe('Agent Visibility - World Activity Feed', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)

    // Take actions to populate activity feed
    await request.post(`${API_BASE}/dwellers/${setup.dwellerId}/act`, {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        action_type: 'observe',
        content: 'The memory trading floor buzzes with activity.',
      },
    })

    await request.post(`${API_BASE}/dwellers/${setup.dwellerId}/act`, {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        action_type: 'speak',
        target: 'fellow trader',
        content: 'Have you seen the new memory encryption protocols?',
      },
    })
  })

  test('world page shows live tab', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    // Tab was renamed from "activity" to "live"
    const liveTab = page.locator('button', { hasText: /^live$/i })
    await expect(liveTab).toBeVisible()
    await liveTab.click()

    // Verify activity feed content
    await expect(page.getByText('The memory trading floor buzzes')).toBeVisible()
  })

  test('activity feed shows dweller actions', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const liveTab = page.locator('button', { hasText: /^live$/i })
    await liveTab.click()

    // Check for speech action
    await expect(page.getByText('memory encryption protocols')).toBeVisible()
    // Check for action type label
    await expect(page.getByText('speak').first()).toBeVisible()
  })

  test('activity feed links to dweller profiles', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const liveTab = page.locator('button', { hasText: /^live$/i })
    await liveTab.click()

    // Click on dweller name to navigate to profile (use first() since there are multiple actions)
    const dwellerLink = page.locator(`[data-testid="dweller-${setup.dwellerId}"]`).first()
    await expect(dwellerLink).toBeVisible()
    await dwellerLink.click()

    // Verify navigation to dweller profile
    await expect(page).toHaveURL(new RegExp(`/dweller/${setup.dwellerId}`))
  })
})

test.describe('Agent Visibility - Dweller Profile', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('dweller profile page shows basic info', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText('Edmund Whitestone').first()).toBeVisible()
    await expect(page.getByText(/memory broker/i).first()).toBeVisible()
  })

  test('dweller profile shows personality and background', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    await expect(page.getByText(/cautious but curious/i)).toBeVisible()
    await expect(page.getByText(/grew up in the shadow/i)).toBeVisible()
  })

  test('dweller profile links back to world', async ({ page }) => {
    await page.goto(`/dweller/${setup.dwellerId}`)

    // Find link containing the world name
    const worldLink = page.locator('a', { hasText: new RegExp(setup.worldName, 'i') })
    await expect(worldLink).toBeVisible()
    await worldLink.click()

    await expect(page).toHaveURL(new RegExp(`/world/${setup.worldId}`))
  })
})

test.describe('Agent Visibility - Aspects List', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)

    // Create an aspect
    const aspectRes = await request.post(`${API_BASE}/aspects/worlds/${setup.worldId}/aspects`, {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        aspect_type: 'region',
        title: 'The Undergrid',
        premise:
          'A vast underground network of tunnels and chambers beneath Neo Tokyo, serving as the primary hub for illegal memory trading operations.',
        content: {
          description:
            'The Undergrid is a labyrinthine network of tunnels beneath Neo Tokyo, originally built for earthquake protection but now repurposed as the central hub for memory trading.',
          key_features: [
            'Multi-level tunnel system spanning 50 square kilometers',
            'Bioluminescent lighting from engineered fungi',
            'Encrypted access points requiring memory-key authentication',
          ],
          population: 'Approximately 10,000 permanent residents, mostly traders and technicians',
        },
        canon_justification:
          'Tokyo has extensive underground infrastructure for disaster preparedness. As memory trading grew, these spaces naturally became attractive for their privacy and security. This follows historical patterns of black markets seeking unmonitored spaces.',
      },
    })
    if (!aspectRes.ok()) {
      const error = await aspectRes.text()
      throw new Error(`Failed to create aspect: ${error}`)
    }
    const aspectData = await aspectRes.json()
    const aspectId = aspectData.aspect.id

    // Submit aspect
    const submitRes = await request.post(`${API_BASE}/aspects/${aspectId}/submit`, {
      headers: { 'X-API-Key': setup.agentKey },
    })
    if (!submitRes.ok()) {
      const error = await submitRes.text()
      throw new Error(`Failed to submit aspect: ${error}`)
    }

    // Validate aspect
    const validateRes = await request.post(`${API_BASE}/aspects/${aspectId}/validate`, {
      headers: { 'X-API-Key': setup.validatorKey },
      data: {
        verdict: 'approve',
        critique:
          'The Undergrid is a compelling addition that fits the world premise perfectly. Well-grounded in urban development patterns.',
        canon_conflicts: [],
        suggested_fixes: [],
        updated_canon_summary:
          'A world where memories can be traded in underground markets. The Undergrid beneath Neo Tokyo serves as the primary hub for these operations.',
      },
    })
    if (!validateRes.ok()) {
      const error = await validateRes.text()
      throw new Error(`Failed to validate aspect: ${error}`)
    }
  })

  test('world page shows aspects tab', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const aspectsTab = page.locator('button', { hasText: /^aspects$/i })
    await expect(aspectsTab).toBeVisible()
    await aspectsTab.click()

    // Verify aspects content (use heading role to be specific since text appears in canon summary too)
    await expect(page.getByRole('heading', { name: 'The Undergrid' })).toBeVisible()
  })

  test('aspects list shows aspect details', async ({ page }) => {
    await page.goto(`/world/${setup.worldId}`)

    const aspectsTab = page.locator('button', { hasText: /^aspects$/i })
    await aspectsTab.click()

    // Check for aspect type and premise
    await expect(page.getByText(/underground network/i)).toBeVisible()
  })
})

test.describe('Agent Visibility - Agent Profile', () => {
  let setup: TestSetup

  test.beforeAll(async ({ request }) => {
    setup = await setupTestWorld(request)
  })

  test('agent profile page shows agent info', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    await expect(page.getByText(/e2e test creator/i)).toBeVisible()
    await expect(page.getByText(/@e2e-test-creator/i)).toBeVisible()
  })

  test('agent profile shows proposals', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    // Should show the world they created (proposal is now a world)
    await expect(page.getByText(new RegExp(setup.worldName, 'i'))).toBeVisible()
  })

  test('agent profile shows inhabited dwellers', async ({ page }) => {
    await page.goto(`/agent/${setup.agentId}`)

    // Should show the dweller they inhabit
    await expect(page.getByText('Edmund Whitestone')).toBeVisible()
  })
})

/**
 * Critical API Tests - Platform Health and Configuration
 */
test.describe('API - Platform Configuration', () => {
  test('platform health reports test_mode as enabled', async ({ request }) => {
    const healthRes = await request.get(`${API_BASE}/platform/health`)
    expect(healthRes.ok()).toBeTruthy()

    const health = await healthRes.json()
    expect(health.status).toBe('healthy')
    expect(health.configuration.test_mode_enabled).toBe(true)
  })

  test('platform stats include test_mode status', async ({ request }) => {
    const statsRes = await request.get(`${API_BASE}/platform/stats`)
    expect(statsRes.ok()).toBeTruthy()

    const stats = await statsRes.json()
    expect(stats.environment).toBeDefined()
    expect(stats.environment.test_mode_enabled).toBe(true)
  })
})

/**
 * Critical API Tests - Test Mode Self-Validation
 */
test.describe('API - Test Mode Self-Validation', () => {
  test('agent can test-approve proposal when DSF_TEST_MODE_ENABLED=true', async ({ request }) => {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 8)

    // Register agent
    const agentRes = await request.post(`${API_BASE}/auth/agent`, {
      data: {
        name: `Test-Approve Agent ${timestamp}`,
        username: `test-approve-${timestamp}-${random}`,
      },
    })
    expect(agentRes.ok()).toBeTruthy()
    const agentKey = (await agentRes.json()).api_key.key

    // Create proposal
    const proposalRes = await request.post(`${API_BASE}/proposals`, {
      headers: { 'X-API-Key': agentKey },
      data: {
        name: `Test-Approve World ${timestamp}`,
        premise:
          'A world where neural interfaces allow direct brain-to-brain communication, enabling shared consciousness experiences.',
        year_setting: 2080,
        causal_chain: SAMPLE_CAUSAL_CHAIN,
        scientific_basis:
          'Based on Neuralink progress and brain-computer interface research. Extends current neural interface capabilities.',
        image_prompt:
          'A vast neural network visualization with glowing synaptic connections across a dark cosmos.',
      },
    })
    expect(proposalRes.ok()).toBeTruthy()
    const proposalId = (await proposalRes.json()).id

    // Submit proposal
    const submitRes = await request.post(`${API_BASE}/proposals/${proposalId}/submit?force=true`, {
      headers: { 'X-API-Key': agentKey },
    })
    expect(submitRes.ok()).toBeTruthy()

    // Use test-approve endpoint - THIS MUST WORK when DSF_TEST_MODE_ENABLED=true
    const approveRes = await request.post(
      `${API_BASE}/proposals/${proposalId}/test-approve`,
      { headers: { 'X-API-Key': agentKey } }
    )
    const approveData = await approveRes.json()

    // If this fails, test_mode is broken - agents will be blocked!
    if (!approveRes.ok()) {
      throw new Error(
        `CRITICAL: test-approve failed! Test mode may not be enabled. Error: ${JSON.stringify(approveData)}`
      )
    }

    // Verify world was created (world ID comes from test-approve response)
    expect(approveData.world_created?.id).toBeTruthy()

    // Verify proposal status via API
    const proposalCheck = await request.get(`${API_BASE}/proposals/${proposalId}`)
    const proposalData = await proposalCheck.json()
    expect(proposalData.proposal.status).toBe('approved')
  })

  test('proposal review-cycle endpoint no longer exists (test-approve is the E2E path)', async ({ request }) => {
    const timestamp = Date.now()
    const random = Math.random().toString(36).substring(2, 8)

    // Register agent
    const agentRes = await request.post(`${API_BASE}/auth/agent`, {
      data: {
        name: `Validate Check Agent ${timestamp}`,
        username: `val-check-${timestamp}-${random}`,
      },
    })
    expect(agentRes.ok()).toBeTruthy()
    const agentKey = (await agentRes.json()).api_key.key

    // Create and submit proposal
    const proposalRes = await request.post(`${API_BASE}/proposals`, {
      headers: { 'X-API-Key': agentKey },
      data: {
        name: `Validate Check World ${timestamp}`,
        premise:
          'A world where quantum computing has made all classical encryption obsolete, requiring new security paradigms.',
        year_setting: 2070,
        causal_chain: SAMPLE_CAUSAL_CHAIN,
        scientific_basis:
          'Based on quantum computing research and cryptography fundamentals. Shor algorithm implications for post-quantum standards.',
        image_prompt:
          'A quantum computing data center with crystalline qubit arrays glowing in cold blue light.',
      },
    })
    expect(proposalRes.ok()).toBeTruthy()
    const proposalId = (await proposalRes.json()).id

    await request.post(`${API_BASE}/proposals/${proposalId}/submit?force=true`, {
      headers: { 'X-API-Key': agentKey },
    })

    // The old /validate endpoint no longer exists — should return 404 or 405
    const validateRes = await request.post(`${API_BASE}/proposals/${proposalId}/validate`, {
      headers: { 'X-API-Key': agentKey },
      data: { verdict: 'approve', critique: 'test', scientific_issues: [], suggested_fixes: [], research_conducted: 'test', weaknesses: [] },
    })
    // Endpoint is gone — expect 404 (or any non-2xx)
    expect(validateRes.ok()).toBe(false)
  })

  test('agent can self-validate aspect with test_mode=true', async ({ request }) => {
    // First create a world using the normal flow
    const setup = await setupTestWorld(request)

    const timestamp = Date.now()

    // Create an aspect
    const aspectRes = await request.post(`${API_BASE}/aspects/worlds/${setup.worldId}/aspects`, {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        aspect_type: 'technology',
        title: `Self-Validated Tech ${timestamp}`,
        premise:
          'Neural dust - microscopic implants that enable passive memory backup without surgery.',
        content: {
          description:
            'Nanoscale wireless sensors injected into bloodstream, migrate to brain and form mesh network for continuous memory backup.',
          capabilities: [
            'Passive memory recording',
            'Cloud backup every 24 hours',
            'No maintenance required',
          ],
        },
        canon_justification:
          'Based on DARPA neural dust research and blood-brain barrier crossing techniques in development.',
      },
    })
    expect(aspectRes.ok()).toBeTruthy()
    const aspectId = (await aspectRes.json()).aspect.id

    // Submit aspect
    await request.post(`${API_BASE}/aspects/${aspectId}/submit`, {
      headers: { 'X-API-Key': setup.agentKey },
    })

    // Self-validate aspect with test_mode=true
    const validateRes = await request.post(
      `${API_BASE}/aspects/${aspectId}/validate?test_mode=true`,
      {
        headers: { 'X-API-Key': setup.agentKey },
        data: {
          verdict: 'approve',
          critique: 'Self-validating for testing purposes. Technology fits world premise.',
          canon_conflicts: [],
          suggested_fixes: [],
          updated_canon_summary: 'World now includes neural dust technology for passive memory backup.',
        },
      }
    )

    if (!validateRes.ok()) {
      const error = await validateRes.text()
      throw new Error(
        `CRITICAL: test_mode=true aspect self-validation failed! Error: ${error}`
      )
    }

    // Verify aspect is approved
    const aspectCheck = await request.get(`${API_BASE}/aspects/${aspectId}`)
    const aspectData = await aspectCheck.json()
    expect(aspectData.aspect.status).toBe('approved')
  })
})
