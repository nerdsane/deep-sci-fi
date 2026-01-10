# Generic Eval + ABM Tools for Letta Platform

**Design Philosophy**: Light, generalizable, cognizant of bitter lesson
**Target**: Add to Letta platform (available to all agents)
**Reference Implementation**: DSF agent shows how to use them

## Core Principles (Bitter Lesson)

✅ **Tools, not workflows** - Agent chooses when/if to use
✅ **Parameters, not hard-coding** - User provides criteria/rubric
✅ **Feedback, not commands** - Return information, agent decides action
✅ **Scales with better models** - Better judgment, not more rules

❌ **No prescriptive workflows** - No "first eval, then iterate"
❌ **No rigid thresholds** - No "score < 0.7 = bad"
❌ **No domain assumptions** - Works for any content type

---

## Part 1: Evaluation Tools

### Tool 1: `assess_output_quality`

**Purpose**: Generic quality assessment against custom rubric (LLM-as-judge)

**Why it's generalizable:**
- Works for ANY content type (text, code, JSON, structured data)
- User provides the rubric (no baked-in assumptions)
- Agent decides when to use it

```python
async def assess_output_quality(
    content: str,
    rubric: str,
    content_type: str = "text"
) -> dict:
    """
    Evaluate quality of content against a custom rubric.

    Generic tool for ANY agent to self-assess their work.
    Agent provides content and quality criteria (rubric).
    Returns structured feedback.

    Args:
        content: The output to evaluate (text, JSON, code, etc.)
        rubric: Quality criteria as natural language description
        content_type: Hint for parsing (text, json, python, markdown)

    Returns:
        {
            "score": float (0.0-1.0),
            "reasoning": str,
            "strengths": [str],
            "improvements": [str],
            "meets_criteria": bool
        }

    Examples:
        # Writing assistant
        assess_output_quality(
            content=draft,
            rubric="Clear, concise, engaging. No jargon. Active voice.",
            content_type="text"
        )

        # Code agent
        assess_output_quality(
            content=code,
            rubric="Clean, readable, follows PEP8. Has docstrings. Handles errors.",
            content_type="python"
        )

        # DSF agent (reference implementation)
        assess_output_quality(
            content=json.dumps(world),
            rubric="Logically consistent. Abstract roles (not names). Deep research evident.",
            content_type="json"
        )
    """
    # Implementation: LLM-as-judge with structured output

    prompt = f"""
Evaluate this {content_type} content against the provided quality rubric.

CONTENT:
{content[:2000]}  # Truncate if too long

QUALITY RUBRIC:
{rubric}

Evaluate on a scale of 0.0 (fails rubric) to 1.0 (exceeds rubric).

Return JSON:
{{
    "score": float,
    "reasoning": "brief explanation of score",
    "strengths": ["what meets/exceeds rubric"],
    "improvements": ["specific suggestions for what doesn't meet rubric"],
    "meets_criteria": bool
}}
"""

    # Call LLM (use fast model like haiku for efficiency)
    result = await call_llm(prompt, model="claude-haiku-4", json_mode=True)

    return result
```

**Bitter Lesson Check:**
- ✅ Generic (works for any content + rubric)
- ✅ Parameterized (rubric is input, not hard-coded)
- ✅ Scales (better models = better judgment)
- ✅ Not prescriptive (just returns feedback, agent decides)

---

### Tool 2: `check_logical_consistency`

**Purpose**: Find contradictions in structured content

**Why it's generalizable:**
- Works for any structured data
- Optional explicit rules to check against
- Agent decides what to do with contradictions

