# Dynamic Canvas Implementation Guide

## Phase 1: Foundation (2 weeks)

This guide walks through implementing the foundational pieces for dynamic canvas control.

**Goal:** Enable basic agent-to-canvas communication with 5 core UI primitives.

**Success Criteria:**
- Agent can create simple card layouts via `canvas_ui` tool
- Canvas displays agent-created UI components in real-time
- Both CLI and Canvas show updates simultaneously

## Week 1: Agent Bus & State Management

### Day 1-2: Agent Bus Core

#### Step 1: Create Bus Infrastructure

```bash
cd letta-code/src
mkdir -p bus
cd bus
```

**Files to create:**

`bus/types.ts` - Event type definitions:
```typescript
export interface Event {
  type: string;
  id: string;
  timestamp: number;
  payload: any;
}

export interface AgentMessage extends Event {
  type: "agent.message";
  payload: {
    content: string;
    role: "assistant";
    metadata?: Record<string, any>;
  };
}

export interface CanvasUpdate extends Event {
  type: "agent.canvas_update";
  payload: {
    operation: "render" | "update" | "remove" | "layout";
    component_id: string;
    definition?: any;
    layout?: any;
  };
}

export interface CanvasInteraction extends Event {
  type: "canvas.interaction";
  payload: {
    component_id: string;
    interaction_type: string;
    data: any;
    target?: string;
  };
}

export type DSFEvent = AgentMessage | CanvasUpdate | CanvasInteraction;
```

`bus/server.ts` - WebSocket server:
```typescript
import { WebSocketServer, WebSocket } from "ws";
import type { DSFEvent } from "./types";
import { randomUUID } from "crypto";

interface Client {
  id: string;
  ws: WebSocket;
  agentId: string;
  clientType: "cli" | "canvas" | "letta";
  subscriptions: Set<string>;
}

export class AgentBus {
  private wss: WebSocketServer;
  private clients: Map<string, Client> = new Map();
  private eventHistory: DSFEvent[] = [];

  constructor(port: number = 3031) {
    this.wss = new WebSocketServer({ port });
    this.wss.on("connection", this.handleConnection.bind(this));
    console.log(`Agent Bus listening on ws://localhost:${port}`);
  }

  private handleConnection(ws: WebSocket) {
    ws.on("message", (data) => {
      try {
        const msg = JSON.parse(data.toString());
        this.handleMessage(ws, msg);
      } catch (err) {
        console.error("Failed to parse message:", err);
      }
    });

    ws.on("close", () => {
      // Remove client
      for (const [id, client] of this.clients.entries()) {
        if (client.ws === ws) {
          this.clients.delete(id);
          console.log(`Client ${id} disconnected`);
          break;
        }
      }
    });
  }

  private handleMessage(ws: WebSocket, msg: any) {
    switch (msg.type) {
      case "auth":
        this.handleAuth(ws, msg);
        break;
      case "subscribe":
        this.handleSubscribe(ws, msg);
        break;
      case "publish":
        this.handlePublish(ws, msg);
        break;
      default:
        ws.send(JSON.stringify({ error: "Unknown message type" }));
    }
  }

  private handleAuth(ws: WebSocket, msg: any) {
    const clientId = randomUUID();
    const client: Client = {
      id: clientId,
      ws,
      agentId: msg.payload.agent_id,
      clientType: msg.payload.client_type,
      subscriptions: new Set(["*"]) // Default: subscribe to all
    };

    this.clients.set(clientId, client);

    ws.send(JSON.stringify({
      type: "auth_response",
      success: true,
      payload: {
        session_id: clientId,
        subscriptions: Array.from(client.subscriptions)
      }
    }));

    console.log(`Client authenticated: ${clientId} (${client.clientType})`);
  }

  private handleSubscribe(ws: WebSocket, msg: any) {
    const client = this.findClient(ws);
    if (!client) return;

    msg.payload.event_types.forEach((type: string) => {
      client.subscriptions.add(type);
    });

    ws.send(JSON.stringify({
      type: "subscribe_ack",
      success: true
    }));
  }

  private handlePublish(ws: WebSocket, msg: any) {
    const event: DSFEvent = {
      ...msg.payload.event,
      id: randomUUID(),
      timestamp: Date.now()
    };

    // Store in history
    this.eventHistory.push(event);
    if (this.eventHistory.length > 1000) {
      this.eventHistory.shift(); // Keep last 1000
    }

    // Route to subscribers
    this.routeEvent(event);

    // Confirm to publisher
    ws.send(JSON.stringify({
      type: "publish_ack",
      payload: {
        event_id: event.id,
        status: "delivered"
      }
    }));
  }

  private routeEvent(event: DSFEvent) {
    for (const client of this.clients.values()) {
      if (this.shouldReceiveEvent(client, event)) {
        try {
          client.ws.send(JSON.stringify({
            type: "event",
            payload: event
          }));
        } catch (err) {
          console.error(`Failed to send to ${client.id}:`, err);
        }
      }
    }
  }

  private shouldReceiveEvent(client: Client, event: DSFEvent): boolean {
    // Check if client subscribes to this event type
    for (const pattern of client.subscriptions) {
      if (pattern === "*") return true;
      if (this.matchPattern(pattern, event.type)) return true;
    }
    return false;
  }

  private matchPattern(pattern: string, eventType: string): boolean {
    // Simple wildcard matching
    if (pattern.endsWith(".*")) {
      const prefix = pattern.slice(0, -2);
      return eventType.startsWith(prefix);
    }
    return pattern === eventType;
  }

  private findClient(ws: WebSocket): Client | undefined {
    for (const client of this.clients.values()) {
      if (client.ws === ws) return client;
    }
    return undefined;
  }
}
```

`bus/client.ts` - Client library:
```typescript
import WebSocket from "ws";
import type { DSFEvent } from "./types";
import { EventEmitter } from "events";

