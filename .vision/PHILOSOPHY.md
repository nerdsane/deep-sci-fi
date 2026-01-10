# Agent Design Philosophy

**Type:** STABLE
**Created:** 2026-01-09
**Last Updated:** 2026-01-09

---

## Core Principle

**Tools over workflows. Evaluation over prescription. Scale with better models.**

Methods that leverage computation and learning scale better than methods that bake in human knowledge about "the right way" to do things. (The Bitter Lesson)

---

## Key Distinctions

### Tools vs. Prescriptions

**Providing Tools (Good):**
- "You can save worlds as JSON with these fields"
- "You have tools: simulation, verification, world save/load"
- "You can run simulations to see emergent behavior"

**Prescribing Workflows (Bad):**
- "After every simulation, save world in this exact format"
- "First simulate, then verify, then research"
- "Always use tool X with these parameters"

**The Line:** Giving a tool != prescribing its use

### Self-Eval vs. External Eval

**Agent Self-Evaluation:**
- Purpose: Steering mechanism *during* execution
- Example: "Did this simulation reveal anything non-obvious?"
- Agent decides action based on self-assessment

**External Evaluation:**
- Purpose: Measure if the *system* is working
- Example: "Did the final world have contradictions?"
- Used to iterate on prompts, tools, eval criteria
- Agent doesn't see this - it's meta-level

---

## The Spectrum

### Scales with Better Models

- Diverse tools (simulation, verification, search)
- Objective quality criteria
- Self-eval prompts that teach critical thinking
- Examples (few-shot learning)
- Rich toolbox with more options

### Neutral

- Standardized data formats (World JSON structure)
- Tool interfaces/APIs
- Infrastructure (save/load mechanisms)

### Fights Better Models

- Hard-coded sequences ("First X, then Y, then Z")
- Brittle rules ("Always use tool X for problem Y")
- Step-based constraints
- Fixed parameters
- Prescribed workflows

---

## Unified Evaluation Model

Agent and system use THE SAME evaluation tools:

```
Agent has: verify_consistency(), assess_depth(), check_abstraction()
Agent chooses when to use them
System runs same tools systematically
System measures: quality of outputs + agent's use of eval tools
```

This is elegant because:
- Not prescribing when to evaluate
- Fair: only evaluating on criteria agent could check
- Transparent: agent knows what quality means
- Scalable: better models use eval tools more strategically

---

## Practical Guidelines

### What to Build

1. **Rich toolbox** - Action tools + evaluation tools
2. **Self-eval prompts** - "What did this reveal?" "Is this non-obvious?"
3. **Quality rubrics** - Examples of deep vs. shallow work
4. **Standard formats** - World schema for interoperability

### What NOT to Build

1. Mandatory sequences
2. Hard-coded decision trees
3. "Always use X for Y" rules
4. Step counters that gate capabilities

### External Evaluation (Human-Level)

1. Final output quality (world coherence, story compelling)
2. Intermediate quality (simulations useful, research deep)
3. Efficiency (did agent waste cycles)
4. Use results to tune prompts, add/remove tools

---

## The Real Test

> "If Claude Opus 5 came out, would my system get better automatically, or would my constraints hold it back?"

- Better model with toolbox -> better tool choices, deeper self-eval
- Better model with hard-coded workflows -> stuck with your rules

---

## Remember

The goal is a system that gets better as models improve, not one that constrains what better models can do.

**Tools, not prescriptions. Evaluation, not workflows.**
