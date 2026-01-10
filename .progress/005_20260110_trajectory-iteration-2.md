# Trajectory Integration - Iteration 2

**Started**: 2026-01-10
**Status**: 🔄 IN PROGRESS

## Overview

Enhance trajectory system with decision-level embeddings, cross-org sharing, Langfuse observability, and cleanup of redundant code.

## Iteration 1 Complete (Background)

Iteration 1 established basic context learning infrastructure. However, a redundant `search_trajectories` tool was created in letta-code when one already exists as a built-in Letta server tool.

## Iteration 2 Requirements

1. **Remove redundant letta-code search_trajectories** - Use server-side built-in tool
2. **Decision-level embedding persistence** - Enable fine-grained semantic search
3. **Verify cross-org sharing** - Infrastructure exists, verify end-to-end
4. **Verify Letta UI wiring** - TrajectoriesView and AnalyticsView
5. **Deduplicate Langfuse exporter** - Letta imports from OTS
6. **Add Langfuse export API** - REST endpoint for export

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     DSF Agent (Letta Server)                │
│  Built-in tool: search_trajectories                         │
│  Location: letta/letta/functions/function_sets/base.py      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   TrajectoryManager                         │
│  Location: letta/letta/services/trajectory_manager.py       │
│  - Trajectory-level search (existing)                       │
│  - Decision-level search (NEW)                              │
│  - Cross-org anonymization                                  │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────────┐
│   trajectories table    │     │ trajectories_decisions (NEW)│
│   (pgvector embeddings) │     │ (decision-level embeddings) │
└─────────────────────────┘     └─────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Observability Export                         │
│  - LangfuseExporter (from OTS)                              │
│  - OTelTrajectoryExporter (Letta-specific)                  │
│  - API: POST /v1/trajectories/{id}/export/langfuse          │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Remove Redundant letta-code Tool ✅ COMPLETE

**Problem**: letta-code has a client-side wrapper that duplicates the server-side built-in tool.

| File | Action | Status |
|------|--------|--------|
| `letta-code/src/tools/impl/search_trajectories.ts` | DELETE | ✅ |
| `letta-code/src/tools/descriptions/search_trajectories.md` | DELETE | ✅ |
| `letta-code/src/tools/schemas/search_trajectories.json` | DELETE | ✅ |
| `letta-code/src/tools/toolDefinitions.ts` | Remove imports and entry | ✅ |
| `letta-code/src/tools/manager.ts` | Remove from defaults/permissions | ✅ |

**Verification**: `bun run typecheck` passed ✅

### Phase 2: Decision-Level Embedding Persistence ✅ FOUNDATION COMPLETE

**Problem**: Decision embeddings exist in-memory only. Cannot search across decisions efficiently.

**Solution**: Created `trajectories_decisions` table with pgvector indexing for decision-level semantic search.

| File | Action | Status |
|------|--------|--------|
| `letta/letta/orm/trajectory_decision.py` | NEW - ORM model | ✅ |
| `letta/letta/orm/__init__.py` | Add TrajectoryDecision export | ✅ |
| `letta/letta/orm/trajectory.py` | Add decisions relationship | ✅ |
| `letta/letta/orm/organization.py` | Add trajectory_decisions relationship | ✅ |
| `letta/letta/schemas/trajectory_decision.py` | NEW - Pydantic schemas | ✅ |
| `letta/alembic/versions/d9e8f7a6b5c4_*.py` | NEW - Migration | ✅ |

**Remaining** (can be done in follow-up):
- [ ] DecisionManager service (create/search)
- [ ] API endpoints for decision search
- [ ] Integration with trajectory processing

