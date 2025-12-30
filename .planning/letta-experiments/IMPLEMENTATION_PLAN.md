# DSF + Letta Platform: Complete Implementation Plan

**Last Updated**: 2024-12-30
**Status**: Planning Phase

## Overview

Implementation plan for:
1. Generic eval + ABM tools for Letta platform
2. DSF agent as reference implementation
3. Migration of existing world manager

## Philosophy

✅ **Tools, not workflows** - Agent chooses when/if to use
✅ **Parameters, not hard-coding** - Flexible via inputs
✅ **Scales with better models** - Better judgment, not more rules
✅ **Light & generalizable** - Works for any domain

---

## Phase 0: Repository Setup

### Create DSF Agent Repository

**Location**: `~/Development/dsf-agent/` (new repo)

**Structure**:
```
dsf-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── tools/                      # Custom tool definitions (if needed later)
├── agents/                     # DSF agent setup
│   ├── dsf_agent.py           # Agent creator/manager
│   └── prompts.py             # System prompts
├── schemas/
│   └── world.py               # World data schema
├── examples/
│   └── simple_world.py        # Usage examples
└── tests/
```

**Dependencies**:
```toml
dependencies = [
    "letta-client>=0.5.0",      # For using Letta platform
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]
```

**Timeline**: 1 day
**Owner**: You
**Status**: ⏳ Not started

---

## Phase 1: Evaluation Tools (Letta Platform)

**Location**: `letta/` repo
**Timeline**: 2 weeks
**Priority**: HIGH (foundation for everything else)

### 1.1: Implement Core Eval Tools

**Where**: `/letta/functions/function_sets/evaluations.py` (NEW FILE)

**Tools to implement**:

#### Tool 1: `assess_output_quality`
```python
async def assess_output_quality(
    content: str,
    rubric: str,
    content_type: str = "text"
) -> dict
```

- **Implementation**: LLM-as-judge with structured output
- **Model**: claude-haiku-4 (fast, cheap)
- **Returns**: score, reasoning, strengths, improvements, meets_criteria
- **Tests**: Text, code, JSON across different rubrics
- **Timeline**: 3 days
- **Status**: ⏳ Not started

#### Tool 2: `check_logical_consistency`
```python
async def check_logical_consistency(
    content: str,
    rules: list[str] = None,
    format: str = "text"
) -> dict
```

- **Implementation**: Hybrid (algorithmic + LLM)
- **Algorithmic**: Simple rule contradiction checks
- **LLM**: claude-sonnet-4 for complex contradictions
- **Returns**: consistent, contradictions (with elements, description, severity)
- **Tests**: Contracts, schemas, worlds, general text
- **Timeline**: 4 days
- **Status**: ⏳ Not started

#### Tool 3: `compare_versions`
```python
async def compare_versions(
    current: str,
    previous: str,
    comparison_criteria: str = "quality, novelty, accuracy"
) -> dict
```

- **Implementation**: Structural diff + LLM analysis
- **Diff**: Python `difflib` or custom
- **LLM**: claude-sonnet-4 for quality comparison
- **Returns**: improved, changes, better_aspects, worse_aspects, recommendation
- **Tests**: Writing, code, structured data
- **Timeline**: 3 days
- **Status**: ⏳ Not started

#### Tool 4: `analyze_information_gain`
```python
async def analyze_information_gain(
    after: str,
    before: str,
    metric: str = "novelty"
) -> dict
```

- **Implementation**: Diff + LLM synthesis
- **Focus**: What's NEW, not just different
- **LLM**: claude-sonnet-4
- **Returns**: information_gain (0-1), new_facts, insights, significance
- **Tests**: Research outputs, world iterations, data analysis
- **Timeline**: 3 days
- **Status**: ⏳ Not started

**Total timeline for 1.1**: 13 days

### 1.2: Create Evaluation Tool Executor

**Where**: `/letta/services/tool_executor/evaluation_tool_executor.py` (NEW FILE)

**Implementation**:
```python
class EvaluationToolExecutor(ToolExecutor):
    """Executor for evaluation tools"""

    async def execute_tool_async(
        self,
        tool_name: str,
        tool_args: dict,
        agent_state: AgentState
    ) -> dict:
        # Route to appropriate eval tool
        # Handle LLM calls
        # Return structured results
```

- **Inherits from**: `ToolExecutor` base class
- **Handles**: All 4 eval tools
- **Timeline**: 1 day
- **Status**: ⏳ Not started

### 1.3: Register Tools in Letta

**Where**: Multiple files in `letta/`

