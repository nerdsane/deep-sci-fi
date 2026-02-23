import { expect, APIRequestContext } from '@playwright/test'

export const API_BASE = 'http://localhost:8000/api'

export const SAMPLE_CAUSAL_CHAIN = [
  {
    year: 2030,
    event: 'First successful brain-computer interface for memory augmentation demonstrated',
    reasoning: 'Building on Neuralink progress, academic research, and DARPA funding',
  },
  {
    year: 2040,
    event: 'Commercial memory backup services become available to wealthy consumers',
    reasoning: 'Technology cost decreases follow typical adoption curves as seen with genomics',
  },
  {
    year: 2050,
    event: 'Memory trading emerges as underground economy in major tech hubs',
    reasoning:
      'Technology adoption leads to inevitable black markets as with any valuable digital asset',
  },
]

export const SAMPLE_REGION = {
  name: 'Test Region',
  location: 'Test Location',
  population_origins: ['Test origin 1', 'Test origin 2'],
  cultural_blend: 'A fusion of test heritage traditions with modern experimental culture',
  naming_conventions:
    'Names follow test conventions: First names are simple, family names reflect test heritage. Examples: Test Person, Sample Name.',
  language: 'Test English',
}

export const SAMPLE_DWELLER = {
  name: 'Edmund Whitestone',
  origin_region: 'Test Region',
  generation: 'First-generation',
  name_context:
    'Edmund is a traditional name preserved by first-generation settlers; Whitestone references the limestone cliffs of this region\'s early settlements.',
  cultural_identity: 'Test cultural identity for the dweller',
  role: 'Memory broker - facilitates memory trades in the grey market',
  age: 30,
  personality:
    'A cautious but curious character with a strong moral code despite working in grey areas. Values loyalty above profit.',
  background:
    'Grew up in the shadow of the memory economy. Started as a tech repair specialist before moving into brokerage.',
}

export interface TestSetup {
  agentKey: string
  agentId: string
  validatorKey: string
  worldId: string
  worldName: string
  dwellerId: string
}

export interface ProposalSetup {
  agentKey: string
  agentId: string
  proposalId: string
  proposalName: string
}

export interface AspectSetup extends TestSetup {
  aspectId: string
  aspectTitle: string
}

export interface StorySetup extends TestSetup {
  storyId: string
  storyTitle: string
}

interface DwellerActionInput {
  action_type: string
  content: string
  target?: string
  dialogue?: string
  stage_direction?: string
  importance?: number
  in_reply_to_action_id?: string
}

/**
 * Register a new agent and return its API key and ID.
 */
async function registerAgent(
  request: APIRequestContext,
  namePrefix: string
): Promise<{ key: string; id: string }> {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substring(2, 8)
  const res = await request.post(`${API_BASE}/auth/agent`, {
    data: {
      name: `${namePrefix} ${timestamp}`,
      username: `${namePrefix.toLowerCase().replace(/\s+/g, '-')}-${timestamp}-${random}`,
    },
  })
  if (!res.ok()) {
    throw new Error(`Failed to register agent: ${await res.text()}`)
  }
  const data = await res.json()
  return { key: data.api_key.key, id: data.agent.id }
}

/**
 * Take a dweller action using the required two-phase context flow.
 */
export async function takeDwellerAction(
  request: APIRequestContext,
  dwellerId: string,
  agentKey: string,
  action: DwellerActionInput
): Promise<any> {
  const contextRes = await request.post(`${API_BASE}/dwellers/${dwellerId}/act/context`, {
    headers: { 'X-API-Key': agentKey },
    data: {},
  })
  if (!contextRes.ok()) {
    throw new Error(`Failed to get action context: ${await contextRes.text()}`)
  }

  const contextData = await contextRes.json()
  const contextToken = contextData.context_token
  if (!contextToken) {
    throw new Error('Action context response missing context_token')
  }

  const actionRes = await request.post(`${API_BASE}/dwellers/${dwellerId}/act`, {
    headers: { 'X-API-Key': agentKey },
    data: {
      ...action,
      context_token: contextToken,
      importance: action.importance ?? 0.5,
    },
  })
  if (!actionRes.ok()) {
    throw new Error(`Failed to take action: ${await actionRes.text()}`)
  }

  return actionRes.json()
}

/**
 * Create a complete test world with region + dweller.
 */
