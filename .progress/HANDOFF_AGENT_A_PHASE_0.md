# Agent A Handoff: Phase 0 - Standards Migration

**Repository:** https://github.com/rita-aga/deep-sci-fi
**Branch:** main
**Duration:** 2 weeks
**Status File:** `.progress/015_phase0_standards_migration_status.md`

---

## Your Mission

Migrate Deep Sci-Fi's custom Agent Bus protocol to **json-render** (Vercel's declarative JSON framework) for type safety, security, and standards compliance - **WITHOUT breaking the existing immersive 3D UX**.

**Key Constraint:** Phase 3 (World Space components) is being built **IN PARALLEL** by Agent B. You'll integrate their components as they're built.

---

## Context: Why This Matters

### Current State
- **Custom Agent Bus:** WebSocket-based communication (letta-code ↔ Canvas UI)
- **Message format:** Untyped `{ component: string, props: Record<string, unknown> }`
- **Security risk:** No component catalog (agents can call anything)
- **No type safety:** Props are unvalidated

### Target State
- **json-render protocol:** Declarative JSON with component catalog
- **Type safety:** Zod schemas validate all props
- **Security:** Whitelist of trusted components only
- **Streaming:** Progressive rendering as AI responds
- **Keep:** WebSocket transport (it works great!)

### Research Background
Read `.progress/014_20260115_agent-driven-ui-research.md` for full context on why json-render is the right choice.

---

## Your Goals

### Week 1: Foundation
1. ✅ Install json-render packages
2. ✅ Create component catalog with **existing** Observatory components (WorldOrb, StarField, AgentPresence, etc.)
3. ✅ Migrate Agent Bus message format to json-render tree structure
4. ✅ Test with existing components

**End of Week 1 Checkpoint:**
- Get TypeScript prop interfaces from Agent B (Phase 3 components)
- They'll commit to `apps/web/components/canvas/world/types.ts`

### Week 2: Integration
1. ✅ Add Phase 3 components to catalog as Agent B builds them
2. ✅ Update `canvas_ui` tool to emit json-render format
3. ✅ Add streaming support (progressive rendering)
4. ✅ Test catalog with all components

### Week 3: Finalization
1. ✅ Ensure all Phase 3 components in catalog
2. ✅ Zod validation passing for all props
3. ✅ Documentation for future component additions

---

## Technical Implementation

### Step 1: Install json-render

```bash
cd apps/web
npm install @json-render/core @json-render/react zod
```

### Step 2: Create Component Catalog

**File:** `apps/web/lib/agent-ui/catalog.ts`

```typescript
import { createCatalog } from '@json-render/core';
import { z } from 'zod';

// Import existing components
import { WorldOrb } from '@/components/canvas/observatory/WorldOrb';
import { StarField } from '@/components/canvas/observatory/StarField';
import { AgentPresence } from '@/components/canvas/observatory/AgentPresence';
import { FloatingSuggestions } from '@/components/canvas/observatory/FloatingSuggestions';

export const catalog = createCatalog({
  components: {
    // Existing Observatory components
    WorldOrb: {
      component: WorldOrb,
      props: z.object({
        worldId: z.string(),
        world: z.object({
          id: z.string(),
          name: z.string(),
          coverImage: z.string().optional(),
          // ... rest of world schema
        }),
        position: z.array(z.number()).length(3),
        scale: z.number().optional().default(1),
        onClick: z.function().optional(),
        onHover: z.function().optional(),
      }),
      hasChildren: false,
    },

    StarField: {
      component: StarField,
      props: z.object({
        count: z.number().optional().default(2000),
        colors: z.array(z.string()).optional(),
      }),
      hasChildren: false,
    },

    AgentPresence: {
      component: AgentPresence,
      props: z.object({
        position: z.array(z.number()).length(3),
        thinking: z.boolean().optional().default(false),
      }),
      hasChildren: false,
    },

    FloatingSuggestions: {
      component: FloatingSuggestions,
      props: z.object({
        agentPosition: z.array(z.number()).length(3),
        suggestions: z.array(z.object({
          id: z.string(),
          text: z.string(),
          type: z.enum(['explore', 'create', 'discover', 'continue']),
          priority: z.enum(['high', 'medium', 'low']),
        })),
        onSuggestionClick: z.function().optional(),
        onDismiss: z.function().optional(),
      }),
      hasChildren: false,
    },

    // Phase 3 components - ADD THESE AS AGENT B BUILDS THEM
    // InteractiveWorldMap: { ... } - Add in Week 2
    // TechArtifact: { ... } - Add in Week 2
    // CharacterReveal: { ... } - Add in Week 2
    // StoryPortal: { ... } - Add in Week 2
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

    // Phase 3 actions - ADD THESE AS AGENT B BUILDS THEM
    // exploreLocation: { ... } - Add in Week 2
    // inspectArtifact: { ... } - Add in Week 2
  }
});

export type ComponentCatalog = typeof catalog;
```

