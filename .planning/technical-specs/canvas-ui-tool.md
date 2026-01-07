# Canvas UI Tool: Technical Specification

## Overview

The `canvas_ui` tool allows the agent to dynamically create, update, and query UI components in the Canvas interface. This tool bridges the gap between conversational AI and visual presentation, enabling the agent to compose rich multimedia experiences.

## Tool Definition

```typescript
{
  name: "canvas_ui",
  description: `
    Control the Canvas UI dynamically. Create layouts, render components,
    handle interactions, and query UI state. Use this to create rich visual
    presentations for stories, worlds, and interactive explorations.

    Operations:
    - render: Create new UI components or replace existing ones
    - update: Modify specific properties of existing components
    - remove: Delete components from canvas
    - layout: Change layout configuration (sizes, orientation)
    - query: Get information about current UI state or user interactions

    Best practices:
    - Use render for initial UI creation or major changes
    - Use update for incremental changes (more efficient)
    - Always provide meaningful component_ids for tracking
    - Consider user context when choosing layouts
    - Query before updating to understand current state
  `,
  parameters: {
    operation: {
      type: "string",
      enum: ["render", "update", "remove", "layout", "query"],
      description: "The operation to perform"
    },
    component_id: {
      type: "string",
      description: "Unique identifier for the component (required for update/remove/layout)"
    },
    definition: {
      type: "object",
      description: "Component definition (required for render/update)"
    },
    layout: {
      type: "object",
      description: "Layout configuration (required for layout operation)"
    },
    query: {
      type: "string",
      description: "Query string for state inspection (required for query operation)"
    }
  },
  required: ["operation"]
}
```

## Operations

### 1. Render

Creates new UI component tree or replaces existing component.

**Parameters:**
```typescript
{
  operation: "render",
  component_id: string,
  definition: ComponentDefinition
}
```

**Example:**
```typescript
canvas_ui({
  operation: "render",
  component_id: "story-presentation-v1",
  definition: {
    type: "Split",
    direction: "horizontal",
    sizes: [65, 35],
    children: [
      {
        type: "Stack",
        spacing: 20,
        children: [
          {
            type: "StorySegment",
            id: "segment-1",
            content: "# The Neon Underground\n\nThe city breathed through...",
            theme: "dark"
          },
          {
            type: "Gallery",
            items: ["asset-img-001", "asset-img-002"],
            layout: "grid",
            columns: 2
          }
        ]
      },
      {
        type: "Sidebar",
        title: "Story Navigation",
        children: [
          {
            type: "Timeline",
            events: [
              { id: "seg-1", label: "Underground", timestamp: "Day 1" },
              { id: "seg-2", label: "The Market", timestamp: "Day 2" },
              { id: "seg-3", label: "Revelation", timestamp: "Day 3" }
            ],
            onSelect: "agent.navigate_segment"
          },
          {
            type: "Button",
            label: "Continue Story",
            variant: "primary",
            onClick: "agent.continue_story"
          }
        ]
      }
    ]
  }
})
```

**Returns:**
```typescript
{
  success: true,
  component_id: "story-presentation-v1",
  rendered_at: 1704067200000,
  state_version: 1
}
```

### 2. Update

Modifies specific properties of an existing component without recreating entire tree.

**Parameters:**
```typescript
{
  operation: "update",
  component_id: string, // Can be nested using dot notation: "root.sidebar.timeline"
  definition: Partial<ComponentDefinition>
}
```

**Example:**
```typescript
// Update story content
canvas_ui({
  operation: "update",
  component_id: "story-presentation-v1.segment-1",
  definition: {
    content: "# The Neon Underground\n\n[Updated content...]"
  }
})

// Add new item to gallery
canvas_ui({
  operation: "update",
  component_id: "story-presentation-v1.gallery",
  definition: {
    items: ["asset-img-001", "asset-img-002", "asset-img-003"] // appended new item
  }
})
```

**Returns:**
```typescript
{
  success: true,
  component_id: "story-presentation-v1.segment-1",
  updated_at: 1704067300000,
  state_version: 2,
  changes: ["content"]
}
```

### 3. Remove

Removes a component from the canvas.

**Parameters:**
```typescript
{
  operation: "remove",
  component_id: string
}
```

**Example:**
```typescript
canvas_ui({
  operation: "remove",
  component_id: "story-presentation-v1.sidebar"
})
```

