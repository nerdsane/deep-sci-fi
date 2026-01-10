# DSF Agent Design Philosophy

*Applying the Bitter Lesson to Deep Sci-Fi agent architecture*

## Core Principle

**Tools over workflows. Evaluation over prescription. Scale with better models.**

Methods that leverage computation and learning scale better than methods that bake in human knowledge about "the right way" to do things.

## The Key Distinctions

### 1. Self-Eval vs. External Eval (Both Needed)

**Agent Self-Evaluation**
- **Purpose**: Steering mechanism *during* execution
- **Example**: "Did this simulation reveal anything non-obvious? If not, try a different angle"
- **Why**: Helps agent learn to assess its own work, improves with better models
- **Risk**: Agent might be biased toward its own outputs

**External Evaluation (Human/System)**
- **Purpose**: Measure if the *system* is working, guide *your* improvements
- **Example**: "Did the final world have logical contradictions? Was the story compelling?"
- **Why**: Iterate on prompts, tools, eval criteria
- **Not prescriptive**: Agent doesn't see this, it's meta-level

### 2. Tools vs. Prescriptions

**✅ Providing Tools (Good)**
```
- "You can save worlds as JSON with these fields: {entities, rules, state, timeline}"
  → Provides capability, agent chooses when/if to use

- "You have tools: ABM simulation, Z3 verification, world save/load, diff_worlds"
  → Empowers agent, doesn't mandate order

- "You can run ABM simulations to see emergent behavior"
  → Offers method without requiring it
```

**❌ Prescribing Workflows (Bad)**
```
- "After every simulation, save world in this exact format"
  → Prescriptive workflow

- "First simulate, then verify, then research"
  → Hard-coded sequence

- "Always use ABM with 100 agents for 50 timesteps"
  → Brittle rules that won't scale
```

**The Line**: Giving a tool ≠ prescribing its use

### 3. Formats as Infrastructure, Not Constraints

**Standardizing data formats is OK**
- Reason: Makes worlds parseable, comparable, enables tooling
- Example: JSON schema for worlds
- NOT prescriptive: This is infrastructure, like "here's how JSON works"

**But don't mandate when/how often to use formats**
- Agent decides: "I should checkpoint this before testing edge cases"
- Format enables capability, doesn't dictate workflow

## The Spectrum: What Scales vs. What Constrains

### 🟢 Scales with Better Models

- **Diverse tools**: ABM, Z3, search, simulation, verification
- **Objective quality criteria**: "Simulations should surface contradictions"
- **Self-eval prompts**: Teach critical thinking, not rote steps
- **Examples**: Few-shot learning with good/bad outputs
- **Rich toolbox**: More options for agent to choose from

### 🟡 Neutral

- **Standardized data formats**: World JSON structure
- **Tool interfaces/APIs**: How to call functions
- **Infrastructure**: Save/load, checkpoint mechanisms

### 🔴 Fights Better Models

- **Hard-coded sequences**: "First do X, then Y, then Z"
- **Brittle rules**: "Always use tool X for problem type Y"
- **Step-based constraints**: Limiting tools by step number
- **Fixed parameters**: Mandating agents=100, steps=50
- **Prescribed workflows**: Forcing specific orderings

## Practical Architecture for DSF + Letta

### What to Build

**Give the agent:**
1. **Rich toolbox**:
   - ABM simulation (emergent behavior)
   - Z3 verification (logical consistency)
   - Search/research tools
   - World save/load/diff
   - Narrative simulation

2. **Self-eval prompts**:
   - "What did this reveal?"
   - "Is this non-obvious?"
   - "How deep was this insight?"
   - "Did I find a contradiction?"

3. **Quality rubrics**:
   - Examples of deep vs. shallow research
   - Examples of useful vs. obvious simulations
   - Clear criteria for "good work"

4. **Standard formats**:
   - World schema for interoperability
   - Simulation output structure
   - Research note format

**Don't build:**
1. Mandatory sequences ("always do X before Y")
2. Hard-coded decision trees
3. "Always use X for Y" rules
4. Step counters that gate capabilities

**You evaluate** (external to agent):
1. **Final outputs**: World coherence? Story compelling?
2. **Intermediate quality**: Were simulations useful? Research deep?
3. **Efficiency**: Did agent waste cycles?
4. **Use results to**: Tune prompts, add/remove tools, refine criteria