**Changes needed**:
1. Add `evaluations` to `ToolType` enum
2. Register executor in `ToolExecutorFactory`
3. Add to built-in tools list
4. Update tool schemas

**Timeline**: 1 day
**Status**: ⏳ Not started

### 1.4: Tests & Documentation

**Where**:
- `/letta/tests/test_evaluation_tools.py` (NEW)
- `/letta/docs/tools/evaluations.md` (NEW)

**Tests**:
- Unit tests for each tool
- Integration tests with different content types
- Performance tests (latency < 3s per eval)
- Error handling tests

**Documentation**:
- Tool descriptions
- Usage examples for different domains
- Best practices
- API reference

**Timeline**: 2 days
**Status**: ⏳ Not started

**Phase 1 Total**: 17 days (3.5 weeks)

---

## Phase 2: Simulation Tools (Letta Platform)

**Location**: `letta/` repo
**Timeline**: 2 weeks
**Priority**: MEDIUM (after eval tools working)

### 2.1: Implement Mechanical ABM Tool

**Where**: `/letta/functions/function_sets/simulation.py` (NEW FILE)

#### Tool 5: `simulate_mechanics`
```python
async def simulate_mechanics(
    scenario_description: str,
    context: dict = None,
    steps: int = 50
) -> dict
```

**Implementation**:
1. **LLM scenario → config** (claude-sonnet-4)
   - Parse scenario into agent types, behaviors, rules
   - Generate Mesa model config

2. **Build Mesa model**
   - Dynamic model generation from config
   - Agent classes created on-the-fly

3. **Run simulation**
   - Execute for N steps
   - Collect data (states, interactions, metrics)

4. **LLM analysis** (claude-sonnet-4)
   - Synthesize emergent behaviors
   - Identify surprises
   - Extract insights

**Dependencies**: `mesa>=3.4.0`

**Returns**: outcome, emergent_behaviors, interactions, surprises, suggests

**Tests**:
- Opinion dynamics (social)
- Market dynamics (economic)
- Disease spread (epidemiological)
- Traffic flow (urban)
- DSF scenarios (neural interfaces, etc.)

**Timeline**: 7 days
**Status**: ⏳ Not started

### 2.2: Implement Social LLM Roleplay Tool

**Where**: `/letta/functions/function_sets/simulation.py`

#### Tool 6: `simulate_interactions`
```python
async def simulate_interactions(
    scenario_description: str,
    agents: list[dict],  # Agent descriptions
    rounds: int = 5
) -> dict
```

**Implementation**:
1. **Initialize agent contexts**
   - Create prompt for each agent
   - Include personality, role, goals

2. **Run interaction rounds**
   - Each agent takes turn (LLM call)
   - Update contexts based on interactions
   - Track conversation/actions

3. **Synthesize results**
   - LLM analyzes all interactions
   - Extract social dynamics
   - Narrative summary

**Model**: claude-haiku-4 (for cost control)

**Returns**: narrative, social_dynamics, conflicts, resolutions, character_insights

**Cost consideration**: ~5-10 agents × 5 rounds × 2 LLM calls = 50-100 calls
- At $0.25/call = $12-25 per simulation
- Need to make this clear to users

**Tests**:
- 3-5 characters with personality differences
- Conflict scenarios
- Decision-making under uncertainty
- DSF character interactions

**Timeline**: 5 days
**Status**: ⏳ Not started

### 2.3: Create Simulation Tool Executor

**Where**: `/letta/services/tool_executor/simulation_tool_executor.py` (NEW FILE)

**Implementation**:
```python
class SimulationToolExecutor(ToolExecutor):
    """Executor for simulation tools"""

    async def execute_tool_async(
        self,
        tool_name: str,
        tool_args: dict,
        agent_state: AgentState
    ) -> dict:
        # Route to mechanics or interactions
        # Handle long-running simulations
        # Return results
```

**Timeline**: 1 day
**Status**: ⏳ Not started

### 2.4: Tests & Documentation

**Where**:
- `/letta/tests/test_simulation_tools.py` (NEW)
- `/letta/docs/tools/simulation.md` (NEW)

**Tests**:
- Mesa model generation
- Various scenarios (social, economic, etc.)
- LLM roleplay with different personalities
- Performance (mechanics < 5s, interactions < 2min)

**Documentation**:
- When to use mechanics vs interactions
- Example scenarios
- Cost considerations for roleplay
- Best practices

**Timeline**: 2 days
**Status**: ⏳ Not started

**Phase 2 Total**: 15 days (3 weeks)

---

## Phase 3: World Manager Migration

**Location**: Multiple repos
**Timeline**: 1 week
**Priority**: MEDIUM (parallel with Phase 2)

