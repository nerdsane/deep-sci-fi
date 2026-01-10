# OTS (Open Trajectory Specification) Implementation

**Started**: 2026-01-09
**Status**: ✅ COMPLETE

## Overview

Implemented an open format for agent decision traces (trajectories) that enables:
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

### Phase 4: DSF Integration ✅ COMPLETE
- [x] DSFEntityExtractor for world/story/rule/element entities (`letta/letta/trajectories/ots/dsf_entity_extractor.py`)
- [x] DSFEvaluationIntegrator placeholder for evaluation tool integration
- [x] DSFContextLearning for context learning retrieval (`letta/letta/trajectories/ots/context_learning.py`)
- [x] Convenience functions: `get_dsf_context()`, `get_anti_patterns()`

### Phase 5: Observability ✅ COMPLETE
- [x] LangfuseExporter for Langfuse trace visualization (`letta/letta/trajectories/ots/observability.py`)
- [x] OTelTrajectoryExporter for OTel span export
- [x] `link_trajectory_to_current_span()` for span context continuity
- [x] Convenience functions: `export_to_langfuse()`, `export_to_otel()`

## Files Created

```
letta/letta/trajectories/ots/
├── __init__.py              # Package exports (all phases)
├── schema.json              # JSON Schema for OTS format
├── annotation_schema.json   # JSON Schema for annotations
├── models.py                # Pydantic models
├── adapter.py               # Letta → OTS conversion
├── decision_extractor.py    # Decision extraction
├── store.py                 # OTS storage layer
├── decision_embeddings.py   # Decision embedding utilities
├── dsf_entity_extractor.py  # DSF entity extraction
├── context_learning.py      # Context learning retrieval
└── observability.py         # Langfuse + OTel exporters

letta/letta/services/
├── annotation_manager.py    # Annotation CRUD service

letta/letta/schemas/
├── trajectory_annotation.py # Annotation Pydantic schemas
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
9. **Context learning is retrieval-based** - Find similar past decisions at inference time
10. **OTel integration uses existing infra** - Builds on Letta's existing OTel setup

## Usage Examples

### Adding Context Learning to DSF Agent

```python
from letta.trajectories.ots import get_dsf_context

# Before agent takes an action
context = await get_dsf_context(
    situation="Creating a story in the Nexus world about time travel",
    actor=user,
    world_checkpoint="nexus-v3",
    max_examples=3,
)

# Include in agent system prompt
system_prompt = f"""
{base_prompt}

## Relevant Past Experience
{context}
"""
```

### Extracting DSF Entities

```python
from letta.trajectories.ots import extract_dsf_entities, OTSAdapter

adapter = OTSAdapter()
ots_trajectory = adapter.from_letta_trajectory(letta_trajectory)
entities = extract_dsf_entities(ots_trajectory)

worlds = [e for e in entities if e.type == "world"]
stories = [e for e in entities if e.type == "story"]
rules = [e for e in entities if e.type == "rule"]
```

### Exporting to Langfuse

```python
from letta.trajectories.ots import export_to_langfuse, OTSAdapter

adapter = OTSAdapter()
ots_trajectory = adapter.from_letta_trajectory(letta_trajectory)

# Export to Langfuse for visualization
trace_id = await export_to_langfuse(
    ots_trajectory,
    public_key="pk-...",
    secret_key="sk-...",
)
print(f"View trace at: https://cloud.langfuse.com/trace/{trace_id}")
```

### Exporting to OTel

```python
from letta.trajectories.ots import export_to_otel, OTSAdapter

adapter = OTSAdapter()
ots_trajectory = adapter.from_letta_trajectory(letta_trajectory)

# Export as OTel spans (goes to configured collector)
trace_id = export_to_otel(ots_trajectory)
```

### Linking Trajectory to Current Span

```python
from letta.trajectories.ots import link_trajectory_to_current_span

# Within a traced operation
with tracer.start_as_current_span("agent_run"):
    # ... agent executes ...

    # Link the captured trajectory
    link_trajectory_to_current_span(ots_trajectory)
```

## Summary

The OTS implementation provides a complete solution for agent trajectory management:

| Capability | Module | Key Functions |
|------------|--------|---------------|
| Format | models.py | `OTSTrajectory`, `OTSDecision`, `OTSAnnotation` |
| Conversion | adapter.py | `OTSAdapter.from_letta_trajectory()` |
| Storage | store.py | `OTSStore`, `store_ots_trajectory()` |
| Annotations | annotation_manager.py | `AnnotationManager` |
| Embeddings | decision_embeddings.py | `DecisionEmbedder`, `find_similar_decisions()` |
| DSF Entities | dsf_entity_extractor.py | `DSFEntityExtractor`, `extract_dsf_entities()` |
| Context Learning | context_learning.py | `get_dsf_context()`, `get_anti_patterns()` |
| Langfuse | observability.py | `LangfuseExporter`, `export_to_langfuse()` |
| OTel | observability.py | `OTelTrajectoryExporter`, `export_to_otel()` |

## Future Enhancements

1. **Deep Letta Evaluation Integration** - Connect DSFEvaluationIntegrator to actual Letta evaluation tools
2. **RL Training Data Export** - Export trajectories in format suitable for RLHF/DPO
3. **Counterfactual Simulation** - Use trajectories to predict alternative outcomes
4. **UI Dashboard** - Build Letta-UI integration for trajectory browsing
5. **Automatic Context Injection** - Hook into agent loop to automatically add context learning