```python
async def check_logical_consistency(
    content: str,
    rules: list[str] = None,
    format: str = "text"
) -> dict:
    """
    Check content for logical contradictions.

    Generic tool for ANY agent working with structured information.
    Can provide explicit rules or let LLM find implicit contradictions.

    Args:
        content: Content to check (text, JSON, etc.)
        rules: Optional explicit rules to verify against
        format: Format hint (text, json, yaml)

    Returns:
        {
            "consistent": bool,
            "contradictions": [
                {
                    "elements": [str],  # What contradicts
                    "description": str,  # Why it contradicts
                    "severity": "minor" | "major"
                }
            ],
            "checks_performed": int
        }

    Examples:
        # Contract review agent
        check_logical_consistency(
            content=contract_text,
            rules=[
                "Payment terms must be <= 90 days",
                "No conflicting clauses about termination"
            ],
            format="text"
        )

        # Data validation agent
        check_logical_consistency(
            content=json.dumps(schema),
            rules=[
                "All foreign keys must reference existing tables",
                "No circular dependencies"
            ],
            format="json"
        )

        # DSF agent (reference implementation)
        check_logical_consistency(
            content=json.dumps(world),
            format="json"
        )
    """
    contradictions = []

    # 1. If explicit rules provided, check them first (algorithmic)
    if rules:
        for rule in rules:
            violation = check_rule_violation(content, rule, format)
            if violation:
                contradictions.append({
                    "elements": [rule],
                    "description": violation,
                    "severity": "major"
                })

    # 2. LLM check for implicit contradictions
    prompt = f"""
Analyze this {format} content for logical contradictions.

CONTENT:
{content[:2000]}

{"EXPLICIT RULES TO CHECK:" if rules else "Look for implicit contradictions."}
{chr(10).join(f"- {r}" for r in rules) if rules else ""}

Find contradictions where:
- Statement A conflicts with statement B
- Property X is impossible given constraint Y
- Cause-effect relationships don't hold

Return JSON:
{{
    "contradictions": [
        {{
            "elements": ["element1", "element2"],
            "description": "why they contradict",
            "severity": "minor" or "major"
        }}
    ]
}}
"""

    result = await call_llm(prompt, model="claude-sonnet-4", json_mode=True)
    contradictions.extend(result["contradictions"])

    return {
        "consistent": len(contradictions) == 0,
        "contradictions": contradictions,
        "checks_performed": len(rules) + 1 if rules else 1
    }
```

**Bitter Lesson Check:**
- ✅ Generic (works for any structured content)
- ✅ Parameterized (rules are optional input)
- ✅ Scales (better models find subtler contradictions)
- ✅ Not prescriptive (returns findings, agent decides)

---

### Tool 3: `compare_versions`

**Purpose**: Compare two versions to measure change/improvement

**Why it's generalizable:**
- Works for any content that has versions
- User specifies what to compare
- Useful for iterative refinement in any domain

```python
async def compare_versions(
    current: str,
    previous: str,
    comparison_criteria: str = "quality, novelty, accuracy"
) -> dict:
    """
    Compare two versions of content to measure improvement.

    Generic tool for iterative refinement. Agent can assess
    whether their revision improved or regressed.

    Args:
        current: Current version
        previous: Previous version
        comparison_criteria: What to compare (comma-separated)

    Returns:
        {
            "improved": bool,
            "changes": [str],  # What changed
            "better_aspects": [str],  # What improved
            "worse_aspects": [str],  # What regressed
            "recommendation": "keep_current" | "revert" | "iterate_more"
        }

    Examples:
        # Writing agent
        compare_versions(
            current=revised_draft,
            previous=first_draft,
            comparison_criteria="clarity, completeness, tone"
        )

        # Code agent
        compare_versions(
            current=refactored_code,
            previous=original_code,
            comparison_criteria="readability, performance, test_coverage"
        )

        # DSF agent (reference implementation)
        compare_versions(
            current=json.dumps(world_v2),
            previous=json.dumps(world_v1),
            comparison_criteria="consistency, depth, abstraction"
        )
    """
    # 1. Algorithmic diff (what changed structurally)
    changes = compute_structural_diff(current, previous)

    # 2. LLM evaluation (quality comparison)
    prompt = f"""
Compare these two versions on: {comparison_criteria}

PREVIOUS VERSION:
{previous[:1000]}

CURRENT VERSION:
{current[:1000]}

CHANGES DETECTED:
{json.dumps(changes, indent=2)}

For each criterion in "{comparison_criteria}", assess if current version is:
- Better (improved)
- Worse (regressed)
- Same (no change)

Return JSON:
{{
    "improved": bool (overall assessment),
    "better_aspects": [list what improved],
    "worse_aspects": [list what regressed],
    "recommendation": "keep_current" or "revert" or "iterate_more"
}}
"""

    result = await call_llm(prompt, model="claude-sonnet-4", json_mode=True)

    return {
        "improved": result["improved"],
        "changes": changes,
        "better_aspects": result["better_aspects"],
        "worse_aspects": result["worse_aspects"],
        "recommendation": result["recommendation"]
    }
```

**Bitter Lesson Check:**
- ✅ Generic (works for any versioned content)
- ✅ Parameterized (criteria are input)
- ✅ Scales (better models have better judgment)
- ✅ Not prescriptive (returns comparison, agent decides)

---

## Part 2: Agent-Based Modeling (ABM) Tool

### Tool: `simulate_scenario`

**Purpose**: Generic simulation of scenarios with emergent behavior

**Why it's generalizable:**
- Works for ANY domain (not just sci-fi)
- Agent describes scenario in natural language
- Returns emergent behaviors (not prescribed outcomes)
- No hard-coded parameters