### 3.1: Assess Current Implementation

**Current location**: `letta-code/src/tools/impl/world_manager.ts`

**Current features**:
- save_world() - Saves to `.dsf/worlds/`
- load_world() - Loads from checkpoint
- diff_worlds() - Compare versions
- update_world() - Apply incremental updates

**Current storage**: `letta-code/.dsf/worlds/*.json`

**Timeline**: 0.5 days (review)
**Status**: ⏳ Not started

### 3.2: Decision: Keep in letta-code or Move?

**Option A: Keep in letta-code** ✅ RECOMMENDED
- World manager stays as letta-code local tool
- Storage remains in `.dsf/worlds/`
- DSF agent can reference it via CLI or file paths

**Option B: Migrate to dsf-agent**
- Reimplement in Python
- Move storage to `dsf-agent/storage/worlds/`
- More self-contained but duplicates code

**Decision**: Choose Option A (keep as-is)
- Reason: Already working, letta-code is your UI layer
- Storage with UI makes sense
- Less migration work

**Timeline**: 0 days (keep as-is)
**Status**: ✅ Decision made

### 3.3: Document Integration Pattern

**Where**: `dsf-agent/docs/architecture.md` (NEW)

**Document**:
- How dsf-agent uses letta-code for world storage
- File path conventions
- When to use world_manager vs custom tools

**Timeline**: 0.5 days
**Status**: ⏳ Not started

**Phase 3 Total**: 1 day

---

## Phase 4: DSF Agent Implementation

**Location**: `dsf-agent/` repo
**Timeline**: 2 weeks
**Priority**: MEDIUM (after Phase 1 complete)

### 4.1: Agent Setup & Configuration

**Where**: `dsf-agent/agents/dsf_agent.py`

**Implementation**:
```python
class DSFAgent:
    """Deep Sci-Fi World Building Agent"""

    def __init__(self, api_key: str = None):
        self.client = Letta(api_key=api_key)
        self.agent_id = None

    def setup(self):
        # Create agent with all Letta platform tools
        agent = self.client.agents.create(
            model='claude-sonnet-4.5',
            tools=[
                # Letta built-in tools
                'send_message',
                'memory',
                'conversation_search',
                'archival_memory_insert',
                'archival_memory_search',

                # Evaluation tools (from Letta platform)
                'assess_output_quality',
                'check_logical_consistency',
                'compare_versions',
                'analyze_information_gain',

                # Simulation tools (from Letta platform)
                'simulate_mechanics',
                'simulate_interactions',
            ],
            memory_blocks=[
                {'label': 'human', 'value': 'User wants deep sci-fi worlds'},
                {'label': 'persona', 'value': DSF_SYSTEM_PROMPT}
            ]
        )
        self.agent_id = agent.id
        return agent

    def create_world(self, prompt: str):
        response = self.client.agents.messages.create(
            agent_id=self.agent_id,
            input=prompt
        )
        return response
```

**Timeline**: 2 days
**Status**: ⏳ Not started

### 4.2: System Prompt Design

**Where**: `dsf-agent/agents/prompts.py`

**Content**:
```python
DSF_SYSTEM_PROMPT = """
You are a Deep Sci-Fi world building agent.

CORE PRINCIPLES:
1. Logical Consistency - Use check_logical_consistency()
2. Abstraction - Use assess_output_quality() with abstraction rubric
3. Deep Research - Use assess_output_quality() with depth rubric
4. Self-Evaluation - Check your work before finalizing

AVAILABLE EVALUATION TOOLS:
- assess_output_quality(content, rubric, type)
  Use for: checking quality against any criteria
  Example: assess_output_quality(world, "consistent, abstract, deep", "json")

- check_logical_consistency(content, rules, format)
  Use for: finding contradictions
  Example: check_logical_consistency(world, format="json")

- compare_versions(current, previous, criteria)
  Use for: measuring improvement
  Example: compare_versions(world_v2, world_v1, "depth, abstraction")

- analyze_information_gain(after, before, metric)
  Use for: assessing novelty
  Example: analyze_information_gain(world_v2, world_v1, "novelty")

SIMULATION TOOLS:
- simulate_mechanics(scenario, context, steps)
  Use for: testing world mechanics, finding emergent patterns
  Example: simulate_mechanics("station with interface failures", world, 50)

- simulate_interactions(scenario, agents, rounds)
  Use for: exploring character dynamics
  Example: simulate_interactions("5 characters react to crisis",
                                   [{"role": "stoic"}, ...], 5)

YOU DECIDE WHEN AND IF TO USE THESE TOOLS.
No prescribed workflow. Use judgment.
"""
```

