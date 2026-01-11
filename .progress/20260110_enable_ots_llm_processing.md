# Enable OTS LLM Processing for Proper Entities and Decisions

**Goal**: Integrate OTS's LLM-based extraction into Letta's trajectory processing to get rich decisions (with rationale, alternatives, confidence) and entities.

**Status**: IN PROGRESS - Backend complete, UI update remaining

---

## Current State

### Letta's Trajectory Processing (gpt-4o-mini)
- `TrajectoryProcessor.generate_searchable_summary()` - NL summary
- `TrajectoryProcessor.score_trajectory()` - quality score 0-1
- `TrajectoryProcessor.extract_labels_and_metadata()` - tags, category, complexity
- `TrajectoryProcessor.generate_embedding()` - vector embedding

### OTS Extraction (Not Currently Used)
- `DecisionExtractor.extract_from_turn(mode="full")` - LLM-based extraction:
  - Decisions with: rationale, alternatives_considered, confidence, context_summary
  - Entities: services, files, users, concepts, resources
- `DSFEntityExtractor` - Programmatic extraction of DSF-specific entities (worlds, stories, rules)

### Gap
Letta uses its own gpt-4o-mini processing but **NOT** OTS's `DecisionExtractor` with LLM mode. This means:
- Decisions only have tool_name/arguments, no rationale/alternatives
- No LLM-extracted entities (concepts, services, etc.)

---

## Architecture

### OTS LLMClient Protocol
```python
class LLMClient(Protocol):
    async def generate(
        self,
        prompt: str,
        response_format: str = "text",
    ) -> str:
        ...
```

### Integration Points
1. **LLM Client Adapter**: Wrap OpenAI to implement `LLMClient`
2. **Processing Pipeline**: Call OTS extraction during `process_trajectory()`
3. **Data Storage**: Store decisions/entities in trajectory schema
4. **API Response**: Return decisions/entities in GET trajectory endpoint
5. **UI Display**: Render rich decision data in TrajectoriesView

---

## Implementation Plan

### Phase 1: Create LLM Client Adapter

**File**: `letta/letta/trajectories/ots/llm_client.py`

```python
from openai import AsyncOpenAI
from letta.settings import model_settings

class OpenAILLMClient:
    """Adapter implementing OTS LLMClient protocol using OpenAI."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = AsyncOpenAI(api_key=model_settings.openai_api_key)

    async def generate(self, prompt: str, response_format: str = "text") -> str:
        kwargs = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content
```

### Phase 2: Integrate OTS Extraction into Processing

**Modify**: `letta/letta/services/trajectory_processing.py`

```python
from letta.trajectories.ots.decision_extractor import DecisionExtractor
from letta.trajectories.ots.dsf_entity_extractor import DSFEntityExtractor
from letta.trajectories.ots.llm_client import OpenAILLMClient
from letta.trajectories.ots.adapter import OTSAdapter

async def extract_ots_decisions_and_entities(self, trajectory_data: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract OTS-style decisions and entities using LLM.

    Returns:
        (decisions, entities)
    """
    # Convert to OTS trajectory format
    ots_trajectory = OTSAdapter.from_letta_trajectory(trajectory_data)

    # Create LLM-enabled decision extractor
    llm_client = OpenAILLMClient(model="gpt-4o-mini")
    extractor = DecisionExtractor(llm_client=llm_client)

    # Extract decisions with LLM enrichment
    all_decisions = []
    all_entities = []

    for turn in ots_trajectory.turns:
        result = await extractor.extract_full(turn)  # Returns ExtractionResult
        all_decisions.extend([d.model_dump() for d in result.decisions])
        all_entities.extend([e.model_dump() for e in result.entities])

    # Also run DSF-specific entity extraction (programmatic)
    dsf_extractor = DSFEntityExtractor()
    dsf_entities = dsf_extractor.extract_all(ots_trajectory)
    all_entities.extend([e.model_dump() for e in dsf_entities])

    # Deduplicate entities by ID
    seen_ids = set()
    unique_entities = []
    for e in all_entities:
        if e["id"] not in seen_ids:
            unique_entities.append(e)
            seen_ids.add(e["id"])

    return all_decisions, unique_entities
```

### Phase 3: Update Process Trajectory to Include OTS