## The Real Test

**Question**: "If GPT-7 or Claude Opus 5 came out, would my system get better automatically, or would my constraints hold it back?"

- ✅ Better model with toolbox → better tool choices, deeper self-eval
- ❌ Better model with hard-coded workflows → stuck with your rules

## Evaluation-Driven vs. Workflow-Driven

### Instead of:
```
1. Generate world
2. Run simulation
3. Verify with Z3
4. Research implications
5. Iterate
```

### Try:
```
Agent has tools: {simulate_abm, verify_z3, research, save_world, diff_worlds}

Agent has quality criteria:
- "Simulations should test edge cases or surface contradictions"
- "Research should connect non-obvious concepts"
- "Verification should find actual logical flaws"

Agent self-evaluates at natural breakpoints:
- "Did I learn something non-obvious?"
- "Should I go deeper or pivot?"
- "Is this useful for the story?"

Agent chooses: what to do, when, and how
```

## Intermediate Outcome Evaluation

Instead of prescribing steps, evaluate information gain:

```
After each major action:
├─ Agent assesses: "What did I learn? What's still uncertain?"
├─ Agent rates: "How novel/deep was this? How relevant?"
└─ Agent decides: "Continue this thread, pivot, or conclude?"
```

You're evaluating *information gain* and *relevance*, not *following steps*.

## Open Questions to Keep Exploring

1. What are the actual failure modes in current Letta outputs?
   - Simulations too obvious/shallow?
   - Research restating vs. synthesizing?
   - Agent giving up too early?

2. What does "one level deeper" look like?
   - Simulation: Second-order effects? Adversarial scenarios?
   - Research: Conceptual models? Distant connections?

3. Can we define quality objectively enough?
   - "Reveals a contradiction"
   - "Tests a boundary condition"
   - "Explores interaction between N constraints"

4. Should evaluation be semi-automated?
   - Agent does work
   - Separate evaluation pass (same model, different prompt)
   - Agent sees evaluation and can revise

## Remember

The goal is to build a system that gets better as models improve, not one that constrains what better models can do.

**Tools, not prescriptions. Evaluation, not workflows.**

---

# Implementation Plan: DSF + Letta Agent

## What We're Trying to Achieve

### The Problem
Current DSF with direct Claude interaction produces:
- Simulations that aren't always useful (test obvious scenarios, not edge cases)
- Research that isn't deep enough (surface-level retrieval, not synthesis)
- Worlds with unnecessary concreteness (random names, cultural elements)
- Inconsistent quality (no reliable self-correction mechanism)

### The Vision
An agent system that:
- **Self-directs**: Chooses what to do and when, no prescribed workflows
- **Self-evaluates**: Assesses its own work, decides to go deeper or pivot
- **Self-corrects**: Detects issues (shallow research, concrete names) and revises
- **Scales**: Gets better automatically with improved models (GPT-7, Opus 5, etc)
- **Produces quality**: Logically consistent, deeply researched, abstractly designed worlds

### The Approach
Instead of telling the agent HOW to work (workflows), we:
1. Give powerful tools (action + evaluation)
2. Provide clear quality criteria (examples, rubrics)
3. Enable self-assessment (evaluation tools agent can use)
4. Measure outcomes (external eval for system improvement)
5. Iterate based on data (adjust prompts/tools based on what works)

### Key Insight: Unified Evaluation Model
Agent and system use THE SAME evaluation tools:
- Agent has access to: `verify_consistency()`, `assess_depth()`, `check_abstraction()`
- Agent chooses when to use them (self-eval is agent-initiated)
- System runs the same tools systematically (external eval)
- System measures: quality of outputs + agent's use of eval tools

This is elegant because:
- Not prescribing when to evaluate, just providing capability
- Fair: only evaluating on criteria agent could check
- Transparent: agent knows what quality means
- Scalable: better models will use eval tools more strategically

## The Unified Evaluation Model (Core Architecture)

### Two Types of Tools

**Action Tools** (produce artifacts):
- `save_world()`, `load_world()`, `diff_worlds()`
- `simulate_abm()`
- `research()`

**Evaluation Tools** (assess quality):
- `verify_consistency()` - check for contradictions
- `assess_depth()` - rate how deep/thorough
- `check_novelty()` - what's new/surprising
- `evaluate_narrative()` - story quality
- `check_abstraction()` - detect concrete names/cultural elements

