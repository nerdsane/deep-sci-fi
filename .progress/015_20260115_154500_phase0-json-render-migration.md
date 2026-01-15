# Phase 0: json-render Standards Migration

**Agent:** A
**Created:** 2026-01-15 15:45:00
**Status:** PLANNING → IMPLEMENTING
**Branch:** main
**Duration:** 2 weeks (parallel with Agent B's Phase 3)

---

## Mission

Migrate Deep Sci-Fi's custom Agent Bus protocol to **json-render** (Vercel's declarative JSON framework) for type safety, security, and standards compliance - **WITHOUT breaking the existing immersive 3D UX**.

**Key Constraint:** Phase 3 (World Space components) is being built **IN PARALLEL** by Agent B. I'll integrate their components as they're built.

---

## Context: Current Architecture

### What We Have
- **Custom ComponentSpec format**: 17 component types (Dialog, Button, Text, Stack, Grid, etc.)
- **DynamicRenderer**: Switch-statement based renderer (340 lines)
- **Agent Bus WebSocket**: Port 8284, bidirectional communication
- **Message format**: `CanvasUIMessage` with `ComponentSpec` in `spec` field
- **3D Observatory**: Independent layer (unchanged in this phase)

### Key Files
```
letta-code/src/
├── agent-bus/types.ts              (234 lines) - Message protocol
├── tools/impl/canvas_ui.ts         (313 lines) - Agent tool
└── canvas/components/types.ts      (273 lines) - ComponentSpec definitions

apps/web/
├── components/canvas/
│   ├── DynamicRenderer.tsx         (340 lines) - Main replacement target
│   ├── MountPoint.tsx              (92 lines) - Works with any spec
│   ├── types.ts                    - Component type definitions
│   ├── observatory/                - 3D UI (unchanged)
│   ├── primitives/                 - Component implementations
│   ├── layout/                     - Layout components
│   └── experience/                 - Experience components
└── app/page.tsx                    (2000+ lines) - State management
```

### What We're Changing
1. **Component catalog** with Zod schemas (NEW)
2. **json-render tree format** for messages (CHANGED)
3. **json-render Renderer** replaces DynamicRenderer (REPLACED)
4. **Type safety throughout** (NEW)

### What We're Keeping
- WebSocket transport (works great!)
- Message envelope structure (stable)
- 3D Observatory (our differentiator)
- Mount point system (adapter pattern)
- Interaction callbacks (works as-is)

---

## Goals by Week

### Week 1: Foundation (Days 1-5)
**Goal:** Install json-render, create catalog with existing components, migrate message format

**Tasks:**
1. ✅ Read architecture and research documents
2. ✅ Understand current ComponentSpec system
3. ✅ Install json-render packages (@json-render/core@0.2.0, @json-render/react@0.2.0, zod@4.3.5)
4. ✅ Create component catalog with Zod schemas (apps/web/lib/agent-ui/catalog.ts)
5. ✅ Map existing 17 component types to catalog (all components mapped with Zod schemas)
6. ✅ Update message types to json-render tree format (both letta-code and apps/web)
7. ✅ Create json-render renderer component (apps/web/lib/agent-ui/renderer.tsx)
8. ⏳ Test with existing Observatory components

**End of Week 1 Checkpoint:**
- Get TypeScript prop interfaces from Agent B (Phase 3 components)
- They'll commit to `apps/web/components/canvas/world/types.ts`

### Week 2: Integration (Days 6-10)
**Goal:** Add Phase 3 components to catalog, update tools, add streaming

**Tasks:**
1. ⏳ Monitor Agent B's commits for new components
2. ⏳ Add Phase 3 components to catalog as they're built
3. ⏳ Update `canvas_ui` tool to emit json-render format
4. ⏳ Add streaming support (progressive rendering)
5. ⏳ Test catalog with all components
6. ⏳ Update interaction handlers

### Week 3: Finalization (Days 11-14)
**Goal:** Complete migration, verify all components, document

