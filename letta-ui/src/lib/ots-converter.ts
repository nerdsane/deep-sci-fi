/**
 * Convert Letta run data to OTS (Open Trajectory Specification) format.
 *
 * This mirrors the server-side OTSAdapter.from_letta_run() logic.
 */

export interface OTSTrajectory {
  trajectory_id: string;
  version: string;
  metadata: OTSMetadata;
  context: OTSContext;
  system_message?: OTSSystemMessage;
  turns: OTSTurn[];
  final_reward?: number;
}

export interface OTSMetadata {
  task_description: string;
  domain?: string;
  timestamp_start: string;
  timestamp_end?: string;
  duration_ms?: number;
  agent_id: string;
  framework: string;
  environment?: string;
  outcome: 'success' | 'partial_success' | 'failure';
  feedback_score?: number;
  human_reviewed: boolean;
  tags: string[];
}

export interface OTSContext {
  referrer?: string;
  user?: string;
  entities: OTSEntity[];
  resources: OTSResource[];
}

export interface OTSEntity {
  type: string;
  id: string;
  name?: string;
}

export interface OTSResource {
  type: string;
  uri: string;
}

export interface OTSSystemMessage {
  content: string;
  timestamp: string;
}

export interface OTSTurn {
  turn_id: number;
  span_id: string;
  timestamp: string;
  messages: OTSMessage[];
  decisions: OTSDecision[];
}

export interface OTSMessage {
  message_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  timestamp: string;
  content: OTSMessageContent;
  reasoning?: string;
}

export interface OTSMessageContent {
  type: 'text' | 'tool_call' | 'tool_response';
  text?: string;
  data?: Record<string, any>;
}

export interface OTSDecision {
  decision_id: string;
  decision_type: string;
  choice: {
    action: string;
    arguments?: Record<string, any>;
    rationale?: string;
    confidence?: number;
  };
  consequence: {
    success: boolean;
    result_summary?: string;
    error_type?: string;
  };
}

/**
 * Convert Letta run data to OTS format
 */
export function convertRunToOTS(
  runData: Record<string, any>,
  trajectoryId: string,
  agentId?: string
): OTSTrajectory {
  const runId = runData.run_id || trajectoryId;
  const metadata = runData.metadata || {};
  const turns = runData.turns || [];
  const outcome = runData.outcome || {};

  // Map outcome type
  const outcomeType = mapOutcomeType(outcome);

  // Extract task description from first user message
  const taskDescription = inferTaskDescription(turns);

  // Extract system message
  const systemMessage = extractSystemMessage(turns);

  // Extract context (entities, resources)
  const context = extractContext(turns);

  // Convert turns
  const otsTurns = convertTurns(turns);

  return {
    trajectory_id: runId,
    version: '0.1-draft',
    metadata: {
      task_description: taskDescription,
      timestamp_start: metadata.start_time || new Date().toISOString(),
      timestamp_end: metadata.end_time,
      duration_ms: metadata.duration_ns ? metadata.duration_ns / 1_000_000 : undefined,
      agent_id: agentId || metadata.agent_id || 'unknown',
      framework: 'letta',
      environment: metadata.models?.[0],
      outcome: outcomeType,
      feedback_score: outcome.confidence,
      human_reviewed: false,
      tags: [],
    },
    context,
    system_message: systemMessage,
    turns: otsTurns,
    final_reward: outcome.confidence,
  };
}

function mapOutcomeType(outcome: Record<string, any>): 'success' | 'partial_success' | 'failure' {
  const execution = outcome.execution || {};
  const status = execution.status || outcome.type || '';

  if (status === 'completed' || status === 'success') {
    return 'success';
  } else if (status === 'partial_success' || status === 'incomplete') {
    return 'partial_success';
  }
  return 'failure';
}

function inferTaskDescription(turns: any[]): string {
  for (const turn of turns) {
    for (const msg of turn.messages || []) {
      if (msg.role === 'user') {
        const content = msg.content || msg.text;
        const text = extractTextFromContent(content);
        if (text) {
          return text.slice(0, 500);
        }
      }
    }
  }
  return 'Unknown task';
}

function extractTextFromContent(content: any): string {
  if (typeof content === 'string') {
    return content;
  }
  if (Array.isArray(content)) {
    for (const item of content) {
      if (typeof item === 'string') return item;
      if (item?.type === 'text' && item?.text) return item.text;
      if (item?.text) return item.text;
    }
  }
  return '';
}

function extractSystemMessage(turns: any[]): OTSSystemMessage | undefined {
  if (!turns.length) return undefined;

  for (const msg of turns[0].messages || []) {
    if (msg.role === 'system') {
      const text = extractTextFromContent(msg.content || msg.text);
      if (text) {
        return {
          content: text,
          timestamp: msg.timestamp || new Date().toISOString(),
        };
      }
    }
  }
  return undefined;
}

