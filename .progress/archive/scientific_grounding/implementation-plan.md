# Scientific Grounding & Story Coherence Tools - Implementation Plan

## Overview

Implement a comprehensive suite of tools to make the Deep Sci-Fi agent more scientifically rigorous and narratively coherent, following principles inspired by DeepSeek's extended reasoning approach. The agent will be able to:

1. **Trace causality** from present day to imagined futures
2. **Assess scientific plausibility** with nuanced reasoning (not brittle rules)
3. **Validate implications** across domains (physics → economics → social)
4. **Ensure story coherence** across multiple perspectives
5. **Self-question** to find contradictions and gaps
6. **Cross-validate** consistency between world layers

**Philosophy**: Tools not workflows - the agent chooses when/if to use these tools based on its judgment. As models improve, tool usage will improve organically.

---

## Tool Architecture

### Python Tools (Letta Server)
Located in: `letta/functions/function_sets/scientific_grounding.py`

5 LLM-based evaluation tools using the existing `LettaEvaluationToolExecutor` pattern:

1. `assess_scientific_grounding` - Plausibility + justification quality assessment
2. `trace_temporal_causality` - Causal chain from today → future
3. `validate_implications` - Required consequences of premises
4. `cross_domain_consistency` - Multi-layer implication validation
5. `adversarial_probe` - Self-questioning for contradictions

### TypeScript Tools (letta-code)
Located in: `letta-code/src/tools/impl/story_manager.ts` (extend existing tool)

2 new operations for story_manager:

6. `add_event` - Build canonical event graph for story
7. `validate_coherence` - Check multi-perspective narrative consistency

---

## Implementation Details

### TIER 1: Core Scientific Grounding Tools (Python/Letta)

#### Tool 1: `assess_scientific_grounding`

**Purpose**: Evaluate scientific plausibility and justification quality of world elements (replaces brittle symbolic physics checker).

**Signature**:
```python
def assess_scientific_grounding(
    agent_state: "AgentState",
    element: str,           # Technology, rule, or premise to assess
    world_context: str = "", # Optional: full world JSON for context
) -> str:
```

**Returns** (JSON):
```json
{
  "plausibility_score": 0.7,
  "scientific_basis": "Builds on current quantum entanglement research (2024 papers on long-distance entanglement stability)",
  "speculative_leaps": [
    "Assumes information can be transmitted (violates no-communication theorem)",
    "Requires exotic matter with negative energy density"
  ],
  "justification_quality": "acknowledged_speculation",
  "recommendations": [
    "Consider adding explanation of how no-communication theorem is circumvented",
    "Reference theoretical framework (Alcubierre metric, wormhole theory)"
  ],
  "classification": "hard_speculation"
}
```

**Implementation**:
- Use `_call_llm_for_evaluation` pattern from existing evaluation tools
- System prompt: "You are a scientific advisor for sci-fi worldbuilding. Assess plausibility, identify scientific basis, and evaluate justification quality."
- Return structured JSON with scores, basis, and recommendations
- No hard blocking - agent decides how to respond to assessment

---

#### Tool 2: `trace_temporal_causality`

**Purpose**: Generate causal chain from present day (2026) to future technology/event, identifying prerequisites and milestones.

**Signature**:
```python
def trace_temporal_causality(
    agent_state: "AgentState",
    target_element: str,     # "FTL travel", "Mars colony", etc.
    target_year: int,        # Target year for this element
    world_context: str = "", # Optional: existing world for consistency
) -> str:
```

**Returns** (JSON):
```json
{
  "causal_chain": [
    {
      "milestone": "Sustained fusion reaction (net positive energy)",
      "year_estimate": 2035,
      "prerequisites": ["ITER completion", "Advanced plasma confinement"],
      "scientific_basis": "Current ITER project timeline, tokamak research",
      "confidence": "high"
    },
    {
      "milestone": "Commercial fusion power plants",
      "year_estimate": 2055,
      "prerequisites": ["Sustained fusion reaction", "Materials science for neutron bombardment"],
      "scientific_basis": "Engineering timeline post-proof-of-concept",
      "confidence": "medium"
    },
    {
      "milestone": "Abundant cheap energy enables space infrastructure",
      "year_estimate": 2070,
      "prerequisites": ["Commercial fusion power plants"],
      "scientific_basis": "Energy economics, space launch cost models",
      "confidence": "medium"
    }
  ],
  "plausibility_assessment": {
    "overall_plausibility": 0.75,
    "research_gaps": ["Plasma stability", "Neutron-resistant materials"],
    "speculative_leaps": ["Assumes no major setbacks in fusion research"],
    "critical_path": ["Fusion breakthrough is bottleneck"]
  }
}
```

