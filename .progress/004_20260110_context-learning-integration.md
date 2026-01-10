# Context Learning Integration

**Started**: 2026-01-10
**Completed**: 2026-01-10
**Status**: ✅ COMPLETE

## Overview

Enable agents to retrieve relevant past experiences via a `search_trajectories` tool, using a generic OTS library with flexible filters.

## Architecture Decision

```
┌─────────────────────────────────────────────────────────────┐
│                     DSF Agent (letta-code)                  │
│  Calls: search_trajectories(query, filters, include_failures)│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   search_trajectories Tool                   │
│  Location: letta-code/src/tools/impl/search_trajectories.ts │
│  - Wraps OTS ContextLearning                                │
│  - Formats output for agent consumption                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 OTS Library (Generic)                        │
│  Location: ots/src/ots/learning/context.py                  │
│  - search(query, filters, min_score, include_failures)      │
│  - get_anti_patterns(query, filters)                        │
│  - Domain-agnostic, filter-driven                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Storage Backend (Letta)                      │
│  Location: letta/letta/ots/backend.py                       │
│  - LettaStorageBackend implements StorageBackend protocol   │
│  - PostgreSQL + pgvector for semantic search                │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Trigger mechanism** | On-demand via tool | Agent decides when it needs context, not automatic injection |
| **Failure presentation** | Separate anti-pattern section | Clear distinction between "do this" and "avoid this" |
| **DSF-specific methods** | Remove them | OTS should be generic; DSF passes filters |
| **Integration location** | Tool in letta-code | Agent-callable, wraps OTS library |
| **Filter approach** | Flexible `Dict[str, Any]` | Supports arbitrary filter keys without code changes |

## Why On-Demand vs Automatic?

**Considered**: Automatic context injection before every LLM call
- Pro: Agent always has relevant context
- Con: Token bloat, not always needed, reduces agent autonomy

**Chosen**: On-demand via `search_trajectories` tool
- Agent decides when context is useful
- No wasted tokens when agent is confident
- Agent learns to recognize uncertainty and seek help
- Can request specific types of context (failures, specific tool, etc.)

## Why Generic Filters vs DSF Methods?

**Current problem**: Letta's `context_learning.py` has DSF-specific methods:
- `get_similar_world_decisions()`
- `get_similar_story_decisions()`
- `get_rule_application_examples()`

**Why this is wrong**:
1. OTS should be domain-agnostic library
2. DSF is one consumer, not special
3. Adding new domains requires OTS changes

**Solution**: Generic `search()` with flexible filters
```python
# Instead of:
await learner.get_similar_world_decisions(world_id)

# Use:
await learner.search(query, filters={"entity_type": "world", "entity_id": world_id})
```

## Implementation Phases

### Phase 1: Generic OTS Context Learning ✅ COMPLETE
**File**: `ots/src/ots/learning/context.py`

Changes:
- [x] Review current implementation (already has good foundation)
- [x] Add generic `search()` method with `filters: Dict[str, Any]`
- [x] Support filter keys: domain, entity_type, entity_id, action_type, tags
- [x] Update `get_context()` to use `search()` internally
- [x] Add `_extract_examples()` helper for filtering decisions
- [x] Add `_matches_entity_filter()` for entity-based filtering
- [x] Add `_format_combined_context()` for success + anti-pattern output
- [x] Update `ContextLearningResult` dataclass with `anti_patterns` field
- [x] Update `get_anti_patterns()` to accept filters parameter

### Phase 2: Refactor Letta Context Learning ✅ COMPLETE
**File**: `letta/letta/trajectories/ots/context_learning.py`

Changes:
- [x] Renamed class `DSFContextLearning` → `ContextLearning` (kept alias for backwards compat)
- [x] Added generic `search()` method with `filters: Dict[str, Any]` parameter
- [x] Added `_extract_examples()` helper for filtering decisions
- [x] Added `_matches_entity_filter()` for entity-based filtering
- [x] Added `_extract_context_info()` for generic context extraction
- [x] Added `_format_combined_context()` for success + anti-pattern output
- [x] Updated `RetrievedExample` dataclass with generic `context_info` field
- [x] Updated `ContextLearningResult` dataclass with `anti_patterns` field
- [x] Marked DSF-specific methods as deprecated with warnings
- [x] Added `search_trajectories()` convenience function
- [x] Marked `get_dsf_context()` and `get_anti_patterns()` as deprecated
- [x] Updated `__init__.py` exports

### Phase 3: Create search_trajectories Tool ✅ COMPLETE
**File**: `letta-code/src/tools/impl/search_trajectories.ts`

Changes:
- [x] Created `search_trajectories.ts` implementation
- [x] Created `search_trajectories.md` description
- [x] Created `search_trajectories.json` schema
- [x] Registered in `toolDefinitions.ts`
- [x] Added to `ANTHROPIC_DEFAULT_TOOLS` in `manager.ts`
- [x] Added to `TOOL_PERMISSIONS` with `requiresApproval: false`
- [x] Fixed TypeScript errors (method case, type definitions, null checks)

Tool interface:
```typescript
{
  name: "search_trajectories",
  parameters: {
    query: string,           // Natural language description
    filters?: object,        // domain, entity_type, etc.
    include_failures?: bool, // Include anti-patterns
    limit?: number           // Max examples (default 5)
  }
}
```

### Phase 4: Enable Trajectory Capture ✅ COMPLETE
- [x] Added `ENABLE_TRAJECTORY_CAPTURE=true` to `.env`
- [x] dev-compose.yaml already defaults to true

### Phase 5: Verify API Endpoint ✅ COMPLETE
- [x] Verified `POST /v1/trajectories/search` exists in `letta/letta/server/rest_api/routers/v1/trajectories.py`
- [x] Confirmed `TrajectorySearchRequest` schema accepts: query, min_score, max_score, domain_type, limit
- [x] Tool parameters match API schema

## Output Format (Tool Result)

When agent calls `search_trajectories`, formatted output:

```markdown
## Relevant Past Decisions