### The Key Difference

```
Internal (agent-initiated):
├─ Agent decides: "Should I verify consistency now?"
├─ Agent runs: verify_consistency(world)
├─ Agent interprets: "Found contradiction, need to fix"
└─ Agent acts: modifies world

External (systematic):
├─ We run: verify_consistency(final_world)
├─ We check: Did agent catch this? When?
├─ We measure: Quality of final output
└─ We assess: Did agent use eval tools effectively?
```

**External eval measures:**
1. Final output quality (using eval tools)
2. Whether agent used eval tools appropriately
3. Efficiency (actions needed to reach quality)

### Why This Works

- ✅ Not prescriptive: Agent chooses when/if to evaluate
- ✅ Fair: Only eval on criteria agent could check
- ✅ Transparent: Agent knows what "quality" means
- ✅ Scalable: Better models use eval tools more strategically

## Complete Tool Suite (Lean & Essential)

### World Management Tools

```python
save_world(world, checkpoint_name: str) -> SaveResult
  Purpose: Persist world state
  Returns: {saved: bool, path: str, timestamp: str}

  Why: Enables exploration without prescribing path
       Agent can checkpoint before risky changes
       No mandatory autosave, agent decides when

load_world(checkpoint_name: str) -> World
  Purpose: Restore previous state
  Returns: Full world object

  Why: Enables backtracking and exploration
       Agent can try different approaches

diff_worlds(checkpoint1: str, checkpoint2: str) -> DiffReport
  Purpose: Compare two world states
  Returns: {
    "entities_added": [list],
    "entities_removed": [list],
    "rules_changed": [list],
    "complexity_delta": float
  }

  Why: Shows what changed, agent interprets significance
       Helps assess progress
```

**Design decisions:**
- Just 3 tools (save/load/diff)
- No forced naming conventions
- No mandatory checkpoints
- Agent controls when to persist

### Simulation Tool

```python
simulate_abm(
    world: World,
    scenario: str,  # natural language description
    config: dict = {  # all optional
        "agent_count": int,
        "steps": int,
        "focus": str  # what to observe
    }
) -> SimulationResult

  Purpose: Run agent-based model simulation
  Returns: {
    "outcome": str,  # narrative description
    "emergent_behaviors": [list],
    "rule_interactions": [list],
    "unexpected_events": [list],
    "data": dict  # raw simulation data
  }
```

**Design decisions:**
- Just ONE simulation tool (ABM is general enough)
- Natural language scenario input (agent describes what to test)
- All config optional (smart defaults)
- Returns both narrative and raw data
- Can add more simulation types later if needed

### Research Tool (With Built-in Depth Guidance)

```python
research(
    query: str,
    depth_target: str = "auto"  # "surface" | "medium" | "deep" | "auto"
) -> ResearchResult

  Purpose: Search and synthesize information
  Returns: {
    "findings": str,  # synthesized insights
    "sources": [list],
    "connections": [list],  # concepts linked
    "depth_achieved": "surface" | "medium" | "deep",
    "depth_feedback": str,  # "Consider exploring X" or "Good depth"
    "follow_up_questions": [list]  # suggestions for going deeper
  }
```

**Design decisions:**
- Tool itself provides depth feedback
- If agent got surface results, tool suggests follow-ups
- Agent can see "This was shallow" and choose to research more
- Not prescriptive: agent CAN stop at surface if appropriate
- Tool guides toward depth without mandating it

**How depth feedback works:**
```python
# Inside research tool implementation
depth_signals = {
    "surface": {
        "indicators": ["single source", "factual retrieval", "no synthesis"],
        "feedback": "Found basic facts. Consider: {follow_ups}",
        "follow_ups": generate_deeper_questions(query, findings)
    },
    "medium": {
        "indicators": ["multiple sources", "some connections", "comparison"],
        "feedback": "Connected some concepts. Deeper angles: {follow_ups}",
        "follow_ups": generate_deeper_questions(query, findings)
    },
    "deep": {
        "indicators": ["synthesis", "non-obvious connections", "models built"],
        "feedback": "Deep exploration achieved.",
        "follow_ups": []
    }
}
```

### Verification Tool

