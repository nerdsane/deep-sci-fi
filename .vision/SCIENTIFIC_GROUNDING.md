# Scientific Grounding Philosophy

**Type:** STABLE
**Created:** 2026-01-09
**Last Updated:** 2026-01-09

---

## Overview

Deep Sci-Fi is distinguished from generic fiction by its commitment to scientific rigor. This document defines what "scientifically-grounded" means for worlds and stories, and the evaluation approach to achieve it.

---

## Core Philosophy

> "Science fiction is the literature of ideas. The science must be plausible enough that readers accept the world, then the ideas can explore consequences."

**Hard sci-fi is not required.** What IS required:
- Internally consistent rules
- Acknowledged speculation (not handwaving)
- Consequences that follow from premises
- Grounding that improves with better models

---

## What Makes a World "Scientifically Grounded"

### 1. Explicit Rules System

Every world defines rules with:
- **Scope**: Universal, local, or conditional
- **Certainty**: Tentative, established, or fundamental
- **Testability**: Can be validated in stories

**Outcome:** Readers understand the constraints; stories can explore them.

### 2. Causal Chains from Present to Future

Technology and society don't appear from nowhere. Good worlds can trace:
- Present-day research that enables future tech
- Prerequisites and milestones
- Scientific basis (even if speculative)

**Outcome:** The future feels like an extrapolation, not magic.

### 3. Cross-Domain Consistency

Changes in one domain cascade to others:
- Physics → Technology → Economics → Social structures
- A world with fusion power must account for energy economics
- FTL travel must address communication and trade implications

**Outcome:** No isolated "cool tech" that ignores consequences.

### 4. Acknowledged Speculation

Not everything must be hard science. The key is honesty:
- **Hard science**: Based on current knowledge
- **Plausible extrapolation**: Logical extension of current trends
- **Hard speculation**: Requires unknown physics (acknowledged)
- **Fantasy**: No scientific basis (also acknowledged)

**Outcome:** Readers know what's real vs. imagined.

---

## Evaluation Tools (Available to Agents)

### Assessment Tools

| Tool | Purpose |
|------|---------|
| `assess_scientific_grounding` | Evaluate plausibility + justification quality |
| `trace_temporal_causality` | Generate causal chains from today → future |
| `validate_implications` | Find what MUST logically follow from premises |
| `cross_domain_consistency` | Validate cascading effects across domains |
| `adversarial_probe` | Challenge world elements to find gaps |

### Story Coherence Tools

| Tool | Purpose |
|------|---------|
| `add_event` | Build canonical event graph for stories |
| `validate_coherence` | Check multi-perspective narrative consistency |

**Note:** These tools are available but not mandatory. Agents choose when/if to use them. Better models will use them more strategically.

---

## What This Is NOT

### NOT a Physics Simulator
We don't symbolically verify F=ma calculations. LLMs reason about plausibility holistically.

### NOT Brittle Rules
"Speed of light is 299792458 m/s" is less useful than "FTL requires exotic matter because..."

### NOT Blocking
Tools provide information; agents decide action. No gates that prevent creativity.

### NOT Prescriptive
"Use validate_implications before saving" violates the Bitter Lesson. Agents use tools when valuable.

---

## Success Criteria for Grounded Worlds

| Criterion | Measurement |
|-----------|-------------|
| Internal consistency | No major contradictions (check_logical_consistency) |
| Causal grounding | Technology traceable to present research |
| Domain coherence | Cross-domain implications addressed |
| Speculation acknowledged | Classifications assigned honestly |
| Depth over breadth | Rules have "why" not just "what" |

---

## Story Coherence Model

Stories in grounded worlds must maintain:

### 1. Physical Consistency
What happens must follow world rules. No "the ship just went faster than light" in a world where FTL requires fold drives.

### 2. Information Consistency
Characters only know what they've learned. Multi-perspective stories require tracking who knows what.

### 3. Temporal Consistency
Events must be causally ordered. No effects before causes.

### 4. Perspective Reliability
Each viewpoint character's perception is valid but limited. Unreliable narrators are allowed if consistent.

---

## The "Iceberg" World Model

Professional sci-fi authors build deep foundations:

### Surface (10%)
- Opening scene
- Visible elements
- What readers see first

### Foundation (90%)
- Core premise
- Rules with scientific basis
- Technology specifications
- History, geography, culture
- Working notes and unresolved questions

**Outcome:** Stories reveal depth organically. The world feels real because it IS detailed underneath.

---

## Scaling with Better Models

This approach improves with AI advancement:

| What Scales | Why |
|-------------|-----|
| Causal reasoning depth | Better models trace longer chains |
| Cross-domain synthesis | Better models connect more domains |
| Contradiction detection | Better models catch subtle inconsistencies |
| Creative extrapolation | Better models imagine more novel consequences |

| What Doesn't Scale | Why |
|--------------------|-----|
| Hard-coded physics rules | Brittle, incomplete |
| Mandatory tool sequences | Constrains exploration |
| Fixed plausibility thresholds | Arbitrary limits |

---

## Remember

> "The goal is worlds that reward scrutiny, not worlds that pass tests."

Scientific grounding serves storytelling, not the other way around. A grounded world enables deeper exploration of ideas. The tools help achieve that, but the goal is always compelling, coherent fiction.
