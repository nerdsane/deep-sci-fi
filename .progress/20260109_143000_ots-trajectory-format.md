# OTS (Open Trajectory Specification) Implementation

**Started**: 2026-01-09
**Status**: In Progress (Phase 5 remaining)

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

### Phase 4: DSF Integration ✅ COMPLETE
- [x] DSFEntityExtractor for world/story/rule/element entities (`letta/letta/trajectories/ots/dsf_entity_extractor.py`)
- [x] DSFEvaluationIntegrator placeholder for evaluation tool integration
- [x] DSFContextLearning for context learning retrieval (`letta/letta/trajectories/ots/context_learning.py`)
- [x] Convenience functions: `get_dsf_context()`, `get_anti_patterns()`

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
├── store.py                 # OTS storage layer
├── decision_embeddings.py   # Decision embedding utilities
├── dsf_entity_extractor.py  # DSF entity extraction (NEW)
└── context_learning.py      # Context learning retrieval (NEW)

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

## Phase 4 Implementation Details

### DSFEntityExtractor
- Extracts DSF-specific entities from trajectories:
  - Worlds (with development state, version)
  - Stories (with segments, contributions)
  - Rules (scope, certainty, tested status)
  - Elements (characters, locations, tech)
  - Constraints (physical, social, logical, narrative)
- Parses tool calls to world_manager and story_manager
- Extracts world contributions from story segments

### DSFEvaluationIntegrator
- Placeholder for integrating with Letta's evaluation tools
- Will evaluate trajectory consistency with world rules
- Will assess output quality and track information gain

### DSFContextLearning
- Main entry point: `get_context_for_action()`
- Retrieves similar past decisions based on:
  - Current situation description
  - Action type (world_manager, story_manager)
  - World/story context
  - Outcome score threshold
- Formats retrieved decisions for agent consumption
- Supports anti-pattern retrieval (failed decisions)

### Convenience Functions
- `get_dsf_context(situation, actor, ...)` - Get formatted context for agent
- `get_anti_patterns(situation, actor, ...)` - Get failure examples to avoid

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

## Next Steps

1. **Phase 5: Observability**
   - LangfuseExporter for trace visualization
   - OTel integration for spans
   - Dashboard integration for trajectory browsing

2. **Future Enhancements**
   - Deep integration with Letta evaluation tools
   - RL training data export
   - Counterfactual simulation