```python
verify_consistency(world: World) -> ConsistencyReport

  Purpose: Check world for logical contradictions
  Returns: {
    "consistent": bool,
    "contradictions": [
        {
            "elements": [list],  # which rules/entities conflict
            "description": str,
            "severity": "minor" | "major"
        }
    ],
    "edge_cases_checked": int,
    "verification_approach": str  # how verified (Z3, logic, etc)
  }
```

**Design decisions:**
- Z3 is implementation detail (hidden under the hood)
- Agent cares about "is it consistent?", not "how to write Z3"
- Returns actionable issues
- Can use best verification method (Z3, logical reasoning, etc)

### Evaluation Tools (Self-Assessment)

```python
assess_depth(
    content: str,  # research output, simulation description, etc
    content_type: "research" | "simulation" | "world"
) -> DepthAssessment

  Purpose: Evaluate how deep/thorough something is
  Returns: {
    "depth_score": 1-5,
    "depth_category": "surface" | "medium" | "deep",
    "reasoning": str,  # why this score
    "strengths": [list],
    "could_go_deeper": [list],  # specific suggestions
    "comparison": str  # "typical", "above average", "shallow"
  }

check_novelty(current: World, previous: World = None) -> NoveltyReport

  Purpose: Assess what's new/surprising
  Returns: {
    "novelty_score": float,
    "new_elements": {
        "entities": [list],
        "rules": [list],
        "relationships": [list]
    },
    "surprisingness": float,  # how unexpected
    "insights": [list],  # what was learned
    "significance": str  # "minor iteration" | "major advance"
  }

evaluate_narrative(story: str, world: World) -> NarrativeEvaluation

  Purpose: Assess story quality
  Returns: {
    "structure": {
        "has_conflict": bool,
        "has_stakes": bool,
        "character_agency": bool,
        "arc_complete": bool
    },
    "grounding": {
        "follows_world_rules": bool,
        "rules_used": [list],
        "violations": [list]
    },
    "quality": {
        "emotional_resonance": 1-5,
        "interestingness": 1-5,
        "originality": 1-5
    },
    "feedback": str,  # specific suggestions
    "strengths": [list],
    "weaknesses": [list]
  }

check_abstraction(world: World) -> AbstractionReport

  Purpose: Detect unnecessary concreteness
  Returns: {
    "abstraction_score": float,
    "concrete_names": [
        {"name": "John", "context": "...", "suggestion": "The Merchant"}
    ],
    "cultural_specifics": [
        {"element": "Christmas", "context": "...", "suggestion": "harvest festival"}
    ],
    "unnecessary_details": [list],
    "reasoning": str,  # why abstraction matters here
    "examples_of_good_abstraction": [list]
  }
```

**Design decisions:**
- All return structured, actionable feedback
- Agent can use anytime (self-eval is agent-initiated)
- Same tools used for external eval
- Not blockers, just signals

## Addressing Specific Issues

### Issue A: Agent Not Doing Deep Enough Research

**Multi-layered solution within bitter lesson constraints:**

#### Layer 1: Research Tool Guides Toward Depth
- Tool returns `depth_achieved` and `follow_up_questions`
- If shallow, suggests deeper angles
- Built into the tool itself
- Agent decides whether to pursue

#### Layer 2: System Prompt Clarification
```
When researching, aim for depth over breadth:
- Surface: Retrieving facts (not enough)
- Medium: Connecting concepts (better)
- Deep: Building models, finding non-obvious connections (goal)

After research, use assess_depth() to check. If you got "surface"
results, research() will suggest follow-up questions. Consider pursuing them.
```

#### Layer 3: Strong Examples in Prompt
```
Example of shallow research:
Query: "What is quantum entanglement?"
Finding: "Quantum entanglement is when particles are connected..."
Depth: Surface (just definition)

Example of deep research:
Query: "What is quantum entanglement?"
Finding: "Entanglement creates correlation without causation, which
challenges classical assumptions about locality. This connects to
information theory because... Implications for my world: if consciousness
works via entanglement, then..."
Depth: Deep (connections, implications, model-building)
```

#### Layer 4: Self-Correction Loop (Agent-Directed)
```
Agent workflow (self-directed):
1. Research topic
2. Assess depth (sees "surface" result)
3. Research tool suggests follow-ups
4. Agent decides: go deeper or move on
```