**Tasks:**
1. ⏳ Ensure all Phase 3 components in catalog
2. ⏳ Zod validation passing for all props
3. ⏳ Remove old DynamicRenderer (if fully migrated)
4. ⏳ Documentation for future component additions
5. ⏳ Test entire flow end-to-end
6. ⏳ Commit and push changes

---

## Implementation Plan

### Phase 1.1: Install json-render (Day 1)

**File:** `apps/web/package.json`

```bash
cd apps/web
bun add @json-render/core @json-render/react zod
```

**Verify installation:**
```bash
bun run typecheck
```

### Phase 1.2: Create Component Catalog (Days 1-2)

**File:** `apps/web/lib/agent-ui/catalog.ts` (NEW)

**Structure:**
```typescript
import { createCatalog } from '@json-render/core';
import { z } from 'zod';

// Import existing components
import { Button } from '@/components/canvas/primitives/Button';
import { Text } from '@/components/canvas/primitives/Text';
// ... rest of imports

// Define Zod schemas for each component
const ButtonSchema = z.object({
  label: z.string(),
  variant: z.enum(['primary', 'secondary', 'ghost']).optional(),
  size: z.enum(['sm', 'md', 'lg']).optional(),
  disabled: z.boolean().optional(),
  onClick: z.string().optional(), // Event handler name
});

// Create catalog
export const catalog = createCatalog({
  components: {
    Button: {
      component: Button,
      props: ButtonSchema,
      hasChildren: false,
    },
    Text: {
      component: Text,
      props: z.object({
        content: z.string(),
        variant: z.enum(['body', 'heading', 'caption']).optional(),
        color: z.string().optional(),
      }),
      hasChildren: false,
    },
    // ... 15 more components
  },

  actions: {
    navigateToWorld: {
      params: z.object({
        worldId: z.string(),
      })
    },
    selectSuggestion: {
      params: z.object({
        suggestionId: z.string(),
      })
    },
    startStory: {
      params: z.object({
        storyId: z.string(),
        worldId: z.string(),
      })
    },
  }
});

export type ComponentCatalog = typeof catalog;
```

**Component Mapping:**
1. Button → ButtonSchema
2. Text → TextSchema
3. Dialog → DialogSchema
4. Stack → StackSchema
5. Grid → GridSchema
6. Image → ImageSchema
7. Gallery → GallerySchema
8. Card → CardSchema
9. Timeline → TimelineSchema
10. Callout → CalloutSchema
11. Stats → StatsSchema
12. Hero → HeroSchema
13. ScrollSection → ScrollSectionSchema
14. ProgressBar → ProgressBarSchema
15. ActionBar → ActionBarSchema
16. Badge → BadgeSchema
17. Divider → DividerSchema

**Note:** Skip RawJsx (security risk) - will handle in Phase 3 if needed

### Phase 1.3: Create json-render Renderer (Day 2)

**File:** `apps/web/lib/agent-ui/renderer.tsx` (NEW)

```typescript
'use client';

import { Renderer as JsonRenderer } from '@json-render/react';
import { catalog } from './catalog';

interface AgentUIRendererProps {
  tree: any;
  onAction?: (action: string, params: any) => void;
}

export function AgentUIRenderer({ tree, onAction }: AgentUIRendererProps) {
  const handleAction = (action: string, params: any) => {
    console.log('[AgentUIRenderer] Action:', action, params);
    onAction?.(action, params);
  };

  return (
    <JsonRenderer
      catalog={catalog}
      tree={tree}
      onAction={handleAction}
    />
  );
}
```

### Phase 1.4: Update Agent Bus Types (Day 3)

**File:** `letta-code/src/agent-bus/types.ts`

**Before:**
```typescript
export type CanvasUIMessage = {
  type: 'canvas_ui';
  action: 'create' | 'update' | 'remove';
  target: string;
  componentId: string;
  spec?: ComponentSpec; // Old custom format
  mode?: 'overlay' | 'fullscreen' | 'inline';
};
```