**Timeline**: 1 day
**Status**: ⏳ Not started

### 4.3: Example Workflows

**Where**: `dsf-agent/examples/`

**Files**:
- `simple_world.py` - Basic world creation
- `iterative_refinement.py` - Using eval tools to improve
- `simulation_testing.py` - Using ABM to test mechanics
- `character_development.py` - Using LLM roleplay

**Timeline**: 2 days
**Status**: ⏳ Not started

### 4.4: Tests

**Where**: `dsf-agent/tests/`

**Tests**:
- Agent setup and configuration
- World creation with eval tools
- Simulation usage
- Integration with letta-code world storage

**Timeline**: 2 days
**Status**: ⏳ Not started

### 4.5: Documentation

**Where**: `dsf-agent/README.md`, `dsf-agent/docs/`

**Docs**:
- Getting started
- Architecture overview
- Tool usage patterns
- Examples and tutorials
- Reference implementation for Letta docs

**Timeline**: 2 days
**Status**: ⏳ Not started

**Phase 4 Total**: 9 days (2 weeks)

---

## Phase 5: Testing & Refinement

**Location**: All repos
**Timeline**: 1 week
**Priority**: HIGH (quality gate)

### 5.1: Integration Testing

**Tests**:
- DSF agent creates world using all eval tools
- Simulations run successfully
- Results are meaningful (not hallucinated)
- Performance is acceptable

**Success criteria**:
- Eval tools return useful feedback
- ABM shows real emergence (not random)
- LLM roleplay is coherent
- DSF agent produces better worlds than baseline

**Timeline**: 3 days
**Status**: ⏳ Not started

### 5.2: User Testing

**Tests**:
- Other use cases beyond DSF (code review, writing, data)
- Performance under load
- Cost analysis
- User feedback

**Timeline**: 2 days
**Status**: ⏳ Not started

### 5.3: Documentation Review

**Review**:
- All tool docs are clear
- Examples work
- Architecture is documented
- Migration guides are complete

**Timeline**: 1 day
**Status**: ⏳ Not started

### 5.4: Bug Fixes & Polish

**Work**:
- Fix issues from testing
- Optimize performance
- Improve error messages
- Add missing features

**Timeline**: 2 days
**Status**: ⏳ Not started

**Phase 5 Total**: 8 days (1.5 weeks)

---

## Phase 6: Contribution to Letta Platform

**Location**: `letta/` repo
**Timeline**: 1 week
**Priority**: MEDIUM (once everything tested)

### 6.1: Prepare Pull Request

**Work**:
- Clean up code
- Ensure all tests pass
- Update CHANGELOG
- Write PR description

**Timeline**: 1 day
**Status**: ⏳ Not started

### 6.2: Documentation for Letta

**Where**: `letta/docs/`

**Docs**:
- Tool reference for evaluations
- Tool reference for simulation
- Best practices guide
- DSF as example use case

**Timeline**: 2 days
**Status**: ⏳ Not started

### 6.3: Submit PR & Address Feedback

**Process**:
- Submit PR to letta repo
- Respond to code review
- Make requested changes
- Get approval and merge

**Timeline**: 3 days (assuming quick review)
**Status**: ⏳ Not started

**Phase 6 Total**: 6 days (1 week)

---

## Summary Timeline

| Phase | Duration | Dependency | Location |
|-------|----------|------------|----------|
| Phase 0: Repo Setup | 1 day | None | dsf-agent/ |
| Phase 1: Eval Tools | 17 days | Phase 0 | letta/ |
| Phase 2: Simulation Tools | 15 days | Phase 1 | letta/ |
| Phase 3: World Manager | 1 day | None (parallel) | letta-code/ |
| Phase 4: DSF Agent | 9 days | Phase 1 | dsf-agent/ |
| Phase 5: Testing | 8 days | Phases 1-4 | All repos |
| Phase 6: Contribution | 6 days | Phase 5 | letta/ |

**Total duration**: ~57 days (~11 weeks, ~2.5 months)

**Can be parallelized**:
- Phase 2 and 4 can overlap (after Phase 1)
- Phase 3 can happen anytime

**Realistic timeline**: 8-10 weeks with parallelization

---

## Repository Locations Summary

### letta/ (Platform)
```
letta/
├── functions/function_sets/
│   ├── evaluations.py          # ⭐ NEW (Phase 1)
│   └── simulation.py           # ⭐ NEW (Phase 2)
│
├── services/tool_executor/
│   ├── evaluation_tool_executor.py    # ⭐ NEW (Phase 1)
│   └── simulation_tool_executor.py    # ⭐ NEW (Phase 2)
│
└── tests/
    ├── test_evaluation_tools.py       # ⭐ NEW (Phase 1)
    └── test_simulation_tools.py       # ⭐ NEW (Phase 2)
```