**Lean check:**
- ✅ Not prescribing "always do 3 research rounds"
- ✅ Not mandating "research must find 5 connections"
- ✅ Providing feedback mechanism
- ✅ Agent chooses strategy
- ✅ Will improve with better models (better judgment about when to go deeper)

### Issue B: Agent Using Random Names Despite System Prompt

**Why system prompt alone doesn't work:**
- Abstract instruction vs concrete examples
- Agent doesn't see the impact
- Easier to use names in the moment
- No feedback loop

**Multi-layered solution:**

#### Layer 1: Much Clearer System Prompt
```
CRITICAL: Do NOT use concrete names or cultural specifics.

❌ Bad: "John Smith runs a bakery in Boston during Christmas"
✅ Good: "A merchant operates a resource distribution point during
          the harvest period"

Why this matters:
- Concrete names anchor to our world, reducing universality
- Cultural specifics limit the world's independence
- Abstract roles maintain consistency better
- Easier to verify logical relationships with abstractions

Use roles, not names: "The Magistrate", "The Engineer"
Use abstract places: "The Central Hub", "The Border Region"
Use invented cultural elements: "The Renewal Ceremony", not "Christmas"
```

#### Layer 2: Strong Examples Throughout Prompt
```
When describing characters, use roles:
- "The Station Commander" not "Commander Jenkins"
- "The Dissenting Scientist" not "Dr. Sarah Chen"

When describing places, use function:
- "The Trading Nexus" not "New Shanghai"
- "The Restricted Zone" not "Area 51"

When describing culture, invent:
- "The Awakening" not "coming of age ceremony"
- "The Long Night" not "winter"
```

#### Layer 3: check_abstraction() Tool
- Agent can self-check before finalizing
- Surfaces specific instances of concreteness
- Provides suggestions for abstractions
- Explains reasoning
- Agent decides whether to revise

#### Layer 4: External Eval Includes Abstraction Score
- We check every output
- Track: does agent improve over time?
- Adjust prompts based on patterns

#### Layer 5: Two-Stage Generation (Optional, Not Mandatory)
```
Agent can choose to:
1. Generate rough draft (might have names)
2. Run check_abstraction()
3. Revise based on feedback

Not prescribed, but tool enables this workflow.
```

**Lean check:**
- ✅ Not blocking generation if names used
- ✅ Not forcing specific abstractions
- ✅ Providing clear guidance + feedback
- ✅ Agent can choose to self-correct
- ✅ Scales with better models (better judgment about abstraction)

## External Evaluation Setup

### What We Measure (Every Output)

```python
external_eval = {
    # Tier 1: Objective checks (fully automated)
    "consistency": {
        "world_consistent": bool,
        "contradiction_count": int,
        "contradictions": [list]
    },

    "complexity": {
        "entity_count": int,
        "rules_count": int,
        "relationship_count": int,
        "complexity_score": float
    },

    "abstraction": {
        "abstraction_score": float,
        "concrete_names_count": int,
        "cultural_specifics_count": int,
        "concrete_names": [list]
    },

    "structure": {
        "has_conflict": bool,
        "has_stakes": bool,
        "character_agency": bool,
        "follows_world_rules": bool
    },

    # Tier 2: Quality assessments (LLM-as-judge)
    "depth": {
        "research_depth": 1-5,
        "simulation_depth": 1-5,
        "reasoning": str
    },

    "quality": {
        "emotional_resonance": 1-5,
        "interestingness": 1-5,
        "originality": 1-5,
        "reasoning": str
    },

    # Tier 3: Process efficiency
    "process": {
        "actions_taken": int,
        "eval_tools_used": int,
        "redundant_actions": int,
        "self_corrections": int
    },

    # Tier 4: Comparative (across runs)
    "comparison": {
        "novelty_vs_baseline": float,
        "quality_vs_average": float,
        "efficiency_vs_average": float
    }
}
```

### How We Use External Eval

- Track trends over time
- Compare configurations (different prompts, tool sets)
- Identify what correlates with quality
- Adjust system based on findings
- **NOT** used to constrain agent during execution

**Lean check:**
- ✅ Measuring outcomes, not process compliance
- ✅ Both objective and qualitative metrics
- ✅ Comparative analysis to detect improvement
- ✅ Used to iterate system, not constrain agent

## System Architecture