**Implementation**:
- LLM generates causal chain working backward from target year
- Each node has prerequisites forming a DAG (directed acyclic graph)
- Grounds early nodes in current research (use agent's knowledge + web search if needed)
- Later nodes become more speculative but maintain causal dependencies
- **Storage**: Result stored in `World.foundation.history.causal_graph` field (see Data Structures section)

---

#### Tool 3: `validate_implications`

**Purpose**: Given a premise, derive what MUST logically follow. Finds missing implications in world.

**Signature**:
```python
def validate_implications(
    agent_state: "AgentState",
    premise: str,            # "Fusion power is cheap and abundant"
    world: str,              # Full World JSON
    scope: str = "immediate", # "immediate" | "cascade" | "full"
) -> str:
```

**Returns** (JSON):
```json
{
  "required_implications": [
    "Energy-intensive processes become economically trivial (desalination, vertical farming, carbon capture)",
    "Fossil fuel economy collapses within decades",
    "Geopolitics shift away from energy resources to rare earth materials"
  ],
  "likely_implications": [
    "Space industry becomes economically viable (launch costs drop)",
    "Climate change mitigation becomes feasible at scale"
  ],
  "contradictions": [
    {
      "implication": "Fossil fuel economy should collapse",
      "world_state": "World still has oil-based economies in 2080",
      "severity": "major"
    }
  ],
  "missing_elements": [
    "No mention of rare earth material conflicts",
    "No description of energy storage infrastructure",
    "No social adaptation to post-scarcity energy"
  ]
}
```

**Implementation**:
- LLM reasons through multi-order implications
- `scope` parameter controls depth:
  - `immediate`: First-order effects only
  - `cascade`: Second/third-order effects
  - `full`: Full causal web exploration
- Compares implications against current world state
- Identifies contradictions and gaps

---

#### Tool 4: `cross_domain_consistency`

**Purpose**: Validate that implications cascade correctly across domains (physics → technology → economics → social).

**Signature**:
```python
def cross_domain_consistency(
    agent_state: "AgentState",
    world: str,              # Full World JSON
    domains: List[str] = ["physics", "technology", "economics", "social"],
) -> str:
```

**Returns** (JSON):
```json
{
  "consistent": false,
  "domain_graph": {
    "physics": {
      "key_rules": ["FTL requires exotic matter", "Relativity still holds"],
      "implies": ["technology"]
    },
    "technology": {
      "key_elements": ["Alcubierre drive", "Wormhole gates"],
      "implies": ["economics", "social"]
    },
    "economics": {
      "key_structures": ["Post-scarcity energy", "Interstellar trade"],
      "contradicts": ["physics.relativity → communication_delay_should_prevent_realtime_trade"]
    }
  },
  "violations": [
    {
      "from_domain": "physics",
      "to_domain": "economics",
      "description": "FTL enables instantaneous communication, but economic model still assumes light-speed trade delays",
      "example": "Stock market operates with 4-hour Earth-Mars lag despite FTL messaging",
      "severity": "major"
    }
  ],
  "recommendations": [
    "Update economic model to reflect instantaneous information transfer",
    "Add rule about FTL communication bandwidth limits if trade delays are intentional"
  ]
}
```

**Implementation**:
- Extract rules/elements from each domain
- Build implication graph showing domain-to-domain connections
- Validate that downstream domains reflect upstream constraints
- Multi-step LLM reasoning with structured output

---

#### Tool 5: `adversarial_probe`

**Purpose**: Self-questioning mode - challenge world elements to find contradictions, missing implications, or unjustified assumptions.

**Signature**:
```python
def adversarial_probe(
    agent_state: "AgentState",
    world_element: str,      # Element, rule, or technology to challenge
    world: str,              # Full World JSON for context
    probe_depth: str = "shallow",  # "shallow" | "deep"
) -> str:
```

**Returns** (JSON):
```json
{
  "challenges": [
    {
      "question": "If FTL travel is possible, why haven't we detected evidence of alien civilizations using it?",
      "challenge_type": "implication",
      "severity": "major"
    },
    {
      "question": "How does the Alcubierre drive handle momentum conservation when exiting warp?",
      "challenge_type": "feasibility",
      "severity": "minor"
    },
    {
      "question": "You claim exotic matter is stable, but this contradicts quantum field theory vacuum stability. How is this resolved?",
      "challenge_type": "contradiction",
      "severity": "fatal"
    }
  ],
  "requires_agent_response": true,
  "suggested_next_steps": [
    "Add working note about Fermi paradox resolution",
    "Research momentum transfer in warp bubbles",
    "Either justify exotic matter stability or acknowledge as speculative"
  ]
}
```

**Implementation**:
- LLM with adversarial system prompt: "You are a skeptical physicist reviewing this sci-fi world. Challenge it rigorously."
- `probe_depth`:
  - `shallow`: Surface-level questions (5-7 challenges)
  - `deep`: Exhaustive probing (15-20 challenges across all domains)
- Categorizes challenges by type and severity
- Agent can then address challenges or acknowledge speculation

---

### TIER 2: Story Coherence Tools (TypeScript/letta-code)

#### Tool 6: `story_manager` - New Operation: `add_event`

**Purpose**: Build canonical event graph for a story - the objective "what happened" independent of narrative perspective.

**Extends**: `letta-code/src/tools/impl/story_manager.ts`

**Signature**:
```typescript
story_manager({
  operation: "add_event",
  story_id: string,
  event: {
    id: string,               // "evt_001"
    timestamp: number,        // Relative story time (seconds from story start)
    location: string,         // Where it happened
    physical_facts: string[], // Objective reality (no interpretations)
    participants: string[],   // Character IDs who were present
    caused_by: string[],      // Event IDs that caused this (causal predecessors)
    information_state: Record<string, string[]> // After this event, who knows what?
  }
})
```

**Returns**:
```json
{
  "toolReturn": "Event evt_001 added to story story_id\nCausal predecessors: evt_000\nParticipants: guard, thief\nInformation updated for 2 characters",
  "status": "success",
  "data": {
    "event_id": "evt_001",
    "graph_nodes": 12,
    "causal_depth": 3
  }
}
```

**Implementation**:
- Load story from `.dsf/stories/{world_checkpoint}/{story_id}.json`
- Add event to story's `event_graph` (new field in Story type)
- Validate causal links (no circular dependencies)
- Update information state tracking (who knows what facts)
- Save updated story
- **Storage**: Event graph stored in `.dsf/stories/{world_checkpoint}/{story_id}/event_graph.json`

**Event Graph Structure**:
```typescript
interface EventGraph {
  nodes: Event[];
  metadata: {
    total_events: number;
    story_duration: number;  // Total timespan in story time
    max_causal_depth: number;
  };
}

interface Event {
  id: string;
  timestamp: number;
  location: string;
  physical_facts: string[];      // Objective reality
  participants: string[];        // Who was present
  caused_by: string[];           // Causal predecessors (event IDs)
  information_state: Record<string, string[]>; // character_id → facts_known
}
```

---

#### Tool 7: `story_manager` - New Operation: `validate_coherence`

**Purpose**: Check if a narrative (from a character's POV) is consistent with the canonical event graph.

**Extends**: `letta-code/src/tools/impl/story_manager.ts`

**Signature**:
```typescript
story_manager({
  operation: "validate_coherence",
  story_id: string,
  narrative: string,        // Story text to validate
  perspective: string,      // Character ID whose POV this is
  segment_id?: string       // Optional: specific segment to validate
})
```

**Returns**:
```json
{
  "toolReturn": "Coherence validation complete\nConsistent: false\n2 violations found\n\nViolation 1: Guard claims to see thief's blue eyes, but event graph shows guard had eyes closed during thief's passage\n\nViolation 2: Thief knows about alarm code, but information state shows thief never learned this",
  "status": "success",
  "data": {
    "consistent": false,
    "violations": [
      {
        "type": "impossible_knowledge",
        "description": "Character knows information they never learned",
        "event_id": "evt_005",
        "narrative_excerpt": "the thief knew the code was 4821"
      },
      {
        "type": "perspective_error",
        "description": "Character describes details they couldn't have observed",
        "event_id": "evt_002",
        "narrative_excerpt": "I saw his piercing blue eyes"
      }
    ],
    "information_timeline": {
      "evt_001": ["Character A learns fact X"],
      "evt_003": ["Character A learns fact Y"]
    }
  }
}
```

**Implementation**:
- Load event graph for story
- Extract character's information state timeline from event graph
- Use LLM to parse narrative and extract:
  - What facts are claimed
  - What events are described
  - What knowledge is assumed
- Compare narrative claims against:
  - Physical facts in event graph (did this actually happen?)
  - Character's information state (could they know this?)
  - Temporal ordering (is sequence correct?)
- Return structured violations with evidence

---

## Data Structure Changes

### 1. Extend World Type (`letta-code/src/types/dsf.ts`)

**Add to History interface**:
```typescript
export interface History {
  timeline?: TimelineEvent[];
  eras?: string[];
  key_events?: string[];
  causal_graph?: CausalGraph;  // NEW - stores trace_temporal_causality results
}

export interface CausalGraph {
  target_element: string;
  target_year: number;
  generated_at: string;        // ISO timestamp
  nodes: CausalNode[];
  metadata: {
    overall_plausibility: number;
    research_gaps: string[];
    speculative_leaps: string[];
  };
}

export interface CausalNode {
  milestone: string;
  year_estimate: number;
  prerequisites: string[];     // Milestone descriptions
  scientific_basis: string;
  confidence: "high" | "medium" | "low" | "speculative";
}
```

### 2. Extend Story Type (`letta-code/src/types/dsf.ts`)

**Add to Story interface**:
```typescript
export interface Story {
  id: string;
  world_checkpoint: string;
  world_version: number;
  metadata: StoryMetadata;
  segments: StorySegment[];
  endpoints: StoryEndpoint[];
  world_contributions: WorldContributions;
  event_graph?: EventGraph;    // NEW - canonical event timeline
}

export interface EventGraph {
  nodes: Event[];
  metadata: {
    total_events: number;
    story_duration: number;
    max_causal_depth: number;
  };
}

export interface Event {
  id: string;
  timestamp: number;             // Story time (seconds from start)
  location: string;
  physical_facts: string[];      // Objective reality
  participants: string[];        // Character IDs present
  caused_by: string[];           // Event ID predecessors
  information_state: Record<string, string[]>; // character_id → facts_known
}
```

### 3. Add New Evaluation Types (`letta-code/src/types/dsf.ts`)

**Add to evaluation types**:
```typescript
export interface ScientificGroundingReport {
  plausibility_score: number;
  scientific_basis: string;
  speculative_leaps: string[];
  justification_quality: "well_justified" | "acknowledged_speculation" | "unjustified";
  recommendations: string[];
  classification: "hard_science" | "plausible_extrapolation" | "hard_speculation" | "fantasy";
}

export interface CausalityValidationReport {
  valid: boolean;
  causal_chain_complete: boolean;
  circular_dependencies: string[];
  missing_prerequisites: string[];
  temporal_violations: string[];
}

export interface CoherenceReport {
  consistent: boolean;
  violations: CoherenceViolation[];
  information_timeline: Record<string, string[]>;
}

export interface CoherenceViolation {
  type: "impossible_knowledge" | "perspective_error" | "temporal_error" | "factual_error";
  description: string;
  event_id: string;
  narrative_excerpt: string;
  severity: "minor" | "major";
}

export type EvaluationResult =
  | ConsistencyReport
  | DepthAssessment
  | NoveltyReport
  | AbstractionReport
  | NarrativeEvaluation
  | ScientificGroundingReport
  | CausalityValidationReport
  | CoherenceReport;
```

---

## Critical Files to Modify

### Python/Letta Files (Backend Tools)

#### 1. Create New Module
**File**: `letta/functions/function_sets/scientific_grounding.py`
- Implement all 5 Python tools (assess, trace, validate, cross_domain, adversarial)
- Follow evaluation tools pattern (NotImplementedError stubs)
- Comprehensive docstrings with examples

#### 2. Extend Evaluation Executor
**File**: `letta/services/tool_executor/evaluation_tool_executor.py`
- Add 5 new methods to `LettaEvaluationToolExecutor` class
- Implement LLM-as-judge logic for each tool
- Use `_call_llm_for_evaluation` helper

#### 3. Register Tools
**File**: `letta/constants.py`
- Add `LETTA_SCIENTIFIC_GROUNDING_MODULE_NAME`
- Add `SCIENTIFIC_GROUNDING_TOOLS` list
- Add module to `LETTA_TOOL_MODULE_NAMES`
- Add tools to `LETTA_TOOL_SET`

#### 4. Update Executor Factory
**File**: `letta/services/tool_executor/tool_execution_manager.py`
- Add function map entries for scientific grounding tools in `LettaEvaluationToolExecutor.execute()`

#### 5. Map Tool Types
**File**: `letta/services/tool_manager.py`
- Add tool name → ToolType mapping (use `ToolType.LETTA_EVALUATION` since they use same executor)

### TypeScript/letta-code Files (CLI Tools)

#### 6. Extend story_manager
**File**: `letta-code/src/tools/impl/story_manager.ts`
- Add `case "add_event"` to operation switch
- Add `case "validate_coherence"` to operation switch
- Implement `addEvent()` helper function
- Implement `validateCoherence()` helper function

#### 7. Update Story Manager Types
**File**: `letta-code/src/types/dsf.ts`
- Add `EventGraph`, `Event`, `CausalGraph`, `CausalNode` interfaces (as shown above)
- Extend `Story` interface with `event_graph?: EventGraph`
- Extend `History` interface with `causal_graph?: CausalGraph`
- Add new evaluation report types

#### 8. Update Story Manager Schema
**File**: `letta-code/src/tools/schemas/story_manager.json`
- Add `add_event` to operation enum
- Add `validate_coherence` to operation enum
- Add event parameter schema
- Add narrative/perspective parameter schemas

#### 9. Update Documentation
**File**: `letta-code/src/tools/descriptions/story_manager.md`
- Document `add_event` operation with examples
- Document `validate_coherence` operation with examples

---

## Implementation Sequence

### Phase 1: Python Scientific Grounding Tools
1. Create `scientific_grounding.py` with 5 tool stubs
2. Extend `evaluation_tool_executor.py` with implementations
3. Register in `constants.py` and `tool_manager.py`
4. Test each tool individually with agent calls

### Phase 2: TypeScript Story Coherence Tools
5. Extend `dsf.ts` with new types (EventGraph, Event, etc.)
6. Extend `story_manager.ts` with `add_event` operation
7. Extend `story_manager.ts` with `validate_coherence` operation
8. Update schema and documentation
9. Test event graph building and validation

### Phase 3: Integration & Testing
10. Test full workflow: world creation → trace_temporal_causality → save with causal_graph
11. Test story workflow: create story → add events → validate_coherence
12. Test cross-tool integration (assess_scientific_grounding on world, then trace_temporal_causality)
13. Update CLAUDE.md with new tool examples

### Phase 4: Documentation & Migration
14. Document all new tools in CLAUDE.md
15. Create migration notes for existing worlds/stories
16. Add tests for each tool (optional but recommended)

---

## Verification Steps

### End-to-End Test: World Scientific Grounding

1. **Start Letta stack**:
   ```bash
   ./start.sh
   ```

2. **Create test world in CLI**:
   ```
   User: Create a world with fusion power and Mars colonies in 2080
   ```

3. **Agent should use new tools**:
   - Agent calls `trace_temporal_causality("fusion power", 2080)`
   - Gets causal chain from 2026 → 2080
   - Stores in world's `causal_graph` field
   - Agent calls `assess_scientific_grounding("fusion power")`
   - Gets plausibility score + justification assessment
   - Agent incorporates into world design

4. **Verify world saved with causal graph**:
   ```bash
   cat .dsf/worlds/{checkpoint}.json | jq '.foundation.history.causal_graph'
   ```
   Should show nodes with prerequisites and scientific basis

5. **Test implication validation**:
   ```
   User: Does this world account for all implications of cheap fusion?
   ```
   - Agent calls `validate_implications("cheap fusion", world_json)`
   - Gets required implications
   - Compares against world state
   - Reports missing elements or contradictions

### End-to-End Test: Story Coherence

1. **Create story with events**:
   ```
   User: Write a heist story where a thief sneaks past a guard
   ```

2. **Agent builds event graph**:
   - Agent calls `story_manager({operation: "add_event", event: {...}})`
   - Builds canonical timeline:
     - evt_001: Guard sits at desk, eyes closed
     - evt_002: Thief enters hallway
     - evt_003: Thief passes desk
     - evt_004: Guard opens eyes after thief passes

3. **Write from multiple perspectives**:
   ```
   User: Now tell the same story from the guard's perspective
   ```

4. **Agent validates coherence**:
   - Agent calls `story_manager({operation: "validate_coherence", perspective: "guard", narrative: "..."})`
   - Checks if guard's narrative matches event graph
   - Detects violations (e.g., "I saw his blue eyes" when eyes were closed)

5. **Verify event graph saved**:
   ```bash
   cat .dsf/stories/{world}/{story_id}/event_graph.json
   ```
   Should show events with causal links and information states

### Automated Tests (Optional)

Create test files:
- `letta/tests/test_scientific_grounding_tools.py`
- `letta-code/src/tests/tools/story-coherence.test.ts`

Test each tool's:
- Input validation
- LLM response parsing
- Error handling
- Output structure

---

## Migration Strategy

### Existing Worlds
- **No migration needed**: `causal_graph` is optional field
- Existing worlds continue working without causal graphs
- Agent can generate causal graphs on-demand for old worlds
- If agent runs `trace_temporal_causality` on existing world, result stored in next save

### Existing Stories
- **No migration needed**: `event_graph` is optional field
- Existing stories continue working without event graphs
- Agent can build event graphs retroactively if needed
- New stories will have event graphs from creation

### Graceful Degradation
- All new tools return meaningful errors if required fields missing
- Tools check for optional fields before accessing
- Agent can operate without using new tools (they're opt-in)

---

## Success Criteria

### World Scientific Grounding
- ✅ Agent can trace causal chains from today → future
- ✅ Agent assesses plausibility with nuanced reasoning (no brittle rules)
- ✅ Agent finds missing implications in worlds
- ✅ Agent validates cross-domain consistency
- ✅ Agent can self-question to find gaps

### Story Coherence
- ✅ Agent builds event graphs for stories
- ✅ Agent validates multi-perspective narratives against event graph
- ✅ Agent detects impossible knowledge and perspective errors
- ✅ Agent ensures temporal consistency across perspectives

### Integration
- ✅ All tools accessible via Letta API
- ✅ Tools return structured JSON
- ✅ Data persisted correctly in `.dsf/` directories
- ✅ No breaking changes to existing worlds/stories
- ✅ Documentation updated with examples

---

## Future Enhancements (Not in This Phase)

1. **Research Integration**: Use WebSearch to ground `trace_temporal_causality` in actual papers
2. **Visual Causality Graphs**: Render causal/event graphs in Canvas UI
3. **Interactive Validation**: Canvas UI shows coherence violations inline
4. **Automated Testing**: Agent runs validation tools automatically on world/story save
5. **Causal Diffing**: Compare causal chains between world versions
6. **Event Replay**: Reconstruct story from event graph in different orders

---

## Notes

- **No Z3/Prolog needed**: All symbolic checks done in TypeScript logic (event graph DAG validation, temporal ordering)
- **No external APIs required**: All tools work with LLM + file system
- **Backward compatible**: All changes are additive, no breaking modifications
- **Agent-driven**: Tools provide information, agent decides action (Bitter Lesson philosophy)
- **Scales with models**: Better models = better reasoning, no rule changes needed