```python
async def simulate_scenario(
    scenario_description: str,
    context: dict = None,
    focus: str = "emergent_behaviors"
) -> dict:
    """
    Simulate a scenario and observe emergent behavior.

    Generic ABM simulation for ANY domain. Agent describes what
    to simulate in natural language. Returns emergent patterns
    and unexpected interactions.

    Args:
        scenario_description: Natural language description of what to simulate
        context: Optional structured context (world rules, entities, etc.)
        focus: What to observe ("emergent_behaviors", "edge_cases", "interactions")

    Returns:
        {
            "outcome": str,  # Narrative description of what happened
            "emergent_behaviors": [str],  # Unexpected patterns that emerged
            "interactions": [str],  # How elements interacted
            "surprises": [str],  # Non-obvious results
            "suggests": [str]  # What this reveals about the scenario
        }

    Examples:
        # Economics agent
        simulate_scenario(
            scenario_description="100 buyers and 50 sellers trading widgets. "
                                 "Buyers value widgets differently. "
                                 "Sellers have different costs.",
            focus="price_discovery"
        )

        # Social dynamics agent
        simulate_scenario(
            scenario_description="Network of 200 people. Information spreads "
                                 "through connections. Some people are influencers.",
            focus="information_spread"
        )

        # Urban planning agent
        simulate_scenario(
            scenario_description="Traffic flows through 10 intersections. "
                                 "Some lights are synchronized, others random.",
            focus="congestion_patterns"
        )

        # DSF agent (reference implementation)
        simulate_scenario(
            scenario_description="Station with neural interfaces. 50 people "
                                 "trying to communicate emotional states. "
                                 "Some interfaces malfunction randomly.",
            context=world,
            focus="emergent_behaviors"
        )
    """
    # Parse scenario into simulation parameters (LLM does this)

    setup_prompt = f"""
You are a simulation designer. Convert this scenario into simulation parameters.

SCENARIO:
{scenario_description}

CONTEXT (if provided):
{json.dumps(context, indent=2) if context else "None"}

Extract:
1. Agent types (what entities exist)
2. Agent behaviors (how they act)
3. Environment rules (constraints)
4. Initial conditions (starting state)
5. What to measure (based on focus: {focus})

Return JSON simulation config.
"""

    sim_config = await call_llm(setup_prompt, model="claude-sonnet-4", json_mode=True)

    # Run lightweight ABM simulation
    # (This would use a simple ABM engine like Mesa or custom implementation)
    sim_results = run_abm_simulation(sim_config, steps=50)

    # Analyze results for emergent behaviors (LLM synthesizes)
    analysis_prompt = f"""
Analyze these simulation results for emergent patterns.

SCENARIO: {scenario_description}

SIMULATION DATA:
{json.dumps(sim_results, indent=2)[:1500]}

Focus on: {focus}

What emerged that wasn't explicitly programmed?
What interactions were non-obvious?
What does this reveal about the scenario?

Return JSON:
{{
    "outcome": "narrative description",
    "emergent_behaviors": [list unexpected patterns],
    "interactions": [list notable interactions],
    "surprises": [list non-obvious results],
    "suggests": [list what this reveals]
}}
"""

    analysis = await call_llm(analysis_prompt, model="claude-sonnet-4", json_mode=True)

    return analysis
```

**Bitter Lesson Check:**
- ✅ Generic (works for any domain via natural language)
- ✅ Not prescriptive (agent describes scenario, no hard-coded params)
- ✅ Scales (better models = better scenario understanding + analysis)
- ✅ Emergent (focuses on behaviors that emerge, not prescribed outcomes)

**Implementation Notes:**
- Use lightweight ABM engine (Mesa, or custom)
- Keep simulations short (50-100 steps) for speed
- LLM translates natural language → sim config
- LLM synthesizes results → emergent insights
- No hard-coded agent counts, step limits, etc.

---

## Where to Add in Letta Platform

```
letta/
├── functions/function_sets/
│   ├── evaluations.py          # ⭐ NEW: Add eval tools
│   │   - assess_output_quality()
│   │   - check_logical_consistency()
│   │   - compare_versions()
│   │
│   └── simulation.py           # ⭐ NEW: Add ABM tool
│       - simulate_scenario()
│
└── services/tool_executor/
    ├── evaluation_tool_executor.py   # ⭐ NEW: Executor for eval tools
    └── simulation_tool_executor.py   # ⭐ NEW: Executor for ABM tool
```

**Why these are platform tools:**
1. **Broadly useful** - Any agent can use them (not DSF-specific)
2. **Lightweight** - No heavy dependencies
3. **Parameterized** - Flexible via inputs, not hard-coded
4. **Self-contained** - Don't require external services (beyond LLM)

---

## How DSF Agent Uses Them (Reference Implementation)

**DSF agent's system prompt:**