**Returns:**
```typescript
{
  success: true,
  component_id: "story-presentation-v1.sidebar",
  removed_at: 1704067400000,
  state_version: 3
}
```

### 4. Layout

Changes layout configuration (sizes, orientation, etc.) without modifying children.

**Parameters:**
```typescript
{
  operation: "layout",
  component_id: string,
  layout: LayoutConfig
}
```

**Layout Config Types:**
```typescript
// Split layout
{
  sizes: [number, number], // percentage or pixels
  direction: "horizontal" | "vertical",
  resizable?: boolean
}

// Grid layout
{
  columns: number,
  gap: number,
  autoFlow: "row" | "column" | "dense"
}

// Stack layout
{
  spacing: number,
  alignment: "start" | "center" | "end" | "stretch"
}
```

**Example:**
```typescript
// Change split orientation and sizes
canvas_ui({
  operation: "layout",
  component_id: "story-presentation-v1",
  layout: {
    direction: "vertical",
    sizes: [70, 30]
  }
})
```

**Returns:**
```typescript
{
  success: true,
  component_id: "story-presentation-v1",
  updated_at: 1704067500000,
  state_version: 4,
  previous_layout: { direction: "horizontal", sizes: [65, 35] }
}
```

### 5. Query

Retrieves information about current UI state or user interactions.

**Parameters:**
```typescript
{
  operation: "query",
  query: string
}
```

**Query Types:**

#### State Queries
```typescript
// Get current component tree
canvas_ui({
  operation: "query",
  query: "state"
})
// Returns: Full component definition tree

// Get specific component
canvas_ui({
  operation: "query",
  query: "component:story-presentation-v1"
})
// Returns: Component definition + current state

// Get all components of type
canvas_ui({
  operation: "query",
  query: "type:Button"
})
// Returns: Array of all button components
```

#### Interaction Queries
```typescript
// Get last user interaction
canvas_ui({
  operation: "query",
  query: "last_interaction"
})
// Returns: { component_id, interaction_type, data, timestamp }

// Get interaction history
canvas_ui({
  operation: "query",
  query: "interactions:last:5"
})
// Returns: Array of last 5 interactions

// Get pending interactions (waiting for agent response)
canvas_ui({
  operation: "query",
  query: "pending_interactions"
})
// Returns: Array of interactions that triggered agent messages
```

#### Layout Queries
```typescript
// Get viewport size
canvas_ui({
  operation: "query",
  query: "viewport"
})
// Returns: { width, height, deviceType: "mobile" | "tablet" | "desktop" }

// Get component dimensions
canvas_ui({
  operation: "query",
  query: "dimensions:story-presentation-v1"
})
// Returns: { width, height, x, y, visible: boolean }
```

**Returns (varies by query type):**
```typescript
{
  success: true,
  query: string,
  result: any,
  timestamp: number
}
```

## Component Definitions

### Base Component

All components extend this base:

```typescript
interface BaseComponent {
  type: string;           // Component type (e.g., "Text", "Image")
  id?: string;           // Optional unique ID
  className?: string;    // CSS class names
  style?: CSSProperties; // Inline styles
  visible?: boolean;     // Visibility (default: true)
}
```

### Layout Components

#### Split
Divides space between two children:

```typescript
{
  type: "Split",
  direction: "horizontal" | "vertical",
  sizes: [number, number], // percentage [60, 40] or pixels [400, 600]
  resizable?: boolean,     // Allow user resize (default: true)
  minSizes?: [number, number], // Minimum sizes
  children: [ComponentDefinition, ComponentDefinition]
}
```

#### Stack
Vertical or horizontal stack with spacing:

```typescript
{
  type: "Stack",
  direction?: "vertical" | "horizontal", // default: vertical
  spacing?: number,                       // gap between items (px)
  alignment?: "start" | "center" | "end" | "stretch",
  children: ComponentDefinition[]
}
```

#### Grid
CSS Grid layout:

```typescript
{
  type: "Grid",
  columns?: number,              // number of columns (auto if not specified)
  gap?: number,                  // gap between items (px)
  autoFlow?: "row" | "column" | "dense",
  children: ComponentDefinition[]
}
```

#### Tabs
Tabbed interface:

```typescript
{
  type: "Tabs",
  tabs: Array<{
    id: string,
    label: string,
    icon?: string,
    content: ComponentDefinition
  }>,
  defaultTab?: string,           // default active tab
  onChange?: string              // event handler
}
```

#### Modal
Overlay modal:

```typescript
{
  type: "Modal",
  title?: string,
  open: boolean,
  onClose?: string,              // event handler
  size?: "small" | "medium" | "large" | "fullscreen",
  children: ComponentDefinition[]
}
```

### Content Components

#### Text
Simple text content:

```typescript
{
  type: "Text",
  content: string,
  variant?: "body" | "heading" | "caption" | "code",
  size?: "xs" | "sm" | "md" | "lg" | "xl" | "2xl",
  color?: string,
  align?: "left" | "center" | "right" | "justify"
}
```

#### Markdown
Rendered markdown content:

```typescript
{
  type: "Markdown",
  content: string,
  theme?: "light" | "dark",
  syntaxHighlight?: boolean,     // highlight code blocks
  linkTarget?: "_blank" | "_self"
}
```

#### Code
Syntax-highlighted code:

```typescript
{
  type: "Code",
  code: string,
  language: string,              // e.g., "typescript", "python"
  theme?: "light" | "dark" | "nord" | "dracula",
  lineNumbers?: boolean,
  highlightLines?: number[],     // lines to highlight
  onCopy?: string                // event handler when user copies
}
```

#### Image
Image display:

```typescript
{
  type: "Image",
  src: string,                   // asset_id or URL
  alt: string,
  fit?: "cover" | "contain" | "fill" | "scale-down",
  width?: number | string,
  height?: number | string,
  onClick?: string,              // event handler
  caption?: string
}
```

#### Video
Video player:

```typescript
{
  type: "Video",
  src: string,                   // asset_id or URL
  poster?: string,               // thumbnail
  autoPlay?: boolean,
  loop?: boolean,
  controls?: boolean,
  muted?: boolean
}
```

#### Audio
Audio player:

```typescript
{
  type: "Audio",
  src: string,                   // asset_id or URL
  autoPlay?: boolean,
  loop?: boolean,
  controls?: boolean,
  visualizer?: boolean           // show waveform visualizer
}
```

### Interactive Components

#### Button
Clickable button:

```typescript
{
  type: "Button",
  label: string,
  variant?: "primary" | "secondary" | "ghost" | "danger",
  size?: "sm" | "md" | "lg",
  icon?: string,                 // icon name or asset_id
  disabled?: boolean,
  loading?: boolean,             // show spinner
  onClick: string                // event handler (required)
}
```

#### Input
Text input field:

```typescript
{
  type: "Input",
  placeholder?: string,
  defaultValue?: string,
  type?: "text" | "password" | "email" | "number" | "url",
  disabled?: boolean,
  onChange?: string,             // event handler
  onSubmit?: string              // event handler (on Enter key)
}
```

#### Select
Dropdown selection:

```typescript
{
  type: "Select",
  options: Array<{ value: string, label: string }>,
  defaultValue?: string,
  placeholder?: string,
  disabled?: boolean,
  onChange: string               // event handler (required)
}
```

#### Slider
Numeric slider:

```typescript
{
  type: "Slider",
  min: number,
  max: number,
  step?: number,
  defaultValue?: number,
  label?: string,
  showValue?: boolean,
  onChange: string               // event handler (required)
}
```

#### Toggle
Boolean toggle/switch:

```typescript
{
  type: "Toggle",
  label: string,
  defaultValue?: boolean,
  disabled?: boolean,
  onChange: string               // event handler (required)
}
```

### Visualization Components

#### Timeline
Event timeline:

```typescript
{
  type: "Timeline",
  events: Array<{
    id: string,
    label: string,
    timestamp?: string,          // display text
    description?: string,
    icon?: string,
    color?: string
  }>,
  orientation?: "vertical" | "horizontal",
  onSelect?: string              // event handler when event clicked
}
```

#### Gallery
Image/asset gallery:

```typescript
{
  type: "Gallery",
  items: string[],               // array of asset_ids
  layout?: "grid" | "masonry" | "carousel",
  columns?: number,              // for grid layout
  gap?: number,
  lightbox?: boolean,            // enable fullscreen view on click
  onSelect?: string              // event handler
}
```

#### Diff
Side-by-side diff viewer:

```typescript
{
  type: "Diff",
  before: string,
  after: string,
  language?: string,             // for syntax highlighting
  theme?: "light" | "dark",
  mode?: "split" | "unified"
}
```

#### Chart
Data visualization (using recharts):

```typescript
{
  type: "Chart",
  chartType: "line" | "bar" | "pie" | "area" | "scatter",
  data: Array<Record<string, any>>,
  xKey: string,
  yKey: string | string[],
  title?: string,
  legend?: boolean,
  theme?: "light" | "dark"
}
```

### Story-Specific Components

#### StorySegment
Rich story content with embedded assets:

```typescript
{
  type: "StorySegment",
  content: string,               // markdown content
  assets?: string[],             // embedded asset_ids
  theme?: "light" | "dark",
  metadata?: {
    segment_id: string,
    story_id: string,
    author?: string,
    timestamp?: string
  }
}
```

#### WorldCard
World overview card:

```typescript
{
  type: "WorldCard",
  world_id: string,
  coverImage?: string,           // asset_id
  title: string,
  description: string,
  stats?: {
    stories: number,
    characters: number,
    locations: number
  },
  actions?: Array<{
    label: string,
    onClick: string              // event handler
  }>
}
```

#### CharacterCard
Character profile card:

```typescript
{
  type: "CharacterCard",
  name: string,
  avatar?: string,               // asset_id
  role?: string,
  description: string,
  traits?: string[],
  onClick?: string               // event handler
}
```

#### BranchExplorer
Visual story branch navigator:

```typescript
{
  type: "BranchExplorer",
  story_id: string,
  branches: Array<{
    id: string,
    label: string,
    description?: string,
    segments: number,
    thumbnail?: string           // asset_id
  }>,
  currentBranch?: string,
  onSelect: string               // event handler
}
```

## Event Handlers

When user interacts with components, events are sent to the agent via Agent Bus.

### Handler Format

Handlers are strings in format: `target.action`

Examples:
- `agent.navigate_segment` - Calls agent with navigation request
- `agent.continue_story` - Asks agent to continue story
- `canvas.update_layout` - Updates canvas layout directly (no agent)

### Handler Execution

When component triggers event:

1. **Canvas captures interaction**
```typescript
{
  component_id: "timeline",
  interaction_type: "click",
  data: { event_id: "seg-2" },
  target: "agent.navigate_segment"
}
```

2. **Canvas publishes to Agent Bus**
```typescript
{
  type: "canvas.interaction",
  payload: { /* interaction data */ }
}
```

3. **Agent receives and processes**
```typescript
// Agent's system prompt includes:
// "When you receive canvas.interaction events, respond appropriately"

// Agent sees:
"User clicked Timeline event 'seg-2'. They want to navigate to segment 2."

// Agent responds:
canvas_ui({
  operation: "update",
  component_id: "segment-1",
  definition: {
    content: "[Segment 2 content...]"
  }
})
```

### Predefined Handlers

Some handlers are handled by canvas directly (no agent roundtrip):

- `canvas.scroll_to` - Scroll to component
- `canvas.focus` - Focus input element
- `canvas.copy` - Copy content to clipboard
- `canvas.download` - Download asset
- `canvas.fullscreen` - Toggle fullscreen mode

Use these for instant UI feedback without agent latency.

## Tool Implementation

### File Structure

```
letta-code/src/tools/impl/
├── canvas_ui.ts          # Main tool implementation
├── canvas/
│   ├── state.ts          # Canvas state manager
│   ├── validator.ts      # Component definition validation
│   ├── serializer.ts     # Component serialization
│   └── components/       # Component type definitions
│       ├── layout.ts
│       ├── content.ts
│       ├── interactive.ts
│       ├── visualization.ts
│       └── story.ts
```

### Core Logic