export class AgentBusClient extends EventEmitter {
  private ws?: WebSocket;
  private url: string;
  private sessionId?: string;
  private reconnectInterval: NodeJS.Timeout | null = null;

  constructor(url: string = "ws://localhost:3031") {
    super();
    this.url = url;
  }

  async connect(auth: {
    agent_id: string;
    client_type: "cli" | "canvas" | "letta";
    client_id: string;
  }): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);

      this.ws.on("open", () => {
        // Authenticate
        this.ws!.send(JSON.stringify({
          type: "auth",
          payload: auth
        }));
      });

      this.ws.on("message", (data) => {
        const msg = JSON.parse(data.toString());

        if (msg.type === "auth_response") {
          if (msg.success) {
            this.sessionId = msg.payload.session_id;
            console.log("Connected to Agent Bus:", this.sessionId);
            resolve();
          } else {
            reject(new Error("Authentication failed"));
          }
        } else if (msg.type === "event") {
          this.handleEvent(msg.payload);
        }
      });

      this.ws.on("error", (err) => {
        console.error("WebSocket error:", err);
        reject(err);
      });

      this.ws.on("close", () => {
        console.log("Disconnected from Agent Bus");
        this.attemptReconnect();
      });
    });
  }

  subscribe(eventTypes: string[]) {
    if (!this.ws) throw new Error("Not connected");

    this.ws.send(JSON.stringify({
      type: "subscribe",
      payload: { event_types: eventTypes }
    }));
  }

  publish(event: Omit<DSFEvent, "id" | "timestamp">) {
    if (!this.ws) throw new Error("Not connected");

    this.ws.send(JSON.stringify({
      type: "publish",
      payload: { event }
    }));
  }

  private handleEvent(event: DSFEvent) {
    // Emit specific event type
    this.emit(event.type, event);
    // Also emit generic "event"
    this.emit("event", event);
  }

  private attemptReconnect() {
    if (this.reconnectInterval) return;

    this.reconnectInterval = setInterval(() => {
      console.log("Attempting to reconnect...");
      // Would need to store auth info to reconnect
      // For now, just clear interval
      clearInterval(this.reconnectInterval!);
      this.reconnectInterval = null;
    }, 5000);
  }

  disconnect() {
    if (this.reconnectInterval) {
      clearInterval(this.reconnectInterval);
    }
    if (this.ws) {
      this.ws.close();
    }
  }
}
```

#### Step 2: Update Canvas Server

Modify `letta-code/src/canvas/server.ts` to start Agent Bus:

```typescript
import { AgentBus } from "../bus/server";

