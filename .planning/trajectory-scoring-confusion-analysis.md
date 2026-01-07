# Trajectory Scoring Confusion Analysis

**Date:** 2026-01-02
**Issue:** UI shows "success" but outcome_score is 0.4-0.5 - seems contradictory

---

## Root Cause: Two Different Concepts with Confusing Names

There are **TWO separate fields** measuring different things:

### 1. `outcome.type` (Heuristic - Execution Status)

**Location:** `trajectory.data.outcome.type`
**Set by:** TrajectoryConverter (heuristic rules)
**Values:** `"success"`, `"partial_success"`, `"failure"`, `"error"`
**Measures:** **Did the run complete without errors?**

```python
# letta/services/trajectory_converter.py:214-217
if run.status == "completed":
    outcome_type = "success"  # ← Simple boolean: no errors
    confidence = 0.7
    reasoning.append("Run completed successfully")
```

**Logic:**
- Run status = "completed" → `"success"`
- Run status = "failed" → `"failure"`
- Stop reason = "max_tokens" → `"partial_success"`
- Errors occurred → `"error"`

### 2. `outcome_score` (LLM Evaluation - Learning Value)

**Location:** `trajectory.outcome_score` (top-level field)
**Set by:** TrajectoryProcessor (LLM-based evaluation)
**Values:** `0.0-1.0` (float)
**Measures:** **How valuable is this trajectory for continual learning?**

```python
# letta/services/trajectory_processing.py:91-120
Scoring criteria (weighted):
1. INTERACTION DEPTH (35%): Multi-turn dialogue, refinement, engagement
2. TASK COMPLEXITY (30%): Novel/challenging vs routine/trivial
3. TOOL USAGE (20%): Rich tool use, sophisticated capabilities
4. LEARNING VALUE (15%): Useful reference case, demonstrates patterns
```

**Logic:**
- Single-turn simple task → 0.4-0.5 (mediocre learning value)
- Multi-turn complex problem-solving → 0.8-0.9 (high learning value)
- No interaction or failed → 0.1-0.3 (low learning value)

---

## Example: Why "Success" Can Have Low Score

**Trajectory:** agent-4a83769e-5194-458a-8ca1-9a1151f64f07 trajectory-5e67a0c8...

```json
{
  "data": {
    "outcome": {
      "type": "success",        // ← Run completed without errors
      "confidence": 0.8,
      "reasoning": ["Run completed successfully", "Agent naturally ended turn"]
    }
  },
  "outcome_score": 0.5,           // ← Mediocre learning value
  "score_reasoning": "The trajectory consists of a single turn with a detailed response from the assistant, but lacks multi-turn interaction that would indicate deeper engagement or iterative refinement. While the task demonstrates some complexity in presenting creative worlds, the absence of user follow-up questions or tool usage limits its learning value, resulting in a mediocre score."
}
```

**Translation:**
- ✅ **Execution succeeded:** Agent completed the task, no errors
- ❌ **Learning value mediocre:** Single turn, no complex problem-solving, no tool usage

---

## Why This Is Confusing

| Issue | Impact |
|-------|--------|
| **Naming collision** | "success" (outcome.type) vs "0.5 score" sounds contradictory |
| **UI shows outcome.type** | Users see "success" prominently but not the score context |
| **Different purposes** | Execution status ≠ learning value, but both called "outcome" |
| **Binary vs spectrum** | "success/failure" is binary, score is nuanced 0-1 spectrum |

**User mental model:**
> "Success = high score, right?"

**Reality:**
> "Success = completed without errors. Score = learning value (may be low even for 'success')"

---

## Real-World Examples

### Example 1: High Execution Success, Low Learning Value
```
outcome.type: "success"
outcome_score: 0.4
Scenario: Agent answered a simple factual question in one turn
Why: Task completed ✅, but trivial interaction with no learning value
```

### Example 2: Execution Failed, High Learning Value
```
outcome.type: "error"
outcome_score: 0.8
Scenario: Multi-turn debugging session that hit API timeout after deep investigation
Why: Run failed ❌, but rich problem-solving with high learning value
```

### Example 3: High Both
```
outcome.type: "success"
outcome_score: 0.9
Scenario: Complex multi-turn story generation with iteration, tool usage, refinement
Why: Task completed ✅ AND rich, valuable interaction
```

---

## Proposed Solutions

### Option 1: Rename `outcome.type` to `execution_status` ⭐ RECOMMENDED

**Change the field name** to make it clear it's about execution, not quality.

```python
# Before (confusing)
{
  "outcome": {
    "type": "success",  # ← Sounds like it means "high quality"
    "confidence": 0.8
  }
}

# After (clear)
{
  "execution": {
    "status": "completed",  # ← Clearly about execution
    "confidence": 0.8
  }
}
```

**New values:**
- `"completed"` (instead of "success")
- `"failed"` (same)
- `"incomplete"` (instead of "partial_success")
- `"error"` (same)