```
You have access to evaluation tools:
- assess_output_quality(content, rubric, type)
- check_logical_consistency(content, rules, format)
- compare_versions(current, previous, criteria)

And simulation:
- simulate_scenario(description, context, focus)

USE THEM WHEN YOU JUDGE IT'S HELPFUL.

For DSF worlds, useful rubrics include:
- "Logically consistent, abstract roles, deeply researched"
- "Non-obvious emergent behaviors from rules"
- "Conceptual connections beyond surface facts"

You decide WHEN to eval and WHAT to simulate.
No prescribed workflow.
```

**Example DSF workflow (agent-directed, not prescribed):**

```
Agent: Creates initial world
Agent: check_logical_consistency(world) → finds contradiction
Agent: Fixes contradiction
Agent: assess_output_quality(world, rubric="consistent, abstract, deep")
       → Gets score 0.6, suggestions to go deeper
Agent: simulate_scenario("station with neural interfaces malfunction")
       → Discovers emergent behavior
Agent: Updates world based on simulation insights
Agent: compare_versions(updated, original, "depth, novelty")
       → Sees improvement, decides to continue
```

Agent decides the flow, not a prescribed sequence.

---

## Implementation Phases

### Phase 1: Eval Tools (Week 1-2)
- [ ] Implement `assess_output_quality()` with LLM-as-judge
- [ ] Implement `check_logical_consistency()` with hybrid approach
- [ ] Implement `compare_versions()` with diff + LLM
- [ ] Add to `/letta/functions/function_sets/evaluations.py`
- [ ] Create `evaluation_tool_executor.py`
- [ ] Test with diverse content types (text, code, JSON)

### Phase 2: ABM Tool (Week 2-3)
- [ ] Implement `simulate_scenario()` with Mesa or custom ABM
- [ ] LLM scenario → config translation
- [ ] Lightweight simulation runner (50-100 steps)
- [ ] LLM results → emergent behaviors synthesis
- [ ] Add to `/letta/functions/function_sets/simulation.py`
- [ ] Create `simulation_tool_executor.py`
- [ ] Test with diverse scenarios (economics, social, traffic, DSF)

### Phase 3: DSF Reference Implementation (Week 3-4)
- [ ] Create DSF agent that uses these tools
- [ ] Document DSF as reference in Letta docs
- [ ] Show: "Here's how a world-building agent uses eval + ABM tools"
- [ ] Demonstrate agent-directed usage (no prescribed workflow)
- [ ] Measure: Does DSF agent produce better worlds with these tools?

### Phase 4: Polish & Docs (Week 4)
- [ ] Write tool documentation
- [ ] Add examples for different domains
- [ ] Performance optimization
- [ ] Submit PR to Letta repo

---

## Success Criteria

**These tools are successful if:**

1. **Broadly useful** - Other Letta users adopt them for non-DSF use cases
2. **Lightweight** - Fast enough for real-time agent use
3. **Scales** - Better models → better evaluations, no code changes needed
4. **Not prescriptive** - Agents use them flexibly, not in rigid workflows
5. **DSF proves value** - DSF agent produces measurably better worlds

**Metrics:**
- Adoption: # of non-DSF agents using these tools
- Performance: Eval latency < 2s, simulation < 5s
- Quality: DSF worlds score higher on consistency, depth, abstraction
- Flexibility: Agents use tools in diverse, non-prescribed ways

---

## Open Questions

### Q1: How heavyweight should ABM simulation be?

**Options:**
- Lightweight (50 steps, 10-50 agents, fast but less detailed)
- Medium (100 steps, 50-200 agents, balanced)
- Heavy (500+ steps, 500+ agents, slow but detailed)

**Recommendation**: Start lightweight, let agent decide if they want to run longer
- Default: 50 steps, up to 100 agents
- Agent can call multiple times for different scenarios
- Fast > comprehensive (agent can iterate)

### Q2: Should eval tools be synchronous or async?

**Options:**
- Sync (blocking, simple)
- Async (non-blocking, agent continues while eval runs)

**Recommendation**: Sync for now
- Simpler implementation
- Evals are fast enough (1-3s)
- Agent waits for feedback before continuing
- Can add async later if needed

### Q3: Where does simulation engine live?

**Options:**
- Built into Letta (Mesa dependency)
- External service (HTTP API)
- LLM-only (no real simulation, just LLM reasoning)

**Recommendation**: Built-in with Mesa
- Lightweight dependency
- Fast (local execution)
- Real emergence (not just LLM hallucination)
- Can add external option later for heavy sims

---

## Next Steps

1. **Review this design** - Does it follow bitter lesson? Generalizable enough?
2. **Start with eval tools** - Easier to implement, broadly useful
3. **Test with multiple domains** - Code review, writing, data validation
4. **Add ABM tool** - Once eval tools working
5. **Build DSF reference** - Show how to use them together
6. **Submit to Letta** - PR with documentation and examples
