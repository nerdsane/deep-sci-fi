# Canvas Architecture Decision: Monorepo vs Separate Project

## The Question

Should the Canvas UI live in `letta-code/src/canvas/` or be a separate project `dsf-agent/dsf-canvas-ui/`?

## Current State: Canvas in letta-code

```
letta-code/
├── src/
│   ├── index.ts          # CLI entry point
│   ├── cli/              # Terminal UI (Ink)
│   ├── tools/            # Agent tools
│   └── canvas/           # Web UI (React)
│       ├── app.tsx
│       ├── server.ts
│       └── styles.css
```

**Why this might make sense:**
1. **Shared Agent Context** - Both CLI and Canvas use same agent ID from `.letta/settings.local.json`
2. **Shared Tools** - Canvas server imports tool implementations directly (world_manager, story_manager, etc.)
3. **Shared Types** - TypeScript types for World, Story, etc. defined once
4. **Single Development Workflow** - One `bun run build`, one repo to clone
5. **Tight Coupling** - Canvas triggers agent operations via CLI agent

## Alternative: Separate dsf-canvas-ui

```
dsf-agent/
├── letta/                  # Letta server
├── letta-code/             # CLI only
└── dsf-canvas-ui/          # Separate canvas project
    ├── src/
    │   ├── app.tsx
    │   ├── server.ts
    │   └── components/
    ├── package.json
    └── README.md
```

**Why this might make sense:**
1. **Separation of Concerns** - CLI is terminal, Canvas is web - different domains
2. **Independent Versioning** - Canvas can release v2.0 while CLI stays v1.5
3. **Independent Deployment** - Deploy canvas to web, keep CLI local-only
4. **Optional Canvas** - Users can skip canvas entirely, just use CLI
5. **Cleaner Boundaries** - Each project has single responsibility

## Analysis

### Current Tight Coupling Points

**1. Shared Agent ID**
```typescript
// Both read from same settings file
const settings = await Bun.file(".letta/settings.local.json").json();
const agentId = settings.agentId;
```
**Impact:** If separate, need shared settings location or API to get agent ID.

**2. Direct Tool Imports**
```typescript
// Canvas server.ts currently does:
import { world_manager } from "../tools/impl/world_manager";
import { story_manager } from "../tools/impl/story_manager";

// Uses them directly in API endpoints
```
**Impact:** If separate, canvas would need to:
- Duplicate tool code, OR
- Call agent via Letta API, OR
- Import tools from npm package

**3. Shared Types**
```typescript
// Both use same type definitions
import type { World, Story, StorySegment } from "../types/dsf";
```
**Impact:** If separate, need shared types package or duplicate definitions.

**4. Shared File System**
```typescript
// Both read/write to .dsf/
const worlds = await readdir(".dsf/worlds");
const stories = await readdir(".dsf/stories");
```
**Impact:** Both need to be in same workspace or parent directory.

**5. Canvas Triggers CLI Agent**
```typescript
// Canvas sends messages to agent
const response = await fetch(`${LETTA_BASE_URL}/messages`, {
  body: JSON.stringify({
    agent_id: agentId,
    messages: [{ role: "user", text: "Create story in this world" }]
  })
});
```
**Impact:** This actually works fine if separate - goes through Letta API.

### Comparison Matrix

| Aspect | Monorepo (Current) | Separate Projects |
|--------|-------------------|-------------------|
| **Development** | ⭐⭐⭐ Simple - one clone, one build | ⚠️ Complex - coordinate two repos |
| **Type Sharing** | ⭐⭐⭐ Import directly | ⚠️ Need shared package or duplication |
| **Tool Reuse** | ⭐⭐⭐ Import directly | ⚠️ Need to call via API or package |
| **Versioning** | ⚠️ Canvas+CLI must version together | ⭐⭐⭐ Independent versions |
| **Deployment** | ⚠️ Bundle both even if only need CLI | ⭐⭐⭐ Deploy separately |
| **Concerns** | ⚠️ Mixed (CLI + Web) | ⭐⭐⭐ Separated |
| **Code Navigation** | ⭐⭐ All in one place | ⚠️ Jump between repos |
| **Testing** | ⭐⭐⭐ Test together | ⚠️ Integration tests harder |
| **Discoverability** | ⭐⭐⭐ Users get both | ⚠️ Users might miss canvas |

## Recommendations

### Short-term (Now - 6 months): **Keep in letta-code** ✅

**Reasoning:**
1. **Rapid Development** - You're still iterating on both CLI and Canvas together
2. **Tight Integration** - Canvas directly imports tools, types, utilities
3. **Shared Context** - Agent ID, settings, file system all shared naturally
4. **Fewer Moving Parts** - One repo to manage during active development
5. **User Convenience** - Users get full DSF experience with one install