// After existing server setup
const agentBus = new AgentBus(3031);

console.log("Services running:");
console.log("- Canvas UI: http://localhost:3030");
console.log("- Agent Bus: ws://localhost:3031");
```

#### Step 3: Test Agent Bus

Create `letta-code/src/bus/test.ts`:
```typescript
import { AgentBusClient } from "./client";

async function test() {
  // Create two clients
  const client1 = new AgentBusClient();
  const client2 = new AgentBusClient();

  await client1.connect({
    agent_id: "test-agent",
    client_type: "cli",
    client_id: "test-cli"
  });

  await client2.connect({
    agent_id: "test-agent",
    client_type: "canvas",
    client_id: "test-canvas"
  });

  // Subscribe to events
  client2.subscribe(["agent.*"]);

  // Listen for events
  client2.on("agent.message", (event) => {
    console.log("Client2 received:", event);
  });

  // Publish event
  client1.publish({
    type: "agent.message",
    payload: {
      content: "Hello from client1",
      role: "assistant"
    }
  });

  // Wait a bit then disconnect
  setTimeout(() => {
    client1.disconnect();
    client2.disconnect();
    process.exit(0);
  }, 1000);
}

test().catch(console.error);
```

Run test:
```bash
bun run src/bus/test.ts
```

Expected output:
```
Agent Bus listening on ws://localhost:3031
Client authenticated: <uuid> (cli)
Client authenticated: <uuid> (canvas)
Connected to Agent Bus: <uuid>
Connected to Agent Bus: <uuid>
Client2 received: { type: 'agent.message', id: '<uuid>', timestamp: ..., payload: { content: 'Hello from client1', role: 'assistant' } }
```

### Day 3-4: Canvas State Manager

Create `letta-code/src/tools/canvas/state.ts`:

```typescript
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { join } from "path";

export interface ComponentDefinition {
  type: string;
  id?: string;
  [key: string]: any;
}

export interface CanvasState {
  version: number;
  component_id: string;
  definition: ComponentDefinition;
  created_at: number;
  updated_at: number;
}

export class CanvasStateManager {
  private static instance: CanvasStateManager;
  private states: Map<string, CanvasState> = new Map();
  private stateDir: string;

  private constructor() {
    this.stateDir = join(process.cwd(), ".dsf", "canvas");
    if (!existsSync(this.stateDir)) {
      mkdirSync(this.stateDir, { recursive: true });
    }
    this.loadStates();
  }

  static getInstance(): CanvasStateManager {
    if (!this.instance) {
      this.instance = new CanvasStateManager();
    }
    return this.instance;
  }

  render(componentId: string, definition: ComponentDefinition): CanvasState {
    const state: CanvasState = {
      version: 1,
      component_id: componentId,
      definition,
      created_at: Date.now(),
      updated_at: Date.now()
    };

    this.states.set(componentId, state);
    this.persist(componentId);
    return state;
  }

  update(componentId: string, partial: Partial<ComponentDefinition>): {
    version: number;
    changes: string[];
  } {
    const state = this.states.get(componentId);
    if (!state) {
      throw new Error(`Component not found: ${componentId}`);
    }

    // Merge changes
    const changes = Object.keys(partial);
    state.definition = { ...state.definition, ...partial };
    state.version++;
    state.updated_at = Date.now();

    this.persist(componentId);
    return { version: state.version, changes };
  }

  remove(componentId: string): void {
    this.states.delete(componentId);
    const filePath = join(this.stateDir, `${componentId}.json`);
    if (existsSync(filePath)) {
      unlinkSync(filePath);
    }
  }

  get(componentId: string): CanvasState | undefined {
    return this.states.get(componentId);
  }