**After:**
```typescript
export type CanvasUIMessage = {
  type: 'canvas_ui';
  action: 'create' | 'update' | 'remove';
  target: string;
  componentId: string;
  tree?: {
    type: string;
    props: Record<string, unknown>;
    key: string;
    children?: Array<any>;
  }; // json-render format
  mode?: 'overlay' | 'fullscreen' | 'inline';
};

// Keep old format for backwards compatibility during transition
export type LegacyCanvasUIMessage = {
  type: 'canvas_ui';
  action: 'create' | 'update' | 'remove';
  target: string;
  componentId: string;
  spec?: ComponentSpec; // OLD
  mode?: 'overlay' | 'fullscreen' | 'inline';
};
```

**File:** `apps/web/agent-bus/types.ts`

Update matching types in apps/web version.

### Phase 1.5: Update Canvas UI Tool (Day 3)

**File:** `letta-code/src/tools/impl/canvas_ui.ts`

**Before:**
```typescript
export async function canvas_ui(args: CanvasUIArgs): Promise<CanvasUIResult> {
  const ws = await ensureAgentBusConnection();

  const message: CanvasUIMessage = {
    type: 'canvas_ui',
    action: args.action || 'create',
    target: args.target,
    componentId: args.spec?.id || generateId(),
    spec: args.spec,
    mode: args.mode,
  };

  ws.send(JSON.stringify(message));
  return { status: 'success' };
}
```

**After:**
```typescript
// Helper to convert ComponentSpec to json-render tree
function componentSpecToTree(spec: ComponentSpec): JsonRenderTree {
  return {
    type: spec.type,
    props: spec.props || {},
    key: spec.id || generateId(),
    children: spec.children
      ? Array.isArray(spec.children)
        ? spec.children.map(componentSpecToTree)
        : [componentSpecToTree(spec.children)]
      : undefined,
  };
}

export async function canvas_ui(args: CanvasUIArgs): Promise<CanvasUIResult> {
  const ws = await ensureAgentBusConnection();

  const tree = args.spec ? componentSpecToTree(args.spec) : undefined;

  const message: CanvasUIMessage = {
    type: 'canvas_ui',
    action: args.action || 'create',
    target: args.target,
    componentId: tree?.key || generateId(),
    tree: tree, // json-render format
    mode: args.mode,
  };

  ws.send(JSON.stringify(message));
  return { status: 'success' };
}
```

**Note:** This maintains backwards compatibility - agents still use ComponentSpec, tool converts to json-render tree.

### Phase 1.6: Update Canvas UI Rendering (Days 4-5)

**File:** `apps/web/app/page.tsx`

**Before:**
```typescript
// In wsClient.onCanvasUI handler
<DynamicRenderer
  spec={entry.spec}
  onInteraction={handleInteraction}
/>
```

**After:**
```typescript
import { AgentUIRenderer } from '@/lib/agent-ui/renderer';

// In wsClient.onCanvasUI handler
<AgentUIRenderer
  tree={entry.tree}
  onAction={(action, params) => {
    wsClient.sendInteraction({
      type: 'interaction',
      componentId: entry.componentId,
      interactionType: action,
      data: params,
    });
  }}
/>
```

**File:** `apps/web/components/canvas/MountPoint.tsx`

Update to handle both `spec` and `tree` formats during transition:

```typescript
interface MountPointProps {
  target: string;
  components: Array<{
    componentId: string;
    spec?: ComponentSpec;  // OLD - for backwards compat
    tree?: JsonRenderTree; // NEW - json-render format
  }>;
  onInteraction: (componentId: string, type: string, data: any) => void;
  className?: string;
  layout?: 'vertical' | 'horizontal';
  spacing?: number;
}

// Render with conditional logic
{components.map(({ componentId, spec, tree }) => (
  <div key={componentId} className="mount-point-item">
    {tree ? (
      <AgentUIRenderer
        tree={tree}
        onAction={(action, params) => onInteraction(componentId, action, params)}
      />
    ) : spec ? (
      <DynamicRenderer
        spec={spec}
        onInteraction={onInteraction}
      />
    ) : null}
  </div>
))}
```

### Phase 1.7: Testing (Day 5)