**Pros:**
- ✅ Clear semantic distinction
- ✅ No more confusion between execution and quality
- ✅ "completed + 0.5 score" makes sense

**Cons:**
- ❌ Breaking change (old trajectories have old schema)
- ❌ Requires migration or version handling

**Implementation:**
```python
# letta/services/trajectory_converter.py
def _determine_outcome(self, run, messages):
    execution_status = "unknown"
    if run.status == "completed":
        execution_status = "completed"  # Not "success"
    elif run.status == "failed":
        execution_status = "failed"

    return {
        "status": execution_status,  # Renamed field
        "confidence": confidence,
        "reasoning": reasoning
    }
```

---

### Option 2: Add `quality_score` Alias (Backward Compatible)

Keep `outcome_score` but add a clearer alias in the UI and docs.

**Field mapping:**
- `outcome_score` → Also called `quality_score` or `learning_value`
- `outcome.type` → Also called `execution_status`

**Pros:**
- ✅ Backward compatible
- ✅ No schema changes needed
- ✅ Can fix with UI/docs only

**Cons:**
- ❌ Doesn't fix the root naming issue
- ❌ Still have two "outcome" concepts

---

### Option 3: Update UI Labels

Change how the UI displays these fields:

```
Before:
  Outcome: success
  Score: 0.5

After:
  Execution: ✅ Completed
  Learning Value: ⭐⭐⭐☆☆ (0.5)
```

**Pros:**
- ✅ No code changes needed
- ✅ Visual distinction makes it clear
- ✅ Immediate fix

**Cons:**
- ❌ Doesn't fix API/schema confusion
- ❌ Agents still see confusing field names

---

### Option 4: Merge Into Single Enum

Replace binary "success/failure" with outcome score ranges:

```python
# Instead of outcome.type + outcome_score, just use:
"outcome_tier": "moderate"  # Derived from score

# Mapping:
score >= 0.7 → "high_quality"
0.3 < score < 0.7 → "moderate_quality"
score <= 0.3 → "low_quality"
execution failed → "failed"
```

**Pros:**
- ✅ Single source of truth
- ✅ No confusion

**Cons:**
- ❌ Loses granularity (can't see 0.5 vs 0.6)
- ❌ Execution status and quality conflated again

---

## Recommendation

**Implement Option 1 + Option 3:**

1. **Rename field** (Option 1):
   - `outcome.type` → `execution.status`
   - Values: "completed", "failed", "incomplete", "error"

2. **Update UI** (Option 3):
   - Show "Execution: ✅ Completed" instead of "Outcome: success"
   - Show "Learning Value: 0.5 ⭐⭐⭐☆☆" prominently
   - Add tooltip explaining the distinction

3. **Update documentation:**
   - Clearly explain execution status vs learning value
   - Update system prompts to use correct terminology
   - Add examples showing they measure different things

---

## Migration Strategy

### Phase 1: Add New Field (Backward Compatible)

```python
# Add execution field alongside outcome
return {
    "outcome": {...},           # Keep for backward compat
    "execution": {              # New field (clear semantics)
        "status": "completed",
        "confidence": 0.8,
        "reasoning": [...]
    }
}
```

### Phase 2: Update Consumers

- Update UI to use `execution.status`
- Update docs to reference `execution` field
- Update system prompts

### Phase 3: Deprecate Old Field

- Add deprecation warning for `outcome.type`
- Schedule removal in next major version
- Migrate existing trajectories (one-time script)

---

## Files to Modify

### Core Logic
- `letta/services/trajectory_converter.py:198-240` - Rename outcome to execution
- `letta/schemas/trajectory.py` - Update schema if adding new field

### UI
- `letta-ui/src/components/TrajectoriesView.tsx` - Update labels
- Add visual distinction (icons, stars, etc.)

### Documentation
- `letta-code/src/agent/prompts/system_prompt.txt` - Update terminology
- `.planning/trajectories-*.md` - Update docs
- README or API docs

---

## Example Queries After Fix

### Before (Confusing)
```
"Find trajectories where outcome.type = 'success' and outcome_score >= 0.7"
^ Why do I need both? Isn't success already good?
```

### After (Clear)
```
"Find trajectories where execution.status = 'completed' and outcome_score >= 0.7"
^ Ah! Must complete AND have high learning value. Makes sense.
```

---

## Summary

**Problem:**
- `outcome.type = "success"` measures execution (did it complete?)
- `outcome_score = 0.5` measures learning value (was it valuable?)
- Naming makes them sound like they should align, but they don't

**Solution:**
- Rename `outcome.type` → `execution.status`
- Change values: "success" → "completed"
- Update UI to show both clearly with different labels
- Document the distinction

**Impact:**
- Users understand why "completed task" might have mediocre score
- No more confusion between execution and quality
- Three-tier system (success/moderate/failure) makes more sense