### Step 3: Create json-render Renderer

**File:** `apps/web/lib/agent-ui/renderer.tsx`

```typescript
'use client';

import { Renderer as JsonRenderer } from '@json-render/react';
import { catalog } from './catalog';
import { useAgentBus } from '@/lib/agent-bus/client';

export function AgentUIRenderer({ tree }: { tree: any }) {
  const agentBus = useAgentBus();

  const handleAction = (action: string, params: any) => {
    // Send interaction back to agent via Agent Bus
    agentBus.send({
      type: 'interaction',
      action,
      params,
      timestamp: Date.now(),
    });
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

### Step 4: Update Agent Bus Message Format

**File:** `letta-code/src/agent-bus/types.ts`

```typescript
// BEFORE (custom)
export type CanvasUIMessage = {
  type: 'canvas_ui';
  component: string;
  props: Record<string, unknown>;
  mountPoint: 'overlay' | 'fullscreen' | 'inline';
};

// AFTER (json-render)
export type CanvasUIMessage = {
  type: 'canvas_ui';
  tree: {
    type: string;  // Component name from catalog
    props: Record<string, unknown>;  // Validated by Zod schema
    key: string;
    children?: Array<any>;
  };
  mountPoint: 'overlay' | 'fullscreen' | 'inline';
};
```

### Step 5: Update canvas_ui Tool

**File:** `letta-code/src/tools/impl/canvas_ui.ts`

```typescript
// BEFORE
export async function canvas_ui(args: {
  component: string;
  props: Record<string, unknown>;
  mountPoint: 'overlay' | 'fullscreen' | 'inline';
}) {
  agentBus.emit({
    type: 'canvas_ui',
    component: args.component,
    props: args.props,
    mountPoint: args.mountPoint,
  });
}

// AFTER
export async function canvas_ui(args: {
  tree: {
    type: string;
    props: Record<string, unknown>;
    key: string;
    children?: Array<any>;
  };
  mountPoint: 'overlay' | 'fullscreen' | 'inline';
}) {
  agentBus.emit({
    type: 'canvas_ui',
    tree: args.tree,
    mountPoint: args.mountPoint,
  });
}
```

### Step 6: Update Canvas UI to Use Renderer

**File:** `apps/web/components/canvas/DynamicRenderer.tsx` (or wherever Agent Bus messages are rendered)

```typescript
import { AgentUIRenderer } from '@/lib/agent-ui/renderer';

export function DynamicRenderer({ message }: { message: CanvasUIMessage }) {
  return <AgentUIRenderer tree={message.tree} />;
}
```

---

## Coordination with Agent B

### Week 1 (End): Get Prop Interfaces

Agent B will commit TypeScript interfaces for Phase 3 components:

**File:** `apps/web/components/canvas/world/types.ts`

```typescript
export interface WorldMapProps {
  worldId: string;
  locations: Location[];
  connections?: Connection[];
  selectedLocation?: string;
  onLocationClick?: (locationId: string) => void;
  onLocationHover?: (locationId: string) => void;
}

export interface TechArtifactProps {
  artifactId: string;
  name: string;
  description: string;
  model3dUrl?: string;
  onInspect?: () => void;
}

// ... more interfaces
```

### Week 2+: Add to Catalog

As Agent B commits components, add them to your catalog:

```typescript
// In catalog.ts
import { InteractiveWorldMap } from '@/components/canvas/world/InteractiveWorldMap';
import { TechArtifact } from '@/components/canvas/world/TechArtifact';