```
Letta Agent
├─ System Prompt
│  ├─ Core philosophy (exploration, depth, abstraction)
│  ├─ Strong examples (good vs bad)
│  ├─ Tool descriptions
│  └─ NO prescribed workflows
│
├─ Action Tools (agent's capabilities)
│  ├─ save_world / load_world / diff_worlds
│  ├─ simulate_abm
│  └─ research
│
├─ Evaluation Tools (agent's self-assessment)
│  ├─ verify_consistency
│  ├─ assess_depth
│  ├─ check_novelty
│  ├─ evaluate_narrative
│  └─ check_abstraction
│
└─ Agent decides: what to do, when, and how

External Evaluation System (separate process)
├─ Runs same evaluation tools systematically
├─ Calculates aggregate metrics
├─ Compares across runs
├─ Identifies patterns
└─ Informs system iteration
```

### Information Flow

```
User: "Create a world about X"
  ↓
Agent: Uses action tools + evaluation tools
  - research, simulate, verify, assess, revise
  - Agent-initiated eval, self-directed workflow
  - Chooses what to do and when
  ↓
Agent: Produces final world + story
  ↓
External Eval: Measures quality + process
  - Runs same eval tools
  - Calculates metrics
  - Compares to baseline
  ↓
Human: Reviews results, adjusts system if needed
  - Updates prompts with better examples
  - Refines tool implementations
  - Adds new capabilities if patterns emerge
  ↓
Next iteration: Improved system that scales with better models
```

## Implementation Phases

### Phase 1: Core Infrastructure
```
□ Define data structures (World, SimulationResult, etc)
□ Implement world save/load/diff
□ Set up Letta agent scaffolding
□ Write lean system prompt (v1)
```

**Deliverable**: Agent can persist and compare worlds

### Phase 2: Action Tools
```
□ Implement research() tool
  - With depth feedback built in
  - Returns follow-up questions
  - Start with LLM knowledge, add real search if needed
□ Implement simulate_abm() tool
  - Natural language scenario input
  - Rich result format (narrative + data)
□ Wire tools to Letta agent
□ Test basic functionality
```

**Deliverable**: Agent can research and simulate

### Phase 3: Evaluation Tools
```
□ Implement verify_consistency()
  - Z3 integration under the hood
  - Clean interface returning contradictions
□ Implement assess_depth()
  - Works for research, simulation, world
  - Returns score + suggestions
□ Implement check_novelty()
  - Compare world states
  - Calculate information gain
□ Implement check_abstraction()
  - Detect names, cultural elements
  - Suggest abstractions with reasoning
□ Implement evaluate_narrative()
  - Structure checks (conflict, stakes, agency)
  - Quality assessment (LLM-as-judge)
  - Grounding verification
```

**Deliverable**: Agent can self-assess quality

### Phase 4: System Prompt Refinement
```
□ Add strong examples (good vs bad for each dimension)
□ Add depth guidance with concrete examples
□ Add abstraction guidance with concrete examples
□ Add tool usage hints (not rules, just suggestions)
□ Explain WHY for each guideline (not just WHAT)
□ Test on sample prompts, iterate based on behavior
```

**Deliverable**: Clear, example-rich system prompt

### Phase 5: External Evaluation System
```
□ Implement evaluation runner
  - Runs eval tools on outputs
  - Calculates aggregate metrics
  - Logs results
□ Set up tracking/storage
  - Store eval results per run
  - Enable time-series analysis
□ Create comparison system
  - Compare across runs
  - Identify trends
□ Build simple dashboard (optional)
  - Visualize metrics over time
  - Highlight patterns
```

**Deliverable**: Systematic quality measurement

### Phase 6: Testing & Iteration
```
□ Run agent on diverse test prompts
□ Collect external eval data (n=10-20 runs)
□ Analyze failure modes
  - Where does agent struggle?
  - Which eval tools does agent use/ignore?
  - Depth/abstraction issues still present?
□ Adjust prompts/tools based on findings
  - Add examples targeting failure modes
  - Refine tool feedback messages
  - Update eval criteria if needed
□ Compare to baseline (current DSF)
  - Quality comparison
  - Efficiency comparison
  - Identify improvements and regressions
□ Iterate until consistently better than baseline
```

**Deliverable**: Production-ready agent system

## Lean Checklist (Pre-Implementation)

Before implementing any feature, verify:

- [ ] **Necessity**: Is this tool necessary or nice-to-have?
- [ ] **Capability vs Prescription**: Does it enable capability or prescribe workflow?
- [ ] **Scalability**: Will it scale with better models?
- [ ] **Simplicity**: Is the interface as simple as possible?
- [ ] **Actionability**: Does it provide actionable feedback?
- [ ] **Agency**: Can agent choose whether/when to use it?
- [ ] **Outcomes**: Does it measure outcomes or compliance?

**Red flags that suggest over-engineering:**
- "Agent must do X before Y"
- "This validates that agent followed the process"
- "This ensures agent uses tool Z"
- "Agent needs permission to do X"
- "This gates access based on step number"

**Green flags that suggest good design:**
- "Agent can do X if they want"
- "This helps agent assess quality"
- "This provides feedback about outcomes"
- "Agent decides when to use this"
- "This enables new capabilities"

## Open Design Questions

### Q1: Should research() fetch real data or use LLM knowledge?
**Options:**
- Real fetch: More grounded, current info (but slower, more complex)
- LLM knowledge: Faster, cheaper (but potentially outdated)
- Hybrid: LLM + optional real search (more flexible)

**Recommendation**: Start with LLM knowledge, add real search if needed
- Reasoning: Simpler to implement, faster iteration
- Can add web search later if LLM knowledge insufficient

### Q2: Where does story generation happen?
**Options:**
- Separate tool: `generate_story(world)`
- Part of main loop: Agent writes story naturally in conversation
- Outside agent: Separate process after world creation

**Recommendation**: Agent writes story as part of main loop
- Reasoning: More natural, agent can interleave world-building and storytelling
- Agent can revise world based on story needs and vice versa

### Q3: How do we initialize the world?
**Options:**
- Agent starts from scratch (blank slate)
- User provides seed concept, agent builds from there
- Template/scaffold provided (some structure pre-defined)

**Recommendation**: User provides seed concept, agent builds
- Reasoning: Balances agency and direction
- User provides intent, agent figures out how

### Q4: Should we have explicit "revise_world" tool?
**Options:**
- Explicit tool: More trackable, clear action
- Direct editing: Agent just modifies world naturally
- Both: Agent chooses approach

**Recommendation**: No separate tool, agent edits world naturally
- Reasoning: World is just data, agent can modify directly
- Don't create unnecessary abstractions
- If we need tracking, that's external logging concern

### Q5: How much world structure do we prescribe?
**Options:**
- Freeform: Agent defines structure entirely
- Schema: Must have {entities, rules, relationships}
- Validation: Check for required elements

**Recommendation**: Light schema, flexible contents
- Reasoning: Need parseable structure for tools (diff, verify, etc)
- But don't prescribe what entities/rules should exist
- Schema is infrastructure, not creative constraint

**Example schema:**
```python
World = {
    "concept": str,  # high-level premise
    "entities": [list],  # any structure agent defines
    "rules": [list],  # any structure agent defines
    "relationships": [list],  # optional
    "metadata": dict  # timestamps, versions, etc
}
```

## Success Criteria

We'll know this system works when:

1. **Quality**: Worlds are logically consistent, deeply researched, abstractly designed
   - Zero contradictions (or agent catches and fixes them)
   - Research connects non-obvious concepts
   - No concrete names/cultural elements (or agent self-corrects)

2. **Agency**: Agent self-directs effectively
   - Uses eval tools without being told
   - Goes deeper when appropriate
   - Pivots when stuck

3. **Efficiency**: Reaches quality outcomes reliably
   - Consistent good results across prompts
   - No wasted cycles on shallow work
   - Self-corrects before finalizing

4. **Scalability**: Better models = better results automatically
   - No changes needed to leverage model improvements
   - System constraints don't limit capability
   - Tools remain useful with more capable models

5. **Comparison**: Outperforms current DSF
   - Higher consistency scores
   - Deeper research (measured objectively)
   - Better abstraction (fewer concrete elements)
   - More compelling stories (human eval)

## Next Steps

1. **Review this plan** - Anything missing? Over-engineered?
2. **Save this document** - Reference for implementation
3. **Start Phase 1** - Core infrastructure and data structures
4. **Iterate rapidly** - Build, test, refine
5. **Stay lean** - Add only what's needed, remove what doesn't work

Remember: The goal is a system that scales with model capability, not one that constrains it. When in doubt, choose tools over workflows, evaluation over prescription.
