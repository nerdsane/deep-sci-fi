# Phase 0: Standards Migration - Status

**Agent:** A
**Week:** 1/3
**Started:** 2026-01-15
**Last Updated:** 2026-01-15

---

## Mission

Migrate Deep Sci-Fi's custom Agent Bus protocol to **json-render** for type safety, security, and standards compliance - WITHOUT breaking the existing immersive 3D UX.

**Key Constraint:** Phase 3 (World Space components) is being built IN PARALLEL by Agent B. Will integrate their components as they're built.

---

## Progress

### Week 1: Foundation (Current)
- [x] Installed json-render packages (`@json-render/core`, `@json-render/react`, `zod`)
- [x] Created component catalog with Zod schemas for all existing Canvas UI components
- [x] Created component registry (json-render requires this instead of direct catalog usage)
- [x] Created json-render renderer component with JSONUIProvider
- [x] Added helper to convert simple tree format to UITree (flat structure)
- [ ] Resolved all type errors
- [ ] Tested with existing components
- [ ] **CRITICAL:** Received prop interfaces from Agent B (`apps/web/components/canvas/world/types.ts`)

### Week 2: Integration
- [ ] Added InteractiveWorldMap to catalog (from Agent B)
- [ ] Added TechArtifact to catalog (from Agent B)
- [ ] Added CharacterReveal to catalog (from Agent B)
- [ ] Added StoryPortal to catalog (from Agent B)
- [ ] Updated `canvas_ui` tool in letta-code to emit json-render format
- [ ] Added streaming support (progressive rendering)

### Week 3: Finalization
- [ ] All Phase 3 components in catalog
- [ ] Zod validation passing for all components
- [ ] Documentation for future component additions
- [ ] Run `/no-cap` verification
- [ ] Commit and push changes

---

## Current Status

**Working on:** Adapting to actual json-render API (differs from handoff document)
**Next:** Create proper ComponentRegistry and update renderer

## Issues Discovered

### json-render API Mismatch
The handoff document showed a simplified json-render API that doesn't match the actual library:

**Expected (from handoff):**
```typescript
<Renderer catalog={catalog} tree={simpleTree} />
```

**Actual json-render API:**
```typescript
<Renderer
  registry={componentRegistry}  // Not catalog!
  tree={{ root: "key", elements: {...} }}  // Flat structure!
/>
```

**Impact:** Need to adapt implementation but core goals remain (type safety, security, catalog)

**Solution:** Create ComponentRegistry from catalog and adapt message format to UITree structure

---

## Coordination with Agent B

### What Agent B is Building (Phase 3)
- **InteractiveWorldMap** - Locations as visual points on illustrated map
- **TechArtifact** - 3D rotatable objects
- **CharacterReveal** - Silhouettes → dramatic reveals
- **StoryPortal** - Visual gateways to narratives

### Critical Handoff Point
**End of Week 1:** Agent B will commit TypeScript prop interfaces to:
```
apps/web/components/canvas/world/types.ts
```

These interfaces will define the props for all Phase 3 components, which I'll use to create Zod schemas for the catalog.

### Status Check
- Agent B started work: ✅
- `apps/web/components/canvas/world/` directory exists: ✅
- `types.ts` file created: ❌ (expected end of Week 1)

---

## Technical Notes

### Current Architecture
- **Agent Bus Protocol:** WebSocket-based (letta-code ↔ Canvas UI)
- **Message Format:** `CanvasUIMessage` with `action`, `target`, `componentId`, `spec`
- **Component Specs:** Custom TypeScript types (no runtime validation)
- **Components:** 17 existing UI components (Dialog, Button, Text, Stack, Grid, etc.)

### Target Architecture
- **Keep:** WebSocket transport (works great!)
- **Change:** Message payload to json-render tree structure
- **Add:** Component catalog with Zod schemas for validation
- **Add:** Runtime type safety and security (whitelist)

### Files to Create
- `apps/web/lib/agent-ui/catalog.ts` - Component catalog
- `apps/web/lib/agent-ui/renderer.tsx` - json-render renderer

### Files to Modify
- `letta-code/src/agent-bus/types.ts` - Update CanvasUIMessage
- `letta-code/src/tools/impl/canvas_ui.ts` - Emit json-render format
- `apps/web/components/canvas/DynamicRenderer.tsx` - Use json-render renderer
- `apps/web/package.json` - Add dependencies

---

## Blockers

None currently.

---

## Questions

None currently.

---

## Decisions Made

1. **Week 1 Focus:** Get foundation working with existing components first, then integrate Agent B's components in Week 2
2. **Coordination Strategy:** Monitor `apps/web/components/canvas/world/types.ts` for Agent B's commit at end of Week 1

---

## Next Steps

1. Install json-render and Zod packages
2. Create component catalog with existing components
3. Test catalog works before proceeding
