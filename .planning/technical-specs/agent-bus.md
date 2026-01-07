# Agent Bus: Technical Specification

## Overview

The Agent Bus is a real-time message broker that enables bidirectional communication between the CLI, Canvas, and Agent. It serves as the central nervous system for the DSF unified experience.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Agent Bus                           │
│                                                           │
│  ┌─────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   WebSocket │◄──►│   Message    │◄──►│  Event     │ │
│  │   Server    │    │   Router     │    │  Store     │ │
│  └──────┬──────┘    └──────┬───────┘    └─────┬──────┘ │
│         │                  │                   │        │
│         │                  │                   │        │
└─────────┼──────────────────┼───────────────────┼────────┘
          │                  │                   │
          ▼                  ▼                   ▼
    ┌──────────┐      ┌──────────┐       ┌──────────┐
    │   CLI    │      │  Canvas  │       │  Letta   │
    │  Client  │      │  Client  │       │  Server  │
    └──────────┘      └──────────┘       └──────────┘
```

## Event Types

### Agent Events
Events originating from the agent:

```typescript
// Agent sends a message
{
  type: "agent.message",
  id: string,
  timestamp: number,
  payload: {
    content: string,
    role: "assistant",
    metadata?: Record<string, any>
  }
}

// Agent executes a tool
{
  type: "agent.tool_call",
  id: string,
  timestamp: number,
  payload: {
    tool: string,
    arguments: Record<string, any>,
    result?: any,
    status: "pending" | "success" | "error"
  }
}

// Agent updates canvas
{
  type: "agent.canvas_update",
  id: string,
  timestamp: number,
  payload: {
    operation: "render" | "update" | "remove" | "layout",
    component_id: string,
    definition?: ComponentDefinition,
    layout?: LayoutConfig
  }
}

// Agent generates asset
{
  type: "agent.asset_created",
  id: string,
  timestamp: number,
  payload: {
    asset_id: string,
    type: "image" | "audio" | "video" | "document",
    path: string,
    metadata: Record<string, any>
  }
}
```

### Canvas Events
Events originating from the canvas UI:

```typescript
// User interacts with component
{
  type: "canvas.interaction",
  id: string,
  timestamp: number,
  payload: {
    component_id: string,
    interaction_type: "click" | "input" | "select" | "drag",
    data: any,
    target?: string // e.g., "agent.navigate_to_segment"
  }
}

// Canvas state changes
{
  type: "canvas.state_change",
  id: string,
  timestamp: number,
  payload: {
    component_id: string,
    previous_state: any,
    new_state: any
  }
}

// Canvas layout changes
{
  type: "canvas.layout_change",
  id: string,
  timestamp: number,
  payload: {
    layout_id: string,
    config: LayoutConfig
  }
}

// Canvas ready/connected
{
  type: "canvas.ready",
  id: string,
  timestamp: number,
  payload: {
    client_id: string,
    agent_id: string,
    capabilities: string[]
  }
}
```

### CLI Events
Events originating from the CLI:

```typescript
// User sends message
{
  type: "cli.message",
  id: string,
  timestamp: number,
  payload: {
    content: string,
    role: "user",
    metadata?: Record<string, any>
  }
}

// User executes command
{
  type: "cli.command",
  id: string,
  timestamp: number,
  payload: {
    command: string, // e.g., "/canvas", "/pin"
    args?: string[]
  }
}

// CLI approval/rejection
{
  type: "cli.approval",
  id: string,
  timestamp: number,
  payload: {
    approval_id: string,
    decision: "approve" | "reject" | "modify",
    modifications?: any
  }
}
```

### System Events
System-level events:

```typescript
// File system changes
{
  type: "system.file_change",
  id: string,
  timestamp: number,
  payload: {
    path: string,
    change_type: "created" | "modified" | "deleted",
    file_type: "world" | "story" | "asset"
  }
}

// Agent status
{
  type: "system.agent_status",
  id: string,
  timestamp: number,
  payload: {
    agent_id: string,
    status: "idle" | "thinking" | "executing" | "waiting_approval"
  }
}
```

## WebSocket Protocol

### Connection

**Endpoint:** `ws://localhost:3030/agent-bus`

**Authentication:**
```typescript
// On connection, client must authenticate
{
  type: "auth",
  payload: {
    agent_id: string,
    client_type: "cli" | "canvas" | "letta",
    client_id: string // unique client identifier
  }
}

// Server responds
{
  type: "auth_response",
  success: boolean,
  payload: {
    session_id: string,
    subscriptions: string[] // event types this client is subscribed to
  }
}
```

### Subscription Management

```typescript
// Subscribe to event types
{
  type: "subscribe",
  payload: {
    event_types: string[] // e.g., ["agent.*", "canvas.interaction"]
  }
}

// Unsubscribe
{
  type: "unsubscribe",
  payload: {
    event_types: string[]
  }
}
```

### Publishing Events

```typescript
// Publish event
{
  type: "publish",
  payload: {
    event: Event // one of the event types defined above
  }
}

// Server confirms
{
  type: "publish_ack",
  payload: {
    event_id: string,
    status: "delivered" | "queued" | "error",
    error?: string
  }
}
```

### Event Routing

Events are routed based on patterns:

- `agent.*` - All agent events
- `canvas.interaction` - Specific canvas interactions
- `*.message` - All messages (agent and CLI)
- `system.file_change[type=world]` - File changes filtered by type

Clients specify subscriptions on connect or via subscribe message.

## Message Router

The Message Router handles event routing logic:

```typescript
class MessageRouter {
  private subscriptions: Map<string, Set<ClientConnection>>;
  private eventStore: EventStore;

  // Subscribe client to event pattern
  subscribe(clientId: string, pattern: string): void;

  // Unsubscribe client
  unsubscribe(clientId: string, pattern: string): void;

  // Publish event to all matching subscribers
  publish(event: Event): void;

  // Query past events
  query(filter: EventFilter): Event[];

  // Wait for specific event (with timeout)
  waitFor(pattern: string, timeout: number): Promise<Event>;
}
```

### Pattern Matching

Support glob-style patterns:
- `*` - Match any single segment
- `**` - Match any number of segments
- `[type=value]` - Match events with specific payload properties

Examples:
- `agent.*` - All agent events
- `*.message` - All message events
- `agent.tool_call[tool=canvas_ui]` - Only canvas_ui tool calls
- `canvas.interaction[component_id=story-*]` - Interactions with story components

## Event Store

The Event Store persists events for replay and querying:

```typescript
interface EventStore {
  // Append event to store
  append(event: Event): void;

  // Query events
  query(filter: EventFilter): Event[];

  // Get events since timestamp
  since(timestamp: number): Event[];

  // Get events for specific session
  session(sessionId: string): Event[];

  // Prune old events (retention policy)
  prune(olderThan: number): void;
}

interface EventFilter {
  types?: string[]; // Event types to match
  since?: number; // Timestamp
  until?: number; // Timestamp
  agent_id?: string;
  client_id?: string;
  limit?: number;
  offset?: number;
}
```

**Storage:** In-memory with periodic flush to disk (`.dsf/events/*.jsonl`)

**Retention:** Keep last 10,000 events or 24 hours, whichever is larger

## Implementation

### File Structure

```
letta-code/src/bus/
├── server.ts          # WebSocket server
├── router.ts          # Message routing logic
├── store.ts           # Event storage
├── types.ts           # Event type definitions
├── patterns.ts        # Pattern matching
└── client.ts          # Client library
```

### Dependencies

```json
{
  "ws": "^8.x",           // WebSocket server
  "minimatch": "^9.x",    // Pattern matching
  "uuid": "^9.x"          // Event IDs
}
```

### Integration Points

#### 1. Canvas Server
```typescript
// Extend existing canvas server
import { AgentBus } from "./bus/server";

const bus = new AgentBus({ port: 3031 }); // Separate port from canvas HTTP
bus.start();

// Bridge file watcher to event bus
watcher.on("change", (path, changeType) => {
  bus.publish({
    type: "system.file_change",
    payload: { path, change_type: changeType, ... }
  });
});
```

#### 2. CLI Integration
```typescript
// Connect CLI to agent bus
import { AgentBusClient } from "./bus/client";

const busClient = new AgentBusClient("ws://localhost:3031/agent-bus");
await busClient.connect({
  agent_id: agentId,
  client_type: "cli",
  client_id: generateClientId()
});

// Subscribe to relevant events
busClient.subscribe([
  "agent.canvas_update",
  "agent.asset_created",
  "canvas.interaction"
]);

// Handle events
busClient.on("agent.canvas_update", (event) => {
  // Notify user in CLI: "Canvas updated with new layout"
});

// Publish CLI messages
busClient.publish({
  type: "cli.message",
  payload: { content: userInput, role: "user" }
});
```

#### 3. Letta Server Integration
```typescript
// Hook into Letta's message processing
// After agent generates response
busClient.publish({
  type: "agent.message",
  payload: { content: response, role: "assistant" }
});

// After tool execution
busClient.publish({
  type: "agent.tool_call",
  payload: {
    tool: toolName,
    arguments: toolArgs,
    result: toolResult,
    status: "success"
  }
});
```

## Security

### Authentication
- Verify agent_id matches active session
- Generate secure client_id tokens
- Rate limit connections per agent_id

### Authorization
- CLI clients can publish any event type
- Canvas clients limited to `canvas.*` events
- Letta server limited to `agent.*` and `system.*` events

### Validation
- Validate all events against schema before routing
- Sanitize payload data
- Reject oversized events (>1MB)

## Performance

### Optimization Strategies
1. **Connection Pooling** - Reuse WebSocket connections
2. **Event Batching** - Group rapid events into batches
3. **Selective Routing** - Only send events to interested clients
4. **Event Store Pruning** - Auto-delete old events
5. **Binary Protocol** - Use MessagePack for large payloads

### Benchmarks (Target)
- **Latency:** <10ms event delivery (same machine)
- **Throughput:** 1000+ events/sec
- **Concurrent Clients:** 100+ without degradation
- **Memory:** <100MB for 10,000 events in store

## Testing Strategy

### Unit Tests
- Pattern matching logic
- Event serialization/deserialization
- Subscription management
- Event filtering

### Integration Tests
- CLI ↔ Bus ↔ Canvas communication
- Event persistence and replay
- Connection handling (disconnect, reconnect)
- Multi-client scenarios

### E2E Tests
- User sends message in CLI → Canvas shows update
- User clicks canvas button → Agent receives event
- Agent generates image → Both CLI and Canvas notified

## Migration Path

### Phase 1: Standalone
- Implement Agent Bus as separate service
- Run alongside existing file watcher
- CLI and Canvas connect optionally

### Phase 2: Integration
- Replace file watcher with event-based updates
- Update tools to publish events
- Migrate canvas to event-driven architecture

### Phase 3: Optimization
- Add event batching
- Implement binary protocol
- Optimize storage and routing

## Future Enhancements

1. **Event Replay** - Replay past sessions for debugging
2. **Event Filtering** - Server-side filtering to reduce bandwidth
3. **Event Compression** - Compress large payloads
4. **Multi-Agent** - Support multiple agents on same bus
5. **Remote Bus** - Network-accessible bus for distributed setups
6. **Event Analytics** - Track usage patterns, performance metrics
