# OTS (Open Trajectory Specification) Implementation

**Started**: 2026-01-09
**Status**: In Progress

## Overview

Implementing an open format for agent decision traces (trajectories) that enables:
1. Display - Render decision history in UIs
2. Context Learning - Retrieve similar examples at inference time
3. Simulation - Predict counterfactuals before acting
4. RL Training - Fine-tune on curated trajectories

## Plan Reference

Full plan at: `/Users/seshendranalla/.claude/plans/fancy-swimming-creek.md`

## Phases

### Phase 1: Format Specification ✅ COMPLETE
- [x] JSON Schema for base spec (`letta/letta/trajectories/ots/schema.json`)
- [x] JSON Schema for annotations (`letta/letta/trajectories/ots/annotation_schema.json`)
- [x] Pydantic models (`letta/letta/trajectories/ots/models.py`)

### Phase 2: Core Implementation ✅ COMPLETE
- [x] OTSAdapter - Convert Letta trajectory → OTS (`letta/letta/trajectories/ots/adapter.py`)
- [x] DecisionExtractor - Extract decisions from turns (`letta/letta/trajectories/ots/decision_extractor.py`)
- [x] Package init (`letta/letta/trajectories/ots/__init__.py`)

### Phase 3: Storage Layer ✅ COMPLETE
- [x] AnnotationManager service for linked annotations (`letta/letta/services/annotation_manager.py`)
- [x] Annotation Pydantic schemas for API (`letta/letta/schemas/trajectory_annotation.py`)
- [x] OTSStore for storing/retrieving OTS trajectories (`letta/letta/trajectories/ots/store.py`)
- [x] Decision-level embedding generation (`letta/letta/trajectories/ots/decision_embeddings.py`)
- [x] Added ANNOTATION enum to PrimitiveType (`letta/letta/schemas/enums.py`)

### Phase 4: DSF Integration 🔲 PENDING
- [ ] DSFEntityExtractor - Extract DSF-specific entities
- [ ] Integration with existing evaluation tools
- [ ] Context learning retrieval

### Phase 5: Observability 🔲 PENDING
- [ ] LangfuseExporter - Export to Langfuse
- [ ] OTel integration

## Files Created

```
letta/letta/trajectories/ots/
├── __init__.py              # Package exports
├── schema.json              # JSON Schema for OTS format
├── annotation_schema.json   # JSON Schema for annotations
├── models.py                # Pydantic models
├── adapter.py               # Letta → OTS conversion
├── decision_extractor.py    # Decision extraction
├── store.py                 # OTS storage layer (NEW)
└── decision_embeddings.py   # Decision embedding utilities (NEW)

letta/letta/services/
├── annotation_manager.py    # Annotation CRUD service (NEW)

letta/letta/schemas/
├── trajectory_annotation.py # Annotation Pydantic schemas (NEW)
├── enums.py                 # Added ANNOTATION enum
```

## Key Decisions

1. **Format is JSON** - Language-agnostic, JSON Schema for spec
2. **Decisions are per-turn** - 1:N relationship (multiple decisions per turn)
3. **Tool calls extracted programmatically** - No LLM needed
4. **Reasoning extracted with LLM** - Required for alternatives/rationale
5. **Annotations are linked entities** - Separate from trajectories
6. **Built inside Letta** - Tight integration with existing trajectory system
7. **Leveraged existing ORM** - TrajectoryAnnotation ORM already existed, created service layer
8. **Decision embeddings are optional** - Can embed decisions for fine-grained search

## Phase 3 Implementation Details

### AnnotationManager
- Full CRUD for trajectory annotations
- Supports trajectory-level, turn-level, and decision-level granularity
- Batch creation for efficiency
- Aggregation queries for statistics
- Search/filter by evaluator, score, label

### OTSStore
- Stores OTS trajectories using existing TrajectoryManager
- Converts between OTS format and Letta storage format
- Stores decision evaluations as linked annotations
- Enriches retrieved trajectories with annotations
- Semantic search for similar decisions

### DecisionEmbedder
- Generates embeddings for individual decisions
- Text representation includes state, choice, consequence
- Batch embedding support
- Cosine similarity search for decision matching

## Next Steps

1. **Phase 4: DSF Integration**
   - DSFEntityExtractor for world/story/rule entities
   - Hook into existing DSF evaluation tools (check_logical_consistency, etc.)
   - Context learning: retrieve relevant decisions before agent actions

2. **Phase 5: Observability**
   - LangfuseExporter for trace visualization
   - OTel integration for spans