**Schema Created**:
```sql
CREATE TABLE trajectories_decisions (
  id VARCHAR PRIMARY KEY,
  trajectory_id VARCHAR REFERENCES trajectories(id) ON DELETE CASCADE,
  turn_index INTEGER NOT NULL,
  decision_index INTEGER NOT NULL,
  action VARCHAR(256) NOT NULL,
  decision_type VARCHAR(64),
  rationale TEXT,
  success BOOLEAN,
  result_summary TEXT,
  error_type VARCHAR(256),
  searchable_text TEXT NOT NULL,
  embedding VECTOR(4096),
  organization_id VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Phase 3: Verify Cross-Org Sharing ⏳ PENDING

**Status**: Infrastructure exists, needs E2E verification.

### Phase 4: Verify Letta UI Trajectory Visualization ⏳ PENDING

### Phase 5: Deduplicate Langfuse Exporter ✅ COMPLETE

**Problem**: Identical `LangfuseExporter` in both `letta/` and `ots/`.

**Solution**: Replaced `letta/letta/trajectories/ots/observability.py` (544 lines) with a thin re-export module (28 lines) that imports from OTS.

| File | Action | Status |
|------|--------|--------|
| `letta/letta/trajectories/ots/observability.py` | Replace with OTS import | ✅ |

OTS is already a dependency in Letta's `pyproject.toml`: `ots @ git+https://github.com/nerdsane/ots.git`

### Phase 6: Add Langfuse Export API ✅ COMPLETE

**Solution**: Added `POST /v1/trajectories/{id}/export/langfuse` endpoint that:
1. Retrieves trajectory by ID
2. Converts to OTS format using `OTSAdapter`
3. Exports to Langfuse using `LangfuseExporter` (from OTS)
4. Returns trace ID with link to Langfuse dashboard

| File | Action | Status |
|------|--------|--------|
| `letta/letta/server/rest_api/routers/v1/trajectories.py` | Add export endpoint | ✅ |

**Usage**:
```bash
curl -X POST http://localhost:8283/v1/trajectories/{id}/export/langfuse \
  -H "Content-Type: application/json" \
  -d '{"tags": ["test"]}'
```

**Requires**: `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` environment variables.

---

## Decisions & Trade-offs

| Decision | Choice | Trade-off |
|----------|--------|-----------|
| Decision storage | New table (not JSONB array) | More schema changes, but enables pgvector indexing |
| Langfuse code | Import from OTS | Adds OTS dependency, but single source of truth |
| OTS visualization | Not in scope | Letta UI shows trajectory-level, not decision-level details |
| Cross-org | Verify existing | Infrastructure exists, just needs E2E testing |

---

## What Works TODAY vs What Doesn't

### Works TODAY (Data Exists)

| Feature | Source Field | Status |
|---------|--------------|--------|
| Trajectory list with search | API + pgvector | ✅ Works |
| Execution status badges | `data.outcome.execution.status` | ✅ Works |
| Learning score (0-1) | `outcome_score` | ✅ Works |
| Semantic search | `embedding` + similarity | ✅ Works |
| Tags, category, complexity | LLM-extracted fields | ✅ Works |
| Turn-by-turn execution trace | `data.turns` | ✅ Works |
| Message content and tool calls | `data.turns[].messages` | ✅ Works |
| Token usage per turn | `data.turns[].input_tokens` | ✅ Works |
| Processing status | `processing_status` | ✅ Works |
| UMAP semantic map | `embedding` vectors | ✅ Works |
| Score distribution histogram | `score_distribution` agg | ✅ Works |
| Turn distribution chart | `turn_distribution` agg | ✅ Works |
| Tool usage bar chart | `tool_usage` agg | ✅ Works |
| Tags word cloud | `tags_frequency` agg | ✅ Works |
| Daily trends line chart | `daily_counts` agg | ✅ Works |

### Does NOT Work (No Data)

| Feature | Why Missing | Would Require |
|---------|-------------|---------------|
| Decision alternatives | Not tracked in Letta | OTS format + UI changes |
| Why decisions were rejected | Not tracked | OTS format |
| Decision-level confidence | Not tracked | OTS format |
| Decision-level evaluations | Not tracked | OTS format |
| Credit assignment | Not tracked | OTS format |
| Per-turn rewards | Only `outcome_score` overall | OTS format |
| Counterfactual analysis | Not designed for this | Major feature |

---

## Findings Log

(Updated during implementation)

---

## Verification Checklist

- [ ] letta-code typecheck passes after tool removal
- [ ] Decision embeddings persist to new table
- [ ] Decision-level search returns results via API
- [ ] Cross-org search returns anonymized results
- [ ] Letta UI trajectory list/search/detail works
- [ ] Langfuse export creates trace in Langfuse dashboard
- [ ] No duplicate code between letta and ots for Langfuse