  query(queryString: string): any {
    // Simple query implementation
    if (queryString === "state") {
      return Array.from(this.states.values());
    }

    if (queryString.startsWith("component:")) {
      const id = queryString.split(":")[1];
      return this.states.get(id);
    }

    if (queryString.startsWith("type:")) {
      const type = queryString.split(":")[1];
      return Array.from(this.states.values())
        .filter(s => s.definition.type === type);
    }

    return null;
  }

  private persist(componentId: string): void {
    const state = this.states.get(componentId);
    if (!state) return;

    const filePath = join(this.stateDir, `${componentId}.json`);
    writeFileSync(filePath, JSON.stringify(state, null, 2));
  }

  private loadStates(): void {
    if (!existsSync(this.stateDir)) return;

    const files = readdirSync(this.stateDir).filter(f => f.endsWith(".json"));
    for (const file of files) {
      try {
        const content = readFileSync(join(this.stateDir, file), "utf-8");
        const state: CanvasState = JSON.parse(content);
        this.states.set(state.component_id, state);
      } catch (err) {
        console.error(`Failed to load state ${file}:`, err);
      }
    }

    console.log(`Loaded ${this.states.size} canvas states`);
  }
}
```

Create `letta-code/src/tools/canvas/validator.ts`:

```typescript
import type { ComponentDefinition } from "./state";

const VALID_TYPES = new Set([
  "Text", "Markdown", "Code", "Image", "Video", "Audio",
  "Button", "Input", "Select", "Slider", "Toggle",
  "Stack", "Grid", "Split", "Tabs", "Modal",
  "Timeline", "Gallery", "Diff", "Chart",
  "StorySegment", "WorldCard", "CharacterCard", "BranchExplorer"
]);

export function validateComponent(definition: ComponentDefinition): void {
  if (!definition.type) {
    throw new Error("Component definition must have a type");
  }

  if (!VALID_TYPES.has(definition.type)) {
    throw new Error(`Invalid component type: ${definition.type}`);
  }

  // Type-specific validation
  switch (definition.type) {
    case "Button":
      if (!definition.onClick) {
        throw new Error("Button must have onClick handler");
      }
      break;

    case "Split":
      if (!definition.children || definition.children.length !== 2) {
        throw new Error("Split must have exactly 2 children");
      }
      break;

    case "Stack":
    case "Grid":
      if (!definition.children || !Array.isArray(definition.children)) {
        throw new Error(`${definition.type} must have children array`);
      }
      break;

    // Add more validation rules as needed
  }
}
```

### Day 5-7: Canvas UI Tool

Create `letta-code/src/tools/impl/canvas_ui.ts`:

```typescript
import type { Tool } from "../types";
import { AgentBusClient } from "../../bus/client";
import { CanvasStateManager } from "../canvas/state";
import { validateComponent } from "../canvas/validator";

interface CanvasUIParams {
  operation: "render" | "update" | "remove" | "layout" | "query";
  component_id?: string;
  definition?: any;
  layout?: any;
  query?: string;
}