```typescript
// canvas_ui.ts
import { AgentBusClient } from "../../bus/client";
import { CanvasStateManager } from "./canvas/state";
import { validateComponent } from "./canvas/validator";

export async function canvas_ui({
  operation,
  component_id,
  definition,
  layout,
  query
}: CanvasUIParams): Promise<CanvasUIResult> {

  // Get canvas state manager
  const stateManager = CanvasStateManager.getInstance();

  // Get agent bus client
  const busClient = AgentBusClient.getInstance();

  switch (operation) {
    case "render":
      // Validate component definition
      validateComponent(definition);

      // Store in state
      const state = stateManager.render(component_id, definition);

      // Publish to agent bus
      busClient.publish({
        type: "agent.canvas_update",
        payload: {
          operation: "render",
          component_id,
          definition
        }
      });

      return {
        success: true,
        component_id,
        rendered_at: Date.now(),
        state_version: state.version
      };

    case "update":
      // Update state
      const updated = stateManager.update(component_id, definition);

      // Publish update
      busClient.publish({
        type: "agent.canvas_update",
        payload: {
          operation: "update",
          component_id,
          definition
        }
      });

      return {
        success: true,
        component_id,
        updated_at: Date.now(),
        state_version: updated.version,
        changes: updated.changes
      };

    case "remove":
      stateManager.remove(component_id);

      busClient.publish({
        type: "agent.canvas_update",
        payload: {
          operation: "remove",
          component_id
        }
      });

      return {
        success: true,
        component_id,
        removed_at: Date.now()
      };

    case "layout":
      const layoutUpdate = stateManager.updateLayout(component_id, layout);

      busClient.publish({
        type: "agent.canvas_update",
        payload: {
          operation: "layout",
          component_id,
          layout
        }
      });

      return {
        success: true,
        component_id,
        updated_at: Date.now(),
        previous_layout: layoutUpdate.previous
      };

    case "query":
      // Execute query
      const result = stateManager.query(query);

      return {
        success: true,
        query,
        result,
        timestamp: Date.now()
      };

    default:
      throw new Error(`Unknown operation: ${operation}`);
  }
}
```

## System Prompt Integration

Add to agent's system prompt:

```markdown
### Canvas UI Control

You have access to the canvas_ui tool which allows you to create dynamic,
interactive UI presentations in the Canvas interface.

When to use canvas_ui:
- Creating rich visual presentations for stories
- Building interactive explorations of worlds
- Displaying multimedia content (images, videos, audio)
- Creating custom layouts for complex information
- Responding to user interactions from canvas

Best practices:
- Start with a clear layout structure (Split, Stack, Grid)
- Use meaningful component_ids for tracking
- Query state before updating to understand current context
- Respond to canvas interactions promptly
- Consider user's viewport and device type
- Use appropriate components for content (StorySegment for stories, etc.)

Example: Creating a story presentation
canvas_ui({
  operation: "render",
  component_id: "story-v1",
  definition: {
    type: "Split",
    children: [
      { type: "StorySegment", content: "..." },
      { type: "Sidebar", children: [...] }
    ]
  }
})

When you receive canvas.interaction events, respond by updating the UI
or continuing the conversation as appropriate.
```

## Testing Strategy

### Unit Tests
- Component validation
- State management operations
- Event handler resolution
- Query parsing and execution

### Integration Tests
- Tool execution → State update → Event publication
- Canvas receives events and renders
- User interaction → Event → Agent response
- State persistence and recovery

### E2E Tests
- Agent creates complex layout → User sees it in canvas
- User clicks button → Agent receives event → Canvas updates
- Multi-step interactions (navigation, form submission)
- Error handling (invalid component, state conflicts)

## Performance Considerations

1. **Incremental Updates** - Use `update` instead of `render` when possible
2. **Lazy Loading** - Load assets on-demand
3. **Virtual Scrolling** - For long lists (timelines, galleries)
4. **Debouncing** - Batch rapid updates
5. **State Diffing** - Only send changed properties to canvas
6. **Component Memoization** - Cache rendered components

## Error Handling

```typescript
// Validation errors
{
  success: false,
  error: "Invalid component definition",
  details: {
    component_type: "Button",
    missing_fields: ["onClick"],
    invalid_fields: ["variant"]
  }
}

// State errors
{
  success: false,
  error: "Component not found",
  component_id: "nonexistent-id"
}

// Query errors
{
  success: false,
  error: "Invalid query",
  query: "unknown:command"
}
```

## Migration from Current System

### Phase 1: Parallel Operation
- Implement canvas_ui tool
- Keep existing file-based rendering
- Canvas displays both: file-based content + UI components

### Phase 2: Gradual Migration
- Update system prompt to suggest canvas_ui for new creations
- Existing content continues to render from files
- New content uses canvas_ui

### Phase 3: Full Migration
- All story/world viewing goes through canvas_ui
- Files become pure data storage
- Canvas is fully dynamic and agent-controlled