**Structure to support future separation:**
```typescript
// Create clear boundaries NOW for easier split later

// 1. Shared types in dedicated directory
letta-code/src/shared/
├── types.ts        # World, Story, etc.
├── constants.ts    # Shared constants
└── utils.ts        # Shared utilities

// 2. Canvas imports only from shared/
// ❌ Don't do this:
import { World } from "../cli/components/types"

// ✅ Do this:
import { World } from "../shared/types"

// 3. Canvas uses Letta API for agent operations
// ❌ Don't do this:
import { world_manager } from "../tools/impl/world_manager"

// ✅ Do this:
const response = await fetch(`${LETTA_BASE_URL}/...`)
```

### Long-term (6+ months): **Consider Separation** 🤔

**When to separate:**

**Trigger 1: Different Release Cadences**
- Canvas needs weekly UI updates
- CLI is stable, releases monthly
- You're constantly rebundling CLI just for canvas changes

**Trigger 2: Different Deployment Needs**
- Want to deploy canvas to web (dsf-canvas.vercel.app)
- CLI stays local-only
- Canvas becomes multi-user, CLI stays single-user

**Trigger 3: Team Structure Changes**
- Different people working on CLI vs Canvas
- Want separate ownership/permissions
- Need independent CI/CD pipelines

**Trigger 4: Shared Across Projects**
- Canvas becomes useful for other agents (not just DSF)
- Want to offer canvas as standalone tool
- Other projects want to fork/extend canvas

**How to separate (when time comes):**

```bash
# 1. Extract to separate repo
dsf-agent/
├── letta-code/           # CLI
├── dsf-canvas-ui/        # Canvas (new)
└── dsf-shared/           # Shared types (new)
    └── package.json      # npm package for types

# 2. Publish shared types
cd dsf-shared
bun publish @deep-scifi/shared

# 3. Both depend on shared
letta-code/package.json:
{
  "dependencies": {
    "@deep-scifi/shared": "^1.0.0"
  }
}

dsf-canvas-ui/package.json:
{
  "dependencies": {
    "@deep-scifi/shared": "^1.0.0"
  }
}

# 4. Canvas communicates only via APIs
// No more direct tool imports
// All operations go through Letta API or Agent Bus
```

## Decision: Keep in letta-code (for now)

### ✅ Advantages (Current)
1. **Faster Development** - No coordination overhead
2. **Type Safety** - Shared types without npm publish cycle
3. **Tool Reuse** - Direct imports of tool implementations
4. **Easier Testing** - Test CLI and Canvas integration together
5. **User Experience** - One install, full experience
6. **Simpler Setup** - One repo to clone, one build command

### ⚠️ To Prevent Future Pain

**1. Use Clear Module Boundaries**
```typescript
// src/shared/ - Types, constants, utils used by BOTH
// src/cli/ - CLI-specific code
// src/canvas/ - Canvas-specific code
// src/tools/ - Agent tools (used by both via API)
// src/bus/ - Agent Bus (used by both)
```

**2. Canvas Communicates via APIs (not direct imports)**
```typescript
// ❌ Current (direct imports):
import { world_manager } from "../tools/impl/world_manager";
world_manager.save(...);

// ✅ Future-proof (via API):
await fetch("/api/world/save", {
  method: "POST",
  body: JSON.stringify({ world })
});
// Server-side still calls world_manager
```

**3. Document Dependencies**
```markdown
# Canvas Dependencies on CLI
- Types: World, Story, StorySegment (from shared/types.ts)
- Settings: Agent ID (from .letta/settings.local.json)
- File System: .dsf/ directory structure
- Agent Operations: Via Letta API

If we ever separate:
- Types → Move to @deep-scifi/shared package
- Settings → Environment variable or API endpoint
- File System → Keep shared (both in dsf-agent/)
- Agent Ops → Already via API ✅
```

## Comparison to Other Projects

**Monorepo (Like You):**
- **Vercel** - CLI + Web dashboard in same repo
- **Next.js** - CLI tools + framework in same repo
- Makes sense when tightly integrated

**Separate Repos:**
- **VS Code** - Editor separate from extensions
- **Gatsby** - Core separate from plugins
- Makes sense when loosely coupled

**DSF is more like Vercel** - Canvas is the dashboard for your CLI agent.

## Summary

**Current structure makes sense because:**
1. Canvas and CLI are tightly coupled by design (shared agent, shared data)
2. You're in active development, moving fast
3. Users expect unified experience (not "install CLI, also install Canvas separately")
4. Development is simpler (one build, one deploy, one version)

**Prepare for potential separation by:**
1. Creating clear module boundaries (`src/shared/`, `src/cli/`, `src/canvas/`)
2. Having canvas communicate via APIs (not direct imports)
3. Documenting dependencies clearly
4. Keeping coupling points visible and minimal

**Revisit this decision when:**
- Canvas and CLI need different release schedules
- You want to deploy canvas to web (multi-user)
- Team splits into CLI and Canvas specialists
- Another project wants to use canvas independently

**For now: Keep it simple, keep it in letta-code!** ✅