export const canvas_ui: Tool<CanvasUIParams> = {
  name: "canvas_ui",
  description: `Control the Canvas UI dynamically. Create layouts, render components, and respond to interactions.

Operations:
- render: Create new UI component tree
- update: Modify existing component properties
- remove: Delete component from canvas
- layout: Change layout configuration
- query: Get information about UI state

Use this to create rich visual presentations for stories, worlds, and interactive experiences.`,

  parameters: {
    type: "object",
    properties: {
      operation: {
        type: "string",
        enum: ["render", "update", "remove", "layout", "query"],
        description: "The operation to perform"
      },
      component_id: {
        type: "string",
        description: "Unique identifier for the component"
      },
      definition: {
        type: "object",
        description: "Component definition (for render/update)"
      },
      layout: {
        type: "object",
        description: "Layout configuration (for layout operation)"
      },
      query: {
        type: "string",
        description: "Query string (for query operation)"
      }
    },
    required: ["operation"]
  },

  handler: async (params: CanvasUIParams) => {
    const stateManager = CanvasStateManager.getInstance();
    const busClient = AgentBusClient.getInstance();

    switch (params.operation) {
      case "render": {
        if (!params.component_id || !params.definition) {
          throw new Error("render requires component_id and definition");
        }

        validateComponent(params.definition);
        const state = stateManager.render(params.component_id, params.definition);

        busClient.publish({
          type: "agent.canvas_update",
          payload: {
            operation: "render",
            component_id: params.component_id,
            definition: params.definition
          }
        });

        return {
          success: true,
          component_id: params.component_id,
          rendered_at: state.created_at,
          state_version: state.version
        };
      }

      case "update": {
        if (!params.component_id || !params.definition) {
          throw new Error("update requires component_id and definition");
        }

        const updated = stateManager.update(params.component_id, params.definition);

        busClient.publish({
          type: "agent.canvas_update",
          payload: {
            operation: "update",
            component_id: params.component_id,
            definition: params.definition
          }
        });

        return {
          success: true,
          component_id: params.component_id,
          updated_at: Date.now(),
          state_version: updated.version,
          changes: updated.changes
        };
      }

      case "remove": {
        if (!params.component_id) {
          throw new Error("remove requires component_id");
        }

        stateManager.remove(params.component_id);

        busClient.publish({
          type: "agent.canvas_update",
          payload: {
            operation: "remove",
            component_id: params.component_id
          }
        });

        return {
          success: true,
          component_id: params.component_id,
          removed_at: Date.now()
        };
      }

      case "query": {
        if (!params.query) {
          throw new Error("query requires query parameter");
        }

        const result = stateManager.query(params.query);

        return {
          success: true,
          query: params.query,
          result,
          timestamp: Date.now()
        };
      }

      default:
        throw new Error(`Unknown operation: ${params.operation}`);
    }
  }
};
```

Register tool in `letta-code/src/tools/index.ts`:
```typescript
import { canvas_ui } from "./impl/canvas_ui";

export const tools = [
  // ... existing tools
  canvas_ui
];
```

## Week 2: Canvas Client & UI Components

### Day 8-10: Canvas Client Integration

Update `letta-code/src/canvas/app.tsx` to connect to Agent Bus and render dynamic components:

```typescript
import { useEffect, useState } from "react";
import { AgentBusClient } from "../bus/client";
import type { ComponentDefinition } from "../tools/canvas/state";
import { ComponentRenderer } from "./components/renderer";

export function App() {
  const [busClient, setBusClient] = useState<AgentBusClient | null>(null);
  const [rootComponent, setRootComponent] = useState<ComponentDefinition | null>(null);

  useEffect(() => {
    // Connect to Agent Bus
    const client = new AgentBusClient("ws://localhost:3031");

    client.connect({
      agent_id: loadAgentId(), // Load from settings
      client_type: "canvas",
      client_id: generateClientId()
    }).then(() => {
      // Subscribe to canvas updates
      client.subscribe(["agent.canvas_update"]);

      // Handle canvas updates
      client.on("agent.canvas_update", (event) => {
        handleCanvasUpdate(event.payload);
      });

      setBusClient(client);
    });

    return () => {
      client?.disconnect();
    };
  }, []);

  const handleCanvasUpdate = (payload: any) => {
    switch (payload.operation) {
      case "render":
        if (!payload.component_id.includes(".")) {
          // Root component
          setRootComponent(payload.definition);
        } else {
          // Nested update - would need more complex state management
          console.log("TODO: Handle nested updates");
        }
        break;

      case "update":
        // Merge updates
        setRootComponent(prev => {
          if (!prev) return null;
          return { ...prev, ...payload.definition };
        });
        break;

      case "remove":
        setRootComponent(null);
        break;
    }
  };

  const handleInteraction = (componentId: string, interactionType: string, data: any, target?: string) => {
    if (!busClient) return;

    busClient.publish({
      type: "canvas.interaction",
      payload: {
        component_id: componentId,
        interaction_type: interactionType,
        data,
        target
      }
    });
  };

  return (
    <div className="canvas-root">
      {rootComponent ? (
        <ComponentRenderer
          definition={rootComponent}
          onInteraction={handleInteraction}
        />
      ) : (
        <div className="empty-state">
          <p>Waiting for agent to create UI...</p>
          <p className="hint">Try: "Create a story presentation"</p>
        </div>
      )}
    </div>
  );
}
```

### Day 11-12: Core Component Renderers

Create `letta-code/src/canvas/components/renderer.tsx`:

```typescript
import type { ComponentDefinition } from "../../tools/canvas/state";
import { Text } from "./primitives/text";
import { Markdown } from "./primitives/markdown";
import { Image } from "./primitives/image";
import { Button } from "./primitives/button";
import { Stack } from "./layouts/stack";
import { Grid } from "./layouts/grid";
import { Split } from "./layouts/split";
import { Card } from "./compositions/card";
import { Gallery } from "./visualizations/gallery";

