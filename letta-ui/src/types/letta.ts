// Letta API types based on discovered endpoints

export interface Agent {
  id: string;
  name: string;
  description?: string;
  agent_type: string;
  model: string;
  embedding: string;
  system?: string;
  created_at: string;
  tags?: string[];
  managed_group?: {
    agent_ids: string[];
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  text?: string;
  content?: Array<{ type: string; text?: string }>;
  tool_calls?: Array<{
    id: string;
    type: string;
    function: {
      name: string;
      arguments: string;
    };
  }>;
  created_at: string;
}

export interface Run {
  id: string;
  agent_id: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  stop_reason?: string;
  created_at: string;
  completed_at?: string;
  metadata_?: Record<string, any>;
}

export interface Step {
  id: string;
  run_id: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  stop_reason?: string;
  created_at: string;
}

export interface Block {
  id: string;
  label: string;
  value: string;
  description?: string;
  limit?: number;
  is_template?: boolean;
  template_name?: string;
}

export interface Tool {
  id: string;
  name: string;
  description?: string;
  source_code?: string;
  tags?: string[];
}

export type TrajectoryVisibility = 'full' | 'anonymized';

export interface Trajectory {
  id: string;
  agent_id: string;
  domain_type?: string;
  share_cross_org?: boolean;
  data: {
    run_id?: string;
    metadata?: {
      start_time?: string;
      end_time?: string;
      duration_ns?: number;
      status?: string;
      step_count?: number;
      message_count?: number;
      input_tokens?: number;
      output_tokens?: number;
      total_tokens?: number;
      models?: string[];
      tools_used?: string[];
    };
    turns?: Array<{
      step_id?: string;
      model?: string;
      input_tokens?: number;
      output_tokens?: number;
      messages?: Message[] | string;  // string for anonymized "[REDACTED]"
      message_count?: number;  // For anonymized trajectories
      tool_calls_count?: number;  // For anonymized trajectories
    }>;
    outcome?: {
      // New format (preferred)
      execution?: {
        status: 'completed' | 'failed' | 'incomplete' | 'error' | 'unknown';
        confidence: number;
        reasoning: string[];
      };
      // Old format (deprecated, kept for backward compatibility)
      type?: 'success' | 'failure' | 'partial_success' | 'unknown';
      confidence?: number;
      reasoning?: string[];
    };
  };
  searchable_summary?: string;
  outcome_score?: number;
  score_reasoning?: string;
  tags?: string[];
  task_category?: string;
  complexity_level?: string;
  metadata?: Record<string, any>;
  processing_status?: string;
  processing_started_at?: string;
  processing_completed_at?: string;
  processing_error?: string;
  embedding?: number[];
  created_at: string;
  updated_at?: string;
  organization_id?: string;
  // For search results
  visibility?: TrajectoryVisibility;
}

export interface SearchTrajectoriesResponse {
  trajectories: Trajectory[];
  total: number;
}

export interface ListResponse<T> {
  items: T[];
  total?: number;
  page?: number;
  page_size?: number;
}