**Test 1: Existing Components Still Work**

```bash
cd apps/web
bun run dev

# In browser console or via CLI:
agentBus.emit({
  type: 'canvas_ui',
  action: 'create',
  target: 'test-mount',
  componentId: 'test-button-1',
  tree: {
    type: 'Button',
    props: {
      label: 'Test Button',
      variant: 'primary',
      onClick: 'handleTestClick',
    },
    key: 'test-button-1',
  },
  mode: 'inline',
});
```

**Test 2: Type Validation Works**

```typescript
// This should FAIL validation (missing required label)
agentBus.emit({
  type: 'canvas_ui',
  tree: {
    type: 'Button',
    props: {
      variant: 'primary',
    },
    key: 'invalid-button',
  },
});

// json-render should throw Zod validation error
```

**Test 3: Actions Work**

```typescript
// Click button in UI
// Should receive InteractionMessage with action name
{
  type: 'interaction',
  componentId: 'test-button-1',
  interactionType: 'handleTestClick',
  data: { ... },
}
```

---

## Phase 2: Agent B Integration (Week 2)

### Phase 2.1: Monitor Agent B Commits (Days 6-10)

**Watch for:**
- `apps/web/components/canvas/world/types.ts` (prop interfaces)
- `apps/web/components/canvas/world/*.tsx` (new components)

**Expected Components from Agent B:**
1. InteractiveWorldMap
2. TechArtifact
3. CharacterReveal
4. StoryPortal
5. (More TBD)

### Phase 2.2: Add Phase 3 Components to Catalog (As built)

**File:** `apps/web/lib/agent-ui/catalog.ts`

```typescript
// When Agent B commits InteractiveWorldMap
import { InteractiveWorldMap } from '@/components/canvas/world/InteractiveWorldMap';
import type { WorldMapProps } from '@/components/canvas/world/types';

// Add to catalog
InteractiveWorldMap: {
  component: InteractiveWorldMap,
  props: z.object({
    worldId: z.string(),
    locations: z.array(LocationSchema),
    connections: z.array(ConnectionSchema).optional(),
    selectedLocation: z.string().optional(),
    onLocationClick: z.function().optional(),
    onLocationHover: z.function().optional(),
  }),
  hasChildren: false,
},
```

**Process:**
1. Watch for Agent B commits
2. Import new component
3. Create Zod schema from TypeScript interface
4. Add to catalog
5. Test component rendering
6. Commit and push

### Phase 2.3: Add Streaming Support (Days 8-9)

**Goal:** Progressive rendering as agent sends tree chunks

**Research:** json-render streaming API
**Implementation:** TBD based on json-render docs

---

## Phase 3: Finalization (Week 3)

### Phase 3.1: Complete Migration (Days 11-12)

**Tasks:**
1. All Phase 3 components in catalog ✓
2. Remove backwards compatibility shims
3. Delete old DynamicRenderer.tsx (if fully migrated)
4. Update all message handlers
5. Run full test suite

### Phase 3.2: Documentation (Day 13)

**Create:** `apps/web/lib/agent-ui/README.md`

**Contents:**
- How to add new components to catalog
- Zod schema patterns
- Testing components
- Action handling
- Streaming (if implemented)

### Phase 3.3: Final Testing & Commit (Day 14)

**Test Cases:**
1. All existing Observatory components render
2. All Phase 3 components render (from Agent B)
3. Type validation catches errors
4. Actions trigger interactions
5. Streaming works (if implemented)
6. No console errors
7. No TypeScript errors

**Commit:**
```bash
git add .
git commit -m "feat: migrate to json-render for type-safe agent-driven UI

- Add json-render and Zod packages
- Create component catalog with 17+ components
- Update Agent Bus message format to json-render tree
- Replace DynamicRenderer with AgentUIRenderer
- Add Zod validation for all component props
- Integrate Phase 3 components from Agent B
- Maintain backwards compatibility during transition
- Add streaming support for progressive rendering

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

git push origin main
```

---

## Coordination with Agent B