interface RendererProps {
  definition: ComponentDefinition;
  onInteraction: (componentId: string, type: string, data: any, target?: string) => void;
}

export function ComponentRenderer({ definition, onInteraction }: RendererProps) {
  const { type, id, ...props } = definition;

  const handleClick = (target?: string, data?: any) => {
    if (id) {
      onInteraction(id, "click", data, target);
    }
  };

  // Map component types to renderers
  switch (type) {
    case "Text":
      return <Text {...props} />;

    case "Markdown":
      return <Markdown {...props} />;

    case "Image":
      return <Image {...props} onClick={props.onClick ? () => handleClick(props.onClick) : undefined} />;

    case "Button":
      return <Button {...props} onClick={() => handleClick(props.onClick, {})} />;

    case "Stack":
      return (
        <Stack {...props}>
          {props.children?.map((child: ComponentDefinition, i: number) => (
            <ComponentRenderer key={i} definition={child} onInteraction={onInteraction} />
          ))}
        </Stack>
      );

    case "Grid":
      return (
        <Grid {...props}>
          {props.children?.map((child: ComponentDefinition, i: number) => (
            <ComponentRenderer key={i} definition={child} onInteraction={onInteraction} />
          ))}
        </Grid>
      );

    case "Split":
      return (
        <Split {...props}>
          {props.children?.map((child: ComponentDefinition, i: number) => (
            <ComponentRenderer key={i} definition={child} onInteraction={onInteraction} />
          ))}
        </Split>
      );

    case "Card":
      return (
        <Card {...props}>
          {props.children && (
            <ComponentRenderer definition={props.children} onInteraction={onInteraction} />
          )}
        </Card>
      );

    case "Gallery":
      return <Gallery {...props} />;

    default:
      return <div className="unknown-component">Unknown component: {type}</div>;
  }
}
```

Create individual component implementations (examples):

`letta-code/src/canvas/components/primitives/text.tsx`:
```typescript
interface TextProps {
  content: string;
  variant?: "body" | "heading" | "caption" | "code";
  size?: "xs" | "sm" | "md" | "lg" | "xl" | "2xl";
  color?: string;
  align?: "left" | "center" | "right" | "justify";
}

export function Text({ content, variant = "body", size = "md", color, align = "left" }: TextProps) {
  return (
    <div
      className={`text-${variant} text-${size} text-${align}`}
      style={{ color }}
    >
      {content}
    </div>
  );
}
```

`letta-code/src/canvas/components/primitives/button.tsx`:
```typescript
interface ButtonProps {
  label: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  loading?: boolean;
  onClick: () => void;
}

export function Button({
  label,
  variant = "primary",
  size = "md",
  disabled,
  loading,
  onClick
}: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant} btn-${size}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? <Spinner /> : label}
    </button>
  );
}
```

`letta-code/src/canvas/components/layouts/stack.tsx`:
```typescript
import { ReactNode } from "react";

interface StackProps {
  children: ReactNode;
  direction?: "vertical" | "horizontal";
  spacing?: number;
  alignment?: "start" | "center" | "end" | "stretch";
}

