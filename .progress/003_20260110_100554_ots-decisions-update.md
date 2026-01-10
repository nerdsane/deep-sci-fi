# OTS Decisions Update - Iteration 2

**Started**: 2026-01-10
**Status**: ✅ COMPLETE

## Overview

This iteration addresses feedback on the OTS standalone library decisions, clarifying key architectural choices based on the original position paper.

## Context

User provided the original position paper on trajectories and feedback on the previous iteration's decisions. Key questions:
1. **D1/D6**: Should OTS provide storage? How does vector search work?
2. **D3**: What are "entities"? How do they relate to decisions?
3. **D8**: Is observability for import or export?
4. **D10**: Should we add JSON Schema?

## Decisions Made

### D1/D6: Storage Architecture

**Decision**: LanceDB as default (not SQLite)

**Rationale**:
- Context learning (core OTS value) requires semantic search
- SQLite stores embeddings as BLOBs but requires O(n) in-memory search
- LanceDB is embedded like SQLite (local files, no server, no API key) but with native vector search
- Used by LlamaIndex, LangChain

**Clarification**: Spec vs Library
- **OTS Spec** = JSON Schema (the format standard)
- **OTS Library** = Python package with convenience implementations
- **Storage** = Each organization hosts their own (LanceDB file, PostgreSQL, etc.)

Analogy: OpenTelemetry defines trace format but doesn't host traces. Each org sends to their backend.

### D3: Entity Model

**Decision**: Two entity locations per position paper

**Position Paper Model**:
- `context.entities` = INPUT (what agent knew at start, populated by framework adapter)
- `context_snapshot.entities` = EVOLVING (per-message, updated as agent discovers/references things)
- `turns[].decisions` = ACTIONS (what agent chose to do + reasoning)

**Extraction Modes**:
| Mode | Decisions | Entities | Cost |
|------|-----------|----------|------|
| `fast` | Tool calls only | Tool call args/results only | Free |
| `full` | Tool calls + reasoning | Tool calls + conversation + reasoning | LLM cost |

In `full` mode, LLM extracts BOTH decisions AND entities from reasoning/conversation.

### D8: Observability Direction

**Decision**: Export-only (no import from OTel/Langfuse)

**Rationale**:
- OTel traces capture WHAT happened (tool calls) but not WHY (reasoning)
- Importing from OTel would produce degraded trajectories missing key OTS value
- Capture-at-source is required for full decision extraction
- Export enables display/visualization in existing observability UIs

### D10: JSON Schema

**Decision**: Add now (not defer)

**Rationale**:
- JSON Schema enables cross-language implementations (TypeScript, Go, Rust)
- Auto-generate from Pydantic models using `pydantic.json_schema()`
- Part of OTS being an open standard

## Implementation Plan

### Phase 1: Update Decision Documentation ✅ COMPLETE
- [x] Update D1/D6: Change default from SQLite to LanceDB
- [x] Update D3: Document two entity locations
- [x] Update D8: Explicit "export-only" language
- [x] Update D10: Remove "defer", add JSON Schema to scope

### Phase 2: Storage Backend Refactor ✅ COMPLETE
- [x] Add `LanceDBBackend` as default (requires `pip install ots[lancedb]`)
- [x] Keep `SQLiteBackend` for simple storage (no context learning)
- [x] Add `PostgresBackend` for production (requires `pip install ots[postgres]`)
- [x] Update `TrajectoryStore` to prefer LanceDB when embedding provider given

### Phase 3: JSON Schema Generation ✅ COMPLETE
- [x] Add `scripts/generate_schemas.py` using `pydantic.json_schema()`
- [x] Create `ots/schemas/` directory with generated schemas
- [x] Includes: trajectory, decision, annotation, and combined ots.schema.json

### Phase 4: Entity/Extraction Model Update ✅ COMPLETE
- [x] Update `DecisionExtractor` to also extract entities in `full` mode
- [x] Added `ExtractionResult` dataclass with decisions and entities
- [x] Added `extract_full()` method with combined LLM extraction
- [x] Updated docstrings to clarify entity model

### Phase 5: Observability Export Update ✅ COMPLETE
- [x] Update module docstrings to clarify export-only
- [x] Updated `observability/__init__.py` with comprehensive explanation
- [x] Updated `langfuse.py` with export-only guidance
- [x] Updated `otel.py` with export-only guidance

## Files Modified

### Decision Documentation
- `.progress/20260110_ots-standalone-library.md` - Updated decisions D1, D3, D6, D8, D10

### Storage Backends
- `ots/src/ots/store/lancedb.py` (new) - LanceDB embedded vector DB backend
- `ots/src/ots/store/postgres.py` (new) - PostgreSQL/pgvector backend
- `ots/src/ots/store/base.py` (update) - TrajectoryStore prefers LanceDB when embedding provider given
- `ots/src/ots/store/__init__.py` (update) - Export new backends

### JSON Schema Generation
- `ots/scripts/generate_schemas.py` (new) - Auto-generates schemas from Pydantic models
- `ots/schemas/trajectory.schema.json` (new) - OTSTrajectory schema
- `ots/schemas/decision.schema.json` (new) - OTSDecision schema
- `ots/schemas/annotation.schema.json` (new) - OTSAnnotation schema
- `ots/schemas/ots.schema.json` (new) - Combined schema with all definitions

### Entity Extraction
- `ots/src/ots/extraction/decisions.py` (update) - Added `extract_full()` method, `ExtractionResult` dataclass, combined extraction prompts

### Observability Export-Only
- `ots/src/ots/observability/__init__.py` (update) - Export-only clarification
- `ots/src/ots/observability/langfuse.py` (update) - Export-only guidance
- `ots/src/ots/observability/otel.py` (update) - Export-only guidance

### Dependencies
- `ots/pyproject.toml` (update) - Added lancedb and postgres optional dependencies

## Key Insights

1. **Spec vs Library**: OTS is a format (spec) AND a convenience library. Don't conflate them.

2. **Entities vs Decisions**:
   - Entities = things referenced/operated on (evolving context)
   - Decisions = actions taken + reasoning (what agent chose)

3. **Vector Search is Required**: Context learning needs semantic search. SQLite alone can't deliver OTS value.

4. **Capture-at-Source**: OTel traces lose reasoning. OTS must capture at framework level, not import from observability.

## Verification

1. Updated decisions in `.progress/20260110_ots-standalone-library.md`
2. Plan aligns with position paper
3. User approved plan before implementation
