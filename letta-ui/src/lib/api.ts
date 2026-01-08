// API client for Letta server
// All requests go through the /api proxy in server.ts

const BASE_URL = '/api';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }

  return response.json();
}

export const api = {
  // Agents
  listAgents: () => fetchApi<any>('/v1/agents'),
  getAgent: (agentId: string) => fetchApi<any>(`/v1/agents/${agentId}`),
  updateAgent: (agentId: string, data: any) =>
    fetchApi<any>(`/v1/agents/${agentId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteAgent: (agentId: string) =>
    fetchApi<void>(`/v1/agents/${agentId}`, { method: 'DELETE' }),

  // Memory
  getCoreMemory: (agentId: string) =>
    fetchApi<any>(`/v1/agents/${agentId}/memory`),

  // Messages
  getAgentMessages: (agentId: string, limit = 20) =>
    fetchApi<any>(`/v1/agents/${agentId}/messages?limit=${limit}`),
  listMessages: (params?: { agent_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.agent_id) searchParams.set('agent_id', params.agent_id);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return fetchApi<any>(`/v1/messages${query ? `?${query}` : ''}`);
  },
  searchMessages: (query: string) =>
    fetchApi<any>(`/v1/messages/search?query=${encodeURIComponent(query)}`),

  // Runs
  listRuns: () => fetchApi<any>('/v1/runs'),
  getRunSteps: (runId: string) => fetchApi<any>(`/v1/runs/${runId}/steps`),
  getRunUsage: (runId: string) => fetchApi<any>(`/v1/runs/${runId}/usage`),
  getRunMetrics: (runId: string) => fetchApi<any>(`/v1/runs/${runId}/metrics`),

  // Steps
  listSteps: (params?: { run_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.run_id) searchParams.set('run_id', params.run_id);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return fetchApi<any>(`/v1/steps${query ? `?${query}` : ''}`);
  },
  getStep: (stepId: string) => fetchApi<any>(`/v1/steps/${stepId}`),
  getStepMetrics: (stepId: string) =>
    fetchApi<any>(`/v1/steps/${stepId}/metrics`),

  // Tools
  listTools: () => fetchApi<any>('/v1/tools'),

  // Jobs
  listJobs: () => fetchApi<any>('/v1/jobs'),
  getActiveJobs: () => fetchApi<any>('/v1/jobs/active'),

  // Models & Providers
  listModels: () => fetchApi<any>('/v1/models'),
  listProviders: () => fetchApi<any>('/v1/providers'),
  listEmbeddingModels: () => fetchApi<any>('/v1/models/embedding'),

  // Sources & Archives
  listSources: () => fetchApi<any>('/v1/sources'),
  listArchives: () => fetchApi<any>('/v1/archives'),

  // Blocks
  listBlocks: () => fetchApi<any>('/v1/blocks'),

  // Folders
  listFolders: () => fetchApi<any>('/v1/folders'),

  // Identities
  listIdentities: () => fetchApi<any>('/v1/identities'),

  // MCP Servers
  listMCPServers: () => fetchApi<any>('/v1/mcp/servers'),

  // Sandbox Configs
  listSandboxConfigs: () => fetchApi<any>('/v1/sandbox/configs'),

  // Trajectories
  listTrajectories: (params?: { limit?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    const query = searchParams.toString();
    return fetchApi<any>(`/v1/trajectories${query ? `?${query}` : ''}`);
  },
  getTrajectory: (trajectoryId: string) =>
    fetchApi<any>(`/v1/trajectories/${trajectoryId}`),
  getTrajectoriesWithEmbeddings: () =>
    fetchApi<any>('/v1/trajectories?include_embeddings=true'),
  searchTrajectories: (query: string) =>
    fetchApi<any>(
      `/v1/trajectories/search?query=${encodeURIComponent(query)}`
    ),

  // Analytics
  getAnalyticsAggregations: (params?: {
    start_date?: string;
    end_date?: string;
    agent_id?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.start_date) searchParams.set('start_date', params.start_date);
    if (params?.end_date) searchParams.set('end_date', params.end_date);
    if (params?.agent_id) searchParams.set('agent_id', params.agent_id);
    const query = searchParams.toString();
    return fetchApi<any>(`/v1/analytics/aggregations${query ? `?${query}` : ''}`);
  },
};