export function Stack({
  children,
  direction = "vertical",
  spacing = 16,
  alignment = "stretch"
}: StackProps) {
  return (
    <div
      className="stack"
      style={{
        display: "flex",
        flexDirection: direction === "vertical" ? "column" : "row",
        gap: `${spacing}px`,
        alignItems: alignment === "stretch" ? "stretch" :
                   alignment === "center" ? "center" :
                   alignment === "end" ? "flex-end" : "flex-start"
      }}
    >
      {children}
    </div>
  );
}
```

### Day 13-14: Testing & Polish

Create test script `letta-code/src/canvas/test-canvas.ts`:

```typescript
import { canvas_ui } from "../tools/impl/canvas_ui";

async function test() {
  // Test render operation
  console.log("Testing render operation...");
  const result = await canvas_ui.handler({
    operation: "render",
    component_id: "test-card",
    definition: {
      type: "Card",
      children: {
        type: "Stack",
        spacing: 12,
        children: [
          {
            type: "Text",
            content: "Hello Canvas!",
            variant: "heading",
            size: "xl"
          },
          {
            type: "Text",
            content: "This is a test of the dynamic canvas system.",
            variant: "body"
          },
          {
            type: "Button",
            label: "Click Me",
            variant: "primary",
            onClick: "agent.test_click"
          }
        ]
      }
    }
  });

  console.log("Render result:", result);

  // Test update operation
  console.log("\nTesting update operation...");
  const updateResult = await canvas_ui.handler({
    operation: "update",
    component_id: "test-card",
    definition: {
      children: {
        children: [
          {
            type: "Text",
            content: "Updated content!",
            variant: "heading"
          }
        ]
      }
    }
  });

  console.log("Update result:", updateResult);

  // Test query operation
  console.log("\nTesting query operation...");
  const queryResult = await canvas_ui.handler({
    operation: "query",
    query: "state"
  });

  console.log("Query result:", queryResult);
}

test().catch(console.error);
```

**Final Integration Test:**

1. Start canvas server: `bun run src/canvas/server.ts`
2. Start CLI: `./deep-scifi.js`
3. In CLI, type: "Create a simple card with a heading and button"
4. Agent should use `canvas_ui` tool
5. Canvas should display the card in real-time
6. Click button in canvas
7. Agent should receive interaction event

## Success Checklist

- [ ] Agent Bus WebSocket server running on port 3031
- [ ] Agent Bus client library works (connection, pub/sub)
- [ ] Canvas State Manager stores and retrieves component definitions
- [ ] `canvas_ui` tool registered and callable by agent
- [ ] Canvas connects to Agent Bus on startup
- [ ] Canvas renders dynamic components from agent
- [ ] Canvas publishes interaction events back to agent
- [ ] Agent receives canvas interactions
- [ ] 5 core primitives work: Text, Button, Stack, Card, Image
- [ ] End-to-end flow: CLI → Agent → canvas_ui → Canvas → User → Interaction → Agent

## Next Steps (Phase 2)

After completing Phase 1:
- Add more component types (Gallery, Timeline, etc.)
- Implement nested component updates
- Add canvas state versioning (undo/redo)
- Build seamless CLI/Canvas switching
- Add canvas templates
- Performance optimization

## Troubleshooting

**Agent Bus not connecting:**
- Check ports (3030 for canvas HTTP, 3031 for Agent Bus WS)
- Verify WebSocket server started: `lsof -i :3031`
- Check client authentication payload

**Canvas not rendering components:**
- Check browser console for errors
- Verify Agent Bus connection (should see "Connected to Agent Bus" in console)
- Check component definition matches schema
- Verify event routing (should see events in Network tab)

**Agent not receiving interactions:**
- Verify agent subscribed to `canvas.interaction` events
- Check Agent Bus routing logic
- Verify event payload format
- Check Letta server logs

## Resources

- [WebSocket API Docs](https://github.com/websockets/ws)
- [React Component Patterns](https://reactpatterns.com/)
- [Agent Tool Development Guide](../letta-experiments/)