export const catalog = createCatalog({
  components: {
    // ... existing components

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

    TechArtifact: {
      component: TechArtifact,
      props: z.object({
        artifactId: z.string(),
        name: z.string(),
        description: z.string(),
        model3dUrl: z.string().optional(),
        onInspect: z.function().optional(),
      }),
      hasChildren: false,
    },

    // ... add more as Agent B builds them
  }
});
```

---

## Status Tracking

**Create:** `.progress/015_phase0_standards_migration_status.md`

**Update daily:**

```markdown
# Phase 0: Standards Migration - Status

**Agent:** A
**Week:** 1/3
**Last Updated:** 2026-01-XX

## Progress

### Week 1
- [x] Installed json-render packages
- [x] Created component catalog with existing components
- [x] Migrated Agent Bus message format
- [x] Tested with Observatory components
- [ ] Received prop interfaces from Agent B (end of week)

### Week 2
- [ ] Added InteractiveWorldMap to catalog
- [ ] Added TechArtifact to catalog
- [ ] Added CharacterReveal to catalog
- [ ] Added StoryPortal to catalog
- [ ] Updated canvas_ui tool

### Week 3
- [ ] Streaming support implemented
- [ ] All validation passing
- [ ] Documentation complete

## Blockers
- None

## Notes
- Existing Observatory components migrated successfully
- Awaiting Phase 3 prop interfaces from Agent B
```

---

## Testing

### Test 1: Existing Components Still Work

```typescript
// In a test or dev console
agentBus.emit({
  type: 'canvas_ui',
  tree: {
    type: 'WorldOrb',
    props: {
      worldId: 'test-world',
      world: { id: 'test', name: 'Test World' },
      position: [0, 0, 0],
      scale: 1.5,
    },
    key: 'test-orb-1',
  },
  mountPoint: 'fullscreen',
});

// Should render WorldOrb in Canvas UI
```

### Test 2: Type Validation Works

```typescript
// This should FAIL validation (missing required worldId)
agentBus.emit({
  type: 'canvas_ui',
  tree: {
    type: 'WorldOrb',
    props: {
      position: [0, 0, 0],
    },
    key: 'invalid-orb',
  },
  mountPoint: 'fullscreen',
});

// json-render should throw Zod validation error
```

### Test 3: Actions Work

```typescript
// In AgentUIRenderer, click on a world orb
// Should emit interaction message back to agent
{
  type: 'interaction',
  action: 'navigateToWorld',
  params: { worldId: 'abc123' },
  timestamp: 1234567890,
}
```

---

## Files You'll Touch

**New Files (Create):**
- `apps/web/lib/agent-ui/catalog.ts`
- `apps/web/lib/agent-ui/renderer.tsx`
- `.progress/015_phase0_standards_migration_status.md`

**Modified Files:**
- `letta-code/src/agent-bus/types.ts`
- `letta-code/src/tools/impl/canvas_ui.ts`
- `apps/web/components/canvas/DynamicRenderer.tsx` (or wherever messages render)
- `apps/web/package.json` (add json-render dependencies)

**Files Agent B Touches (NO CONFLICT):**
- `apps/web/components/canvas/world/` (new components)
- `apps/web/components/canvas/world/types.ts` (prop interfaces you'll use)

---

## Success Criteria

✅ **End of Week 3:**
- [ ] All existing Observatory components in catalog
- [ ] All Phase 3 components in catalog (from Agent B)
- [ ] Zod validation passing for all components
- [ ] Agent tools emit json-render tree format
- [ ] Streaming support working
- [ ] No breaking changes to existing UX
- [ ] Type safety throughout

---

## Resources

- **Research:** `.progress/014_20260115_agent-driven-ui-research.md`
- **Ultra Plan:** `.progress/013_20260110_immersive-ux-ultraplan.md`
- **json-render docs:** https://json-render.dev/
- **json-render GitHub:** https://github.com/vercel-labs/json-render
- **Zod docs:** https://zod.dev/

---

## Questions? Issues?

Update your status file (`.progress/015_phase0_standards_migration_status.md`) with:
- Blockers
- Questions for Agent B
- Decisions made
- Deviations from plan

**Good luck, Agent A!** 🚀