### letta-code/ (UI/CLI)
```
letta-code/
├── .dsf/worlds/                # ✅ Keep as-is (Phase 3)
│   └── *.json
│
└── src/tools/impl/
    └── world_manager.ts        # ✅ Keep as-is (Phase 3)
```

### dsf-agent/ (Application)
```
dsf-agent/                      # ⭐ NEW (Phase 0)
├── agents/
│   ├── dsf_agent.py           # ⭐ NEW (Phase 4)
│   └── prompts.py             # ⭐ NEW (Phase 4)
│
├── examples/
│   ├── simple_world.py        # ⭐ NEW (Phase 4)
│   └── ...
│
└── tests/
    └── ...                     # ⭐ NEW (Phase 4)
```

---

## Tools Summary

### 6 Platform Tools (in letta/)

**Evaluation Tools** (4):
1. `assess_output_quality(content, rubric, type)` - Generic quality assessment
2. `check_logical_consistency(content, rules, format)` - Find contradictions
3. `compare_versions(current, previous, criteria)` - Measure improvement
4. `analyze_information_gain(after, before, metric)` - Assess novelty

**Simulation Tools** (2):
5. `simulate_mechanics(scenario, context, steps)` - Mesa ABM for mechanics
6. `simulate_interactions(scenario, agents, rounds)` - LLM roleplay for social

### Existing Tools (keep as-is)

**World Manager** (in letta-code/):
- `world_manager(operation, ...)` - save/load/diff/update worlds

---

## Dependencies

### New Dependencies for letta/
```toml
[project.dependencies]
mesa = ">=3.4.0"  # For ABM simulation
```

### New Dependencies for dsf-agent/
```toml
[project.dependencies]
letta-client = ">=0.5.0"  # For using Letta platform
pydantic = ">=2.0.0"
python-dotenv = ">=1.0.0"
```

---

## Success Criteria

### For Platform Tools
- ✅ Used by agents beyond DSF (code review, writing, etc.)
- ✅ Performance: Eval < 3s, ABM < 5s, Roleplay < 2min
- ✅ Quality: Feedback is actionable and accurate
- ✅ Cost: Reasonable (evals ~$0.01, ABM ~$0.01, roleplay ~$1-5)

### For DSF Agent
- ✅ Produces logically consistent worlds
- ✅ Uses abstract roles (not concrete names)
- ✅ Shows evidence of deep research
- ✅ Demonstrates effective use of eval/sim tools
- ✅ Better than baseline (direct Claude without tools)

### For Contribution
- ✅ PR accepted by Letta maintainers
- ✅ Tools adopted by Letta community
- ✅ DSF documented as reference implementation

---

## Risk Mitigation

### Risk 1: LLM encoding of scenarios fails
**Mitigation**: Extensive testing with diverse scenarios, fallback to simpler models

### Risk 2: Mesa simulations don't show real emergence
**Mitigation**: Start with well-known models (Schelling, SIR), validate emergence

### Risk 3: Eval tools give unhelpful feedback
**Mitigation**: Iterate on rubrics with real examples, A/B test prompts

### Risk 4: Performance too slow
**Mitigation**: Use faster models (haiku) where possible, cache results, parallel execution

### Risk 5: DSF agent doesn't improve with tools
**Mitigation**: Measure baseline first, iterate on system prompt, add examples

---

## Next Steps

1. **Review this plan** ✅ (you're here!)
2. **Create dsf-agent repo** (Phase 0)
3. **Start Phase 1** - Implement eval tools
4. **Iterate based on testing**

---

## Notes

- **Philosophy check**: All tools follow bitter lesson (tools not workflows, parameters not hard-coding, scales with better models)
- **Generalizability check**: All tools work for domains beyond DSF
- **Lightweight check**: No heavy dependencies, fast execution, reasonable costs
- **Integration**: DSF agent uses platform tools, not custom implementations

---

## Open Questions

1. Should we implement Phase 2 (simulation) before Phase 4 (DSF agent)?
   - **Recommendation**: Yes, so DSF can use simulations

2. Should we add SimPy as well as Mesa?
   - **Recommendation**: Start with Mesa only, add SimPy later if needed

3. Should eval tools support async/background execution?
   - **Recommendation**: Start with sync, add async later if performance issues

4. Should we expose Z3 as advanced tool?
   - **Recommendation**: No for platform, DSF can use as custom tool if needed

---

**Status**: Plan complete, ready for Phase 0! 🚀
