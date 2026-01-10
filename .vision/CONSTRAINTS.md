# TigerStyle Constraints

**Type:** STABLE
**Created:** 2026-01-09
**Last Updated:** 2026-01-09

---

## Overview

Non-negotiable principles for development on this project. Inspired by TigerBeetle's TigerStyle and FoundationDB's simulation-first approach.

These are OUTCOMES to achieve, not prescriptions for HOW to achieve them.

---

## Core Constraints

### 1. Tests Prove It Works

Every task requires tests that demonstrate the feature works as intended.

**Outcome:** Code changes have corresponding tests
**NOT:** "Write tests using this exact pattern"

### 2. No Placeholders in Production

Code that appears to work but doesn't is worse than code that fails.

**Outcome:** No TODO, FIXME, HACK, stub functions, or silent failures
**NOT:** "Run /no-cap after every commit"

### 3. Vision Alignment

Changes should align with project vision and constraints.

**Outcome:** Work matches the documented direction
**NOT:** "Re-read vision files every 10 tool calls"

### 4. CI Must Pass

The continuous integration pipeline is the source of truth for code health.

**Outcome:** All CI jobs green before merge
**NOT:** "Run these specific commands in this order"

### 5. Quality Over Speed

Take time to do it right. Rushing creates technical debt.

**Outcome:** Well-designed, maintainable code
**NOT:** "Always follow this code style guide"

### 6. Explicit Over Implicit

State assumptions clearly. Handle errors explicitly.

**Outcome:** No silent failures, no hidden state
**NOT:** "Use try-catch with this pattern"

---

## Development Process Constraints

### Planning

- Non-trivial tasks should have a plan before implementation
- Plans document decisions and rationale
- Plans are updated as understanding evolves

### Implementation

- Read before writing (understand existing code)
- Make the minimal change needed
- Don't over-engineer for hypothetical future requirements

### Verification

- Tests pass
- Typecheck passes
- Linting passes
- No regressions

### Completion

- Task is complete when verification passes
- Documentation is updated if needed
- Changes are committed with clear messages

---

## What These Constraints Enable

- **Confidence:** Tests prove features work
- **Maintainability:** No hidden landmines
- **Collaboration:** Clear documentation of decisions
- **Evolution:** System can grow without breaking

---

## Anti-Patterns

These violate the spirit of the constraints:

| Anti-Pattern | Why It's Bad |
|--------------|--------------|
| "Tests pass but feature is broken" | Tests don't prove the right thing |
| "TODO: fix later" | Placeholder that becomes permanent |
| "It works on my machine" | Not reproducible |
| "I'll add tests after" | Tests often never get added |
| "We can refactor later" | Technical debt compounds |

---

## Enforcement

Constraints are enforced through:

1. **Pre-commit hooks** - Run tests, typecheck
2. **CI pipeline** - Automated verification
3. **Code review** - Human verification of quality
4. **Evals** - Quality metrics for agent-generated content

Enforcement focuses on **outcomes**, not **process compliance**.