function extractContext(turns: any[]): OTSContext {
  const entities: OTSEntity[] = [];
  const resources: OTSResource[] = [];
  const seenEntityIds = new Set<string>();
  const seenUris = new Set<string>();

  for (const turn of turns) {
    for (const msg of turn.messages || []) {
      const toolCalls = msg.tool_calls || [];
      for (const tc of toolCalls) {
        const func = tc.function || {};
        const name = func.name || '';
        const args = parseArguments(func.arguments);

        // Extract entities from DSF tool calls
        if (['world_manager', 'story_manager', 'asset_manager'].includes(name)) {
          for (const key of ['world_id', 'story_id', 'asset_id', 'id']) {
            if (args[key] && !seenEntityIds.has(args[key])) {
              entities.push({
                type: key.replace('_id', ''),
                id: args[key],
                name: args.name,
              });
              seenEntityIds.add(args[key]);
            }
          }
        }

        // Extract resources
        for (const key of ['file_path', 'path', 'url', 'uri']) {
          if (args[key] && !seenUris.has(args[key])) {
            resources.push({
              type: key === 'url' ? 'url' : 'file',
              uri: args[key],
            });
            seenUris.add(args[key]);
          }
        }
      }
    }
  }

  return { entities, resources };
}

function parseArguments(args: any): Record<string, any> {
  if (typeof args === 'object' && args !== null) return args;
  if (typeof args === 'string') {
    try {
      return JSON.parse(args);
    } catch {
      return { raw: args };
    }
  }
  return {};
}

function convertTurns(turns: any[]): OTSTurn[] {
  return turns.map((turn, idx) => {
    const messages = convertMessages(turn.messages || []);
    const decisions = extractDecisions(turn, idx);
    const timestamp = turn.messages?.[0]?.timestamp || new Date().toISOString();

    return {
      turn_id: idx,
      span_id: turn.step_id || `turn-${idx}`,
      timestamp,
      messages,
      decisions,
    };
  });
}

function convertMessages(messages: any[]): OTSMessage[] {
  return messages.map((msg, idx) => {
    const role = mapRole(msg.role);
    const content = convertContent(msg);
    const reasoning = extractReasoning(msg);

    return {
      message_id: msg.message_id || `msg-${idx}`,
      role,
      timestamp: msg.timestamp || new Date().toISOString(),
      content,
      reasoning,
    };
  });
}

function mapRole(role: string): 'user' | 'assistant' | 'system' | 'tool' {
  const roleMap: Record<string, 'user' | 'assistant' | 'system' | 'tool'> = {
    user: 'user',
    assistant: 'assistant',
    system: 'system',
    tool: 'tool',
  };
  return roleMap[role] || 'assistant';
}

function convertContent(msg: any): OTSMessageContent {
  const content = msg.content;
  const toolCalls = msg.tool_calls;

  if (toolCalls?.length) {
    return {
      type: 'tool_call',
      data: { tool_calls: toolCalls },
    };
  }

  if (msg.tool_call_id) {
    return {
      type: 'tool_response',
      text: extractTextFromContent(content),
      data: { tool_call_id: msg.tool_call_id },
    };
  }

  return {
    type: 'text',
    text: extractTextFromContent(content),
  };
}

function extractReasoning(msg: any): string | undefined {
  const content = msg.content;
  if (Array.isArray(content)) {
    for (const item of content) {
      if (item?.type === 'reasoning') {
        return item.text;
      }
    }
  }
  return undefined;
}

function extractDecisions(turn: any, turnIdx: number): OTSDecision[] {
  const decisions: OTSDecision[] = [];
  const messages = turn.messages || [];

  for (const msg of messages) {
    const toolCalls = msg.tool_calls || [];

    for (let i = 0; i < toolCalls.length; i++) {
      const tc = toolCalls[i];
      const func = tc.function || {};
      const toolName = func.name || 'unknown';
      const args = parseArguments(func.arguments);

      // Find tool result
      const { success, resultSummary } = findToolResult(messages, tc.id);

      decisions.push({
        decision_id: `t${turnIdx}-d${decisions.length}`,
        decision_type: 'tool_selection',
        choice: {
          action: toolName,
          arguments: args,
        },
        consequence: {
          success,
          result_summary: resultSummary,
          error_type: success ? undefined : 'tool_error',
        },
      });
    }
  }

  return decisions;
}

function findToolResult(messages: any[], toolCallId?: string): { success: boolean; resultSummary?: string } {
  if (!toolCallId) return { success: true };

  for (const msg of messages) {
    if (msg.tool_call_id === toolCallId || msg.role === 'tool') {
      const text = extractTextFromContent(msg.content);
      const isError = ['error', 'exception', 'failed', 'failure'].some(
        indicator => text.toLowerCase().includes(indicator)
      );
      return {
        success: !isError,
        resultSummary: text?.slice(0, 500),
      };
    }
  }

  return { success: true };
}