```python
async def process_trajectory(self, trajectory_data: Dict) -> TrajectoryProcessingResult:
    """Full processing pipeline with OTS extraction."""

    # Existing processing
    summary = await self.generate_searchable_summary(trajectory_data)
    score, reasoning = await self.score_trajectory(trajectory_data)
    tags, category, complexity, metadata = await self.extract_labels_and_metadata(trajectory_data)
    embedding = await self.generate_embedding(summary)

    # NEW: OTS extraction
    decisions, entities = await self.extract_ots_decisions_and_entities(trajectory_data)

    return TrajectoryProcessingResult(
        summary=summary,
        score=score,
        reasoning=reasoning,
        tags=tags,
        task_category=category,
        complexity_level=complexity,
        trajectory_metadata=metadata,
        embedding=embedding,
        # NEW fields
        ots_decisions=decisions,
        ots_entities=entities,
    )
```

### Phase 4: Update Schema to Store OTS Data

**File**: `letta/letta/schemas/trajectory.py`

Add to Trajectory schema:
```python
# OTS LLM-extracted data
ots_decisions: Optional[List[Dict[str, Any]]] = Field(
    None,
    description="OTS-style decisions with rationale/alternatives (LLM-extracted)"
)
ots_entities: Optional[List[Dict[str, Any]]] = Field(
    None,
    description="Entities extracted from trajectory (LLM + programmatic)"
)
```

### Phase 5: Update API to Return OTS Data

**File**: `letta/letta/server/rest_api/routers/v1/trajectories.py`

Modify `_extract_decisions_from_trajectory` to use stored OTS decisions when available:
```python
def _extract_decisions_from_trajectory(trajectory: Trajectory) -> List[DecisionSummary]:
    # If OTS decisions are stored, use them (richer data)
    if trajectory.ots_decisions:
        return [
            DecisionSummary(
                decision_id=d.get("decision_id"),
                turn_index=d.get("turn_index", 0),
                decision_type=d.get("decision_type", "tool_selection"),
                action=d.get("choice", {}).get("action", ""),
                arguments=d.get("choice", {}).get("arguments"),
                rationale=d.get("choice", {}).get("rationale"),  # NEW
                success=d.get("consequence", {}).get("success", True),
                error_type=d.get("consequence", {}).get("error_type"),
                result_summary=d.get("consequence", {}).get("result_summary"),
                alternatives_considered=d.get("alternatives", {}).get("considered"),  # NEW
                confidence=d.get("choice", {}).get("confidence"),  # NEW
            )
            for d in trajectory.ots_decisions
        ]

    # Fallback to programmatic extraction
    return _extract_decisions_programmatic(trajectory)
```

### Phase 6: Update UI to Display Rich Decisions

**File**: `letta-ui/src/components/TrajectoriesView.tsx`

Add to decision rendering:
- Rationale (why this action was chosen)
- Alternatives considered (what else was weighed)
- Confidence score
- Context summary (what the agent understood)

---

## Files to Modify

| File | Change |
|------|--------|
| `letta/letta/trajectories/ots/llm_client.py` | **NEW** - OpenAI LLM adapter |
| `letta/letta/services/trajectory_processing.py` | Add OTS extraction to pipeline |
| `letta/letta/schemas/trajectory.py` | Add `ots_decisions`, `ots_entities` fields |
| `letta/letta/orm/trajectory.py` | Add columns for OTS data |
| `letta/letta/server/rest_api/routers/v1/trajectories.py` | Use stored OTS decisions |
| `letta-ui/src/components/TrajectoriesView.tsx` | Display rich decision data |
| `letta-ui/src/types/letta.ts` | Add TypeScript types for OTS fields |

---

## Decision: Which Model for OTS Extraction?

**Selected: GPT-5 mini**

| Model | Input/1M | Output/1M | Context | Notes |
|-------|----------|-----------|---------|-------|
| gpt-4o-mini | $0.15 | $0.60 | 128k | Old default |
| **gpt-5-mini** | $0.25 | $2.00 | 400k | **SELECTED** - Better reasoning, larger context |
| gpt-5-nano | $0.05 | $0.40 | - | Cheapest but less capable |

**Why GPT-5 mini:**
- Better reasoning capabilities than 4o-mini (important for decision extraction)
- 400k context window (3x larger than 4o-mini)
- Still very affordable ($0.25/$2.00)
- Same OpenAI API, easy drop-in

---

## Migration

For existing trajectories without OTS data:
1. Add migration to add nullable `ots_decisions`, `ots_entities` columns
2. Background job to re-process existing trajectories (optional)
3. API returns programmatic extraction if OTS data not available

---

## Verification

1. Create a test trajectory with tool calls and reasoning
2. Verify decisions have:
   - rationale (not null)
   - alternatives_considered (populated when agent weighed options)
   - confidence (when stated)
3. Verify entities are extracted:
   - Services/tools used
   - Files/resources referenced
   - Concepts discussed
4. Verify UI displays rich data