### Week 1 End Checkpoint
**I need from Agent B:**
- TypeScript prop interfaces for Phase 3 components
- File: `apps/web/components/canvas/world/types.ts`
- Components: InteractiveWorldMap, TechArtifact, CharacterReveal, StoryPortal

**I provide to Agent B:**
- Component catalog API documentation
- Zod schema patterns for their components
- Testing guidelines

### Week 2+ Ongoing
**I do:**
- Monitor Agent B's commits
- Add their components to catalog immediately
- Test integration
- Report any type mismatches

**Agent B does:**
- Build Phase 3 components independently
- Follow TypeScript interface patterns
- Commit to `apps/web/components/canvas/world/`

---

## Success Criteria

**End of Phase 0 (Week 3):**
- [x] json-render packages installed
- [ ] Component catalog with 17+ components
- [ ] All existing components migrated
- [ ] All Phase 3 components in catalog
- [ ] Zod validation passing
- [ ] Agent tools emit json-render format
- [ ] Streaming support working
- [ ] No breaking changes to UX
- [ ] Type safety throughout
- [ ] Tests passing
- [ ] Documentation complete

---

## Blockers & Risks

### Potential Blockers
1. **Agent B delay** - If Phase 3 components aren't ready by Week 2
   - Mitigation: Continue with existing components, add Phase 3 later
2. **json-render API changes** - If package updates break API
   - Mitigation: Pin versions in package.json
3. **Type mismatches** - Component props don't match Zod schemas
   - Mitigation: Iterative testing and schema refinement

### Known Risks
1. **Backwards compatibility** - Old messages might break
   - Mitigation: Support both formats during transition
2. **Performance** - json-render overhead
   - Mitigation: Profile and optimize if needed
3. **RawJsx components** - Not in json-render catalog
   - Mitigation: Migrate away from RawJsx or create secure wrapper

---

## Instance Log

**Agent A (This instance):**
- **Status:** PLANNING
- **Current Phase:** 1.1 (Install json-render)
- **Last Updated:** 2026-01-15 15:45:00
- **Claiming:** All Phase 0 tasks

**Agent B:**
- **Status:** Working on Phase 3 (parallel)
- **Responsibility:** World Space components
- **Coordination:** Will provide prop interfaces end of Week 1

---

## Findings & Decisions

### Finding 1: DynamicRenderer is 340 lines
**Decision:** Replace entirely with AgentUIRenderer (json-render)
**Rationale:** Switch statement is hard to maintain, json-render handles recursion automatically

### Finding 2: 17 component types currently supported
**Decision:** Migrate all 17 to catalog, skip RawJsx for security
**Rationale:** RawJsx allows arbitrary JSX execution, violates json-render security model

### Finding 3: Agent Bus WebSocket works well
**Decision:** Keep WebSocket transport, just change message payload
**Rationale:** No need to replace working transport layer

### Finding 4: ComponentSpec uses event handler names (strings)
**Decision:** Map to json-render actions
**Rationale:** json-render has first-class action support, perfect fit

---

## Next Steps

1. ✅ Complete planning
2. ⏳ Install json-render packages
3. ⏳ Create component catalog
4. ⏳ Map 17 existing components
5. ⏳ Update message types
6. ⏳ Create AgentUIRenderer
7. ⏳ Test with existing components
8. ⏳ Coordinate with Agent B for Week 1 checkpoint

**Current Task:** Install json-render packages

---

## Resources

- **Research:** `.progress/014_20260115_agent-driven-ui-research.md`
- **Handoff:** `.progress/HANDOFF_AGENT_A_PHASE_0.md`
- **Ultra Plan:** `.progress/013_20260110_immersive-ux-ultraplan.md`
- **json-render docs:** https://json-render.dev/
- **json-render GitHub:** https://github.com/vercel-labs/json-render
- **Zod docs:** https://zod.dev/
- **Constraints:** `.vision/CONSTRAINTS.md`
- **Architecture:** `.vision/ARCHITECTURE.md`
- **UX Styling:** `.vision/UX_STYLING.md`