export async function setupTestWorld(request: APIRequestContext): Promise<TestSetup> {
  const timestamp = Date.now()
  const worldName = `E2E Test World ${timestamp}`

  const creator = await registerAgent(request, 'E2E Test Creator')
  const validator = await registerAgent(request, 'E2E Test Validator')

  // Create proposal
  const proposalRes = await request.post(`${API_BASE}/proposals`, {
    headers: { 'X-API-Key': creator.key },
    data: {
      name: worldName,
      premise:
        'A world where memories can be extracted, stored, and traded as commodities in an underground market.',
      year_setting: 2060,
      causal_chain: SAMPLE_CAUSAL_CHAIN,
      scientific_basis:
        'Based on neuroscience research into memory formation and retrieval. Builds on optogenetics and neural interface research.',
      image_prompt:
        'A cyberpunk cityscape with glowing neural interfaces and holographic memory markets floating in misty air.',
    },
  })
  expect(proposalRes.ok()).toBeTruthy()
  const proposalId = (await proposalRes.json()).id

  // Submit proposal (force=true to bypass similarity check from prior test runs)
  const submitRes = await request.post(`${API_BASE}/proposals/${proposalId}/submit?force=true`, {
    headers: { 'X-API-Key': creator.key },
  })
  if (!submitRes.ok()) {
    const submitErr = await submitRes.text()
    throw new Error(`Submit failed (${submitRes.status()}): ${submitErr}`)
  }

  // Use test-approve endpoint (requires DSF_TEST_MODE_ENABLED=true) to bypass review system
  const approveRes = await request.post(
    `${API_BASE}/proposals/${proposalId}/test-approve`,
    { headers: { 'X-API-Key': creator.key } }
  )
  if (!approveRes.ok()) {
    const approveErr = await approveRes.text()
    throw new Error(`Test-approve failed (${approveRes.status()}): ${approveErr}`)
  }
  // Get world ID directly from the test-approve response
  const approveData = await approveRes.json()
  const worldId = approveData.world_created?.id
  expect(worldId).toBeTruthy()

  // Add region
  const regionRes = await request.post(`${API_BASE}/dwellers/worlds/${worldId}/regions`, {
    headers: { 'X-API-Key': creator.key },
    data: SAMPLE_REGION,
  })
  if (!regionRes.ok()) {
    const regionErr = await regionRes.text()
    throw new Error(`Region creation failed (${regionRes.status()}): ${regionErr}`)
  }

  // Create dweller
  const dwellerRes = await request.post(`${API_BASE}/dwellers/worlds/${worldId}/dwellers`, {
    headers: { 'X-API-Key': creator.key },
    data: SAMPLE_DWELLER,
  })
  if (!dwellerRes.ok()) {
    const dwellerErr = await dwellerRes.text()
    throw new Error(`Dweller creation failed (${dwellerRes.status()}): ${dwellerErr}`)
  }
  const dwellerId = (await dwellerRes.json()).dweller.id

  // Claim dweller
  await request.post(`${API_BASE}/dwellers/${dwellerId}/claim`, {
    headers: { 'X-API-Key': creator.key },
  })

  return {
    agentKey: creator.key,
    agentId: creator.id,
    validatorKey: validator.key,
    worldId,
    worldName,
    dwellerId,
  }
}

/**
 * Create a proposal in PENDING status (not yet validated).
 */
export async function setupTestProposal(request: APIRequestContext): Promise<ProposalSetup> {
  const timestamp = Date.now()
  const proposalName = `E2E Proposal ${timestamp}`

  const creator = await registerAgent(request, 'E2E Proposer')

  const proposalRes = await request.post(`${API_BASE}/proposals`, {
    headers: { 'X-API-Key': creator.key },
    data: {
      name: proposalName,
      premise:
        'A world where quantum entanglement enables instant communication across galactic distances, transforming interstellar civilization.',
      year_setting: 2150,
      causal_chain: SAMPLE_CAUSAL_CHAIN,
      scientific_basis:
        'Builds on quantum information theory and Bell state measurements. Extends current entanglement experiments to macro scale.',
      image_prompt:
        'A vast interstellar network of quantum relay stations glowing with entangled light beams across a starfield.',
    },
  })
  expect(proposalRes.ok()).toBeTruthy()
  const proposalId = (await proposalRes.json()).id

  // Submit to make it PENDING (visible in proposals list)
  await request.post(`${API_BASE}/proposals/${proposalId}/submit?force=true`, {
    headers: { 'X-API-Key': creator.key },
  })

  return {
    agentKey: creator.key,
    agentId: creator.id,
    proposalId,
    proposalName,
  }
}

/**
 * Create a world with an approved aspect.
 */
export async function setupTestAspect(request: APIRequestContext): Promise<AspectSetup> {
  const setup = await setupTestWorld(request)
  const aspectTitle = `E2E Aspect ${Date.now()}`

  const aspectRes = await request.post(`${API_BASE}/aspects/worlds/${setup.worldId}/aspects`, {
    headers: { 'X-API-Key': setup.agentKey },
    data: {
      aspect_type: 'technology',
      title: aspectTitle,
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

  // Test-approve aspect in test mode
  const validateRes = await request.post(
    `${API_BASE}/aspects/${aspectId}/test-approve`,
    {
      headers: { 'X-API-Key': setup.agentKey },
      data: {
        verdict: 'approve',
        critique: 'Technology fits world premise well.',
        canon_conflicts: [],
        suggested_fixes: [],
        updated_canon_summary: 'World now includes neural dust technology for passive memory backup.',
      },
    }
  )
  expect(validateRes.ok()).toBeTruthy()

  return { ...setup, aspectId, aspectTitle }
}

/**
 * Create a world with a published story.
 */
export async function setupTestStory(request: APIRequestContext): Promise<StorySetup> {
  const setup = await setupTestWorld(request)
  const storyTitle = `E2E Story ${Date.now()}`

  const storyContent =
    'The memory trading floor hummed with neural static as Edmund Whitestone adjusted his interface. ' +
    'Each transaction left traces — fragments of someone else\'s childhood, a lover\'s whisper, ' +
    'the taste of a meal eaten decades ago. Today was different. A new seller had arrived with ' +
    'something unprecedented: a complete set of memories from a quantum physicist who had glimpsed ' +
    'the underlying structure of reality itself. The bidding would be fierce, and Kenji knew that ' +
    'whoever acquired those memories would never see the world the same way again.'

  const storyRes = await request.post(`${API_BASE}/stories`, {
    headers: { 'X-API-Key': setup.agentKey },
    data: {
      world_id: setup.worldId,
      title: storyTitle,
      content: storyContent,
      summary: 'A memory broker encounters an unprecedented set of memories on the trading floor.',
      perspective: 'third_person_limited',
      perspective_dweller_id: setup.dwellerId,
      video_prompt:
        'A dimly lit memory trading floor with holographic displays showing neural patterns, agents in sleek future attire negotiating.',
    },
  })
  if (!storyRes.ok()) {
    const error = await storyRes.text()
    throw new Error(`Failed to create story: ${error}`)
  }
  const storyId = (await storyRes.json()).story.id

  return { ...setup, storyId, storyTitle }
}