Consider these successful past approaches:

### Example 1 (similarity: 0.87, outcome: ✓ Success)
**Action**: world_manager.save
**Context**: Creating initial world rules for hard sci-fi setting
**Reasoning**: Saved checkpoint before adding FTL restrictions
**Result**: World saved successfully with 3 rules defined

## Anti-Patterns to Avoid (if include_failures=true)

### Example 1 (similarity: 0.92, outcome: ✗ Failed)
**Action**: world_manager.update
**Context**: Tried to add magic to hard sci-fi world
**Reasoning**: Added soft magic system without constraints
**Result**: Inconsistency detected - violated "no supernatural elements"
**Lesson**: Check existing rules before adding conflicting elements
```

## Files Modified

| File | Action | Status |
|------|--------|--------|
| `ots/src/ots/learning/context.py` | Add generic `search()` | ✅ |
| `letta/letta/trajectories/ots/context_learning.py` | Refactor DSF methods | ✅ |
| `letta/letta/trajectories/ots/__init__.py` | Update exports | ✅ |
| `letta-code/src/tools/impl/search_trajectories.ts` | NEW tool impl | ✅ |
| `letta-code/src/tools/descriptions/search_trajectories.md` | NEW description | ✅ |
| `letta-code/src/tools/schemas/search_trajectories.json` | NEW schema | ✅ |
| `letta-code/src/tools/toolDefinitions.ts` | Register tool | ✅ |
| `letta-code/src/tools/manager.ts` | Add to defaults | ✅ |
| `.env` | Enable capture | ✅ |
| `letta/.../routers/v1/trajectories.py` | Verified endpoint | ✅ |

## Findings

### Current context.py Analysis (Phase 1)

The existing implementation in `ots/src/ots/learning/context.py` is already well-designed:
- Has `get_context()` with individual filter parameters
- Has `get_anti_patterns()` for failure examples
- Has `get_similar_decisions()` by action type
- Good formatting for agent consumption

What's missing:
- A unified `search()` method accepting `filters: Dict`
- Filter support for `entity_type` and `entity_id`

Plan: Add `search()` as the primary method, update others to use it internally.

## Verification Steps

To verify the integration works:

1. **Restart Letta server** to pick up env change:
   ```bash
   cd letta && docker compose -f dev-compose.yaml down && docker compose -f dev-compose.yaml up -d --build
   ```

2. **Run agent sessions** to generate trajectories:
   - Create/update worlds and stories
   - Trajectories are captured automatically

3. **Verify storage**:
   ```bash
   curl http://localhost:8283/v1/trajectories/
   ```

4. **Test search API directly**:
   ```bash
   curl -X POST http://localhost:8283/v1/trajectories/search \
     -H "Content-Type: application/json" \
     -d '{"query": "creating world rules"}'
   ```

5. **Test via agent tool**:
   Agent calls `search_trajectories("how to create consistent magic rules")`

## Next Steps (Out of Scope)

- [ ] Add automatic context injection (before every LLM call) - optional enhancement
- [ ] Fine-tuning based on trajectories
- [ ] Cross-organization trajectory sharing
- [ ] Decision-level embedding search (not just trajectory-level)
- [ ] Analytics dashboard for trajectory visualization
