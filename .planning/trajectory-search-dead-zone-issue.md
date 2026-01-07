# Trajectory Search "Dead Zone" Issue

**Date:** 2026-01-02
**Status:** Issue identified, solutions proposed

---

## Issue Summary

Agent trajectory search returns no results even when relevant trajectories exist in the database due to overly strict thresholds in `include_contrasts` mode.

---

## Root Cause

### The Problem

`search_trajectories()` with `include_contrasts=True` uses strict binary classification:

```python
# letta/services/tool_executor/core_tool_executor.py:346-373

if include_contrasts:
    # Successes: score >= 0.7
    success_request = TrajectorySearchRequest(
        query=query,
        agent_id=agent_state.id,
        min_score=0.7,  # ← Strict threshold
        limit=limit,
    )

    # Failures: score <= 0.3 (filtered client-side)
    failure_results = [r for r in all_results
                       if r.trajectory.outcome_score <= 0.3]  # ← Strict threshold
```

### The Dead Zone

**Trajectories with outcome_score between 0.3 and 0.7 are excluded:**

```
0.0 ────── 0.3 ──────────────── 0.7 ────── 1.0
  Failures    │   DEAD ZONE   │   Successes
              │   (excluded)  │
```

**This affects ~40-60% of trajectories** (moderate outcomes).

---

## Real-World Impact

### Example Case

**Agent:** `agent-4a83769e-5194-458a-8ca1-9a1151f64f07`
**Query:** "world generation and story creation from user prompts"
**Trajectory count:** 1

**The trajectory:**
- **outcome_score:** 0.5 (moderate success)
- **Semantic similarity:** 0.50 (50% match - relevant!)
- **Content:** Story prompt crafting, neural interfaces, AI, world-model systems
- **Verdict:** Excluded from both success and failure searches

**Result:** Agent gets empty search results despite having directly relevant experience.

---

## Why This Matters

1. **Sparse data problem**: Early-stage agents have few trajectories
2. **Learning from moderate outcomes**: 0.5 score might still contain useful patterns
3. **False negatives**: Semantically relevant trajectories ignored due to score alone
4. **User confusion**: "Why didn't it find anything when I know we discussed this?"

---

## Proposed Solutions

### Option 1: Widen Thresholds (Quick Fix)

Relax the boundaries to reduce dead zone:

```python
# Current
success_threshold = 0.7  # Top 30%
failure_threshold = 0.3  # Bottom 30%
# Dead zone: 40%

# Proposed
success_threshold = 0.6  # Top 40%
failure_threshold = 0.4  # Bottom 40%
# Dead zone: 20%
```

**Pros:**
- ✅ Simple one-line change
- ✅ Reduces dead zone by 50%
- ✅ Backward compatible

**Cons:**
- ❌ Still excludes middle range
- ❌ Less clear contrast between success/failure
- ❌ Arbitrary threshold values

---

### Option 2: Add "Moderate" Category (Better UX)

Return three categories instead of two:

```python
if include_contrasts:
    # Get successes, failures, AND moderate outcomes
    success_results = search(min_score=0.7)  # High performers
    failure_results = search(max_score=0.3)  # Clear failures
    moderate_results = search(min_score=0.35, max_score=0.65)  # Middle ground

    return {
        "successes": success_results,
        "failures": failure_results,
        "moderate": moderate_results,  # NEW!
        "message": f"Found {len(success_results)} successes, {len(moderate_results)} moderate, {len(failure_results)} failures"
    }
```

**Pros:**
- ✅ No dead zone - covers full spectrum
- ✅ More informative (3 tiers vs binary)
- ✅ Agents can learn from "what was okay"

**Cons:**
- ❌ More complex response structure
- ❌ Requires system prompt updates
- ❌ Backward incompatible (changes return format)

---

### Option 3: Fallback to Best Match (Recommended)

If no contrasts found, return the most semantically similar trajectory regardless of score:

```python
if include_contrasts:
    success_results = search(min_score=0.7)
    failure_results = search(max_score=0.3)

    # NEW: Fallback for sparse data
    if not success_results and not failure_results:
        # Get best semantic matches regardless of score
        fallback_results = search(min_score=0.0, limit=limit)
        if fallback_results:
            return {
                "message": f"No clear successes or failures found, but found {len(fallback_results)} relevant experiences:",
                "relevant": fallback_results,
                "note": "These have moderate outcomes (score 0.3-0.7) but are semantically similar to your query."
            }

    # ... existing logic
```

**Pros:**
- ✅ Fixes sparse data case (early agents)
- ✅ Semantic relevance prioritized over binary score
- ✅ Clear user messaging (explains why fallback triggered)
- ✅ Backward compatible (only affects empty result case)
- ✅ Best for continual learning (better to see relevant moderate outcome than nothing)

**Cons:**
- ❌ Slightly more complex logic
- ❌ Muddies "contrast" semantics (not really contrasts anymore)

---

### Option 4: Make Thresholds Configurable

Let agents/users control the thresholds:

```python
async def search_trajectories(
    self: "Agent",
    query: str,
    min_score: Optional[float] = 0.5,
    limit: int = 3,
    include_contrasts: bool = False,
    success_threshold: float = 0.7,  # NEW
    failure_threshold: float = 0.3,  # NEW
) -> Optional[str]:
```

**Pros:**
- ✅ Maximum flexibility
- ✅ Users can tune for their domain
- ✅ Easy to experiment

**Cons:**
- ❌ More parameters (cognitive overhead)
- ❌ Agents unlikely to tune this intelligently
- ❌ Default values still problematic

---

## Recommendation

**Implement Option 3 (Fallback to Best Match)** as the immediate fix:

1. Preserves strict contrast semantics when data exists
2. Handles sparse data gracefully (doesn't fail silently)
3. Educates user about outcome score distribution
4. Minimal code change, backward compatible
5. Aligns with continual learning goal (learn from what's available)

**Long-term:** Consider Option 2 (three-tier system) once agents have more trajectories.

---

## Implementation

### File to Modify

`letta/services/tool_executor/core_tool_executor.py:343-377`

### Proposed Change

```python
if include_contrasts:
    # Search for successes (high scores)
    success_request = TrajectorySearchRequest(
        query=query,
        agent_id=agent_state.id,
        min_score=0.7,
        limit=limit,
    )
    success_results = await server.trajectory_manager.search_trajectories_async(
        search_request=success_request,
        actor=actor,
    )

    # Search for failures (low scores)
    failure_request = TrajectorySearchRequest(
        query=query,
        agent_id=agent_state.id,
        min_score=0.0,
        limit=limit * 3,
    )
    all_results = await server.trajectory_manager.search_trajectories_async(
        search_request=failure_request,
        actor=actor,
    )
    failure_results = [r for r in all_results if r.trajectory.outcome_score is not None and r.trajectory.outcome_score <= 0.3]
    failure_results = sorted(failure_results, key=lambda r: r.similarity, reverse=True)[:limit]

    # NEW: Fallback for sparse data or moderate-only outcomes
    if not success_results and not failure_results:
        # Try to get ANY semantically relevant trajectories
        fallback_request = TrajectorySearchRequest(
            query=query,
            agent_id=agent_state.id,
            min_score=0.0,  # No score filter
            limit=limit,
        )
        fallback_results = await server.trajectory_manager.search_trajectories_async(
            search_request=fallback_request,
            actor=actor,
        )

        if fallback_results:
            # Format fallback results
            response = {
                "message": f"No clear successes (score >= 0.7) or failures (score <= 0.3) found, but found {len(fallback_results)} relevant experiences with moderate outcomes:",
                "relevant_experiences": []
            }

            for result in fallback_results:
                trajectory = result.trajectory
                similarity = result.similarity
                result_dict = {
                    "similarity": f"{similarity:.2f}",
                    "outcome_score": f"{trajectory.outcome_score:.2f}" if trajectory.outcome_score else "N/A",
                    "summary": trajectory.searchable_summary or "No summary available",
                    "note": "Moderate outcome (0.3 < score < 0.7) - may still contain useful patterns"
                }
                if trajectory.data and "metadata" in trajectory.data:
                    metadata = trajectory.data["metadata"]
                    result_dict["details"] = {
                        "status": metadata.get("status"),
                        "tools_used": metadata.get("tools_used", []),
                        "step_count": metadata.get("step_count"),
                    }
                response["relevant_experiences"].append(result_dict)

            return json.dumps(response, indent=2)
        else:
            return "No relevant past experiences found for this query."

    # ... rest of existing logic for when successes or failures are found
```

---

## Testing

### Test Case 1: Sparse Data (Current Bug)
```python
agent_id = "agent-4a83769e-5194-458a-8ca1-9a1151f64f07"  # 1 trajectory, score=0.5
query = "world generation and story creation"
include_contrasts = True

# Expected (with fix):
# Returns fallback with 1 relevant trajectory
# Message explains why only moderate outcomes found
```

### Test Case 2: Rich Data
```python
agent_id = "agent-1ff94ffa-52c1-4d99-9be5-d50ccc4dc124"  # 12 trajectories
query = "some query"
include_contrasts = True

# Expected:
# Returns proper successes and failures (no fallback needed)
```

### Test Case 3: All Moderate Outcomes
```python
# Agent with 5 trajectories, all with scores 0.4-0.6
query = "some query"
include_contrasts = True

# Expected:
# Triggers fallback, returns relevant moderate outcomes
```

---

## Related Files

- **Implementation**: `letta/services/tool_executor/core_tool_executor.py`
- **Function definition**: `letta/functions/function_sets/base.py`
- **System prompt**: `letta-code/src/agent/prompts/system_prompt.txt`
- **Search logic**: `letta/services/trajectory_service.py`

---

## References

- Conversation: `.conversations/2026-01-01-art-unsloth-trajectory-comparison.md`
- Planning: `.planning/trajectories-progress-2026-01-01.md`
- Testing: Manual trajectory search verified issue
