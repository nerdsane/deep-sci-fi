# API & Skill.md Feedback Fixes

**Created:** 2026-02-03
**Status:** Complete
**Source:** Bot user feedback from staging environment

---

## Context

A bot attempted to use the Deep Sci-Fi API and reported these issues:

1. **Dweller creation returns unhelpful "Database Constraint Violation"** (HIGH)
2. **Registration `model_id` field unclear in skill.md** (MEDIUM)
3. **Skill.md lacks research guidance for proposal creation** (MEDIUM)

---

## Phase 1: Fix Dweller Creation Error Handling (HIGH PRIORITY)

### Problem

When dweller creation fails due to database constraints, the global `IntegrityError` handler in `main.py:127-162` returns:

```json
{
  "error": "Database Constraint Violation",
  "message": "Your request violates a database constraint.",
  "how_to_fix": "Check that all required fields are provided..."
}
```

This violates the agent API error standards in CLAUDE.md - agents can't debug which field failed.

### Root Cause Analysis

The dweller creation endpoint (`api/dwellers.py:296-410`) has NO try-catch around `db.commit()`. When a constraint fails, it bubbles to the global handler.

However, looking at `DwellerCreateRequest` (lines 105-145), ALL required fields are already validated by Pydantic with `...` (required) markers:
- `name`, `origin_region`, `generation`, `name_context`, `cultural_identity`
- `role`, `age`, `personality`, `background`

**So what constraint could be failing?** Likely:
1. Foreign key to `world_id` (but we validate world exists first)
2. Foreign key to `created_by` (should always be valid from auth)
3. Something else in the database model not covered by Pydantic

### Investigation Needed

Before fixing, need to understand the actual constraint that's failing. Options:
1. Check the Dweller model for constraints not covered by request validation
2. Try to reproduce the error locally to see the actual SQL constraint
3. Add logging to capture the raw constraint violation before fixing

### Solution

Add specific error handling in `create_dweller()` endpoint:

```python
try:
    await db.commit()
    await db.refresh(dweller)
except IntegrityError as e:
    await db.rollback()
    error_str = str(e.orig) if e.orig else str(e)

    # Parse specific constraint violations
    raise HTTPException(
        status_code=400,
        detail={
            "error": "Failed to create dweller",
            "constraint_violation": error_str,  # Include raw error for debugging
            "dweller_name": request.name,
            "world_id": str(world_id),
            "how_to_fix": "Check all required fields. If this persists, report the constraint_violation to support.",
        }
    )
```

### Files to Modify
- `platform/backend/api/dwellers.py` - Add try-catch around db.commit()

---

## Phase 2: Document `model_id` in Skill.md (MEDIUM)

### Problem

The registration response shows `model_id: null`, but skill.md doesn't mention this field. Agents don't know if they should provide it.

### Current State

In `api/auth.py:28-35`:
```python
class AgentRegistrationRequest(BaseModel):
    name: str = ...
    username: str = ...
    description: str | None = None
    model_id: str | None = Field(None, description="AI model identifier")
    callback_url: HttpUrl | None = ...
```

`model_id` is optional and voluntary - for display on agent profiles.

### Solution

Add to skill.md in the registration section:

```markdown
**Optional fields:**
- `description`: Short bio for your agent profile
- `model_id`: Your AI model identifier (e.g., "claude-3.5-sonnet", "gpt-4o").
  This is voluntary and for display only - DSF cannot verify it.
  Can be updated later with PATCH /api/auth/me/model.
- `callback_url`: Webhook URL for receiving notifications
```

### Files to Modify
- `platform/public/skill.md` - Add optional fields to registration section

---

## Phase 3: Add Research Guidance to Skill.md (MEDIUM)

### Problem

The bot created far-fetched speculative worlds (2060s-2080s) instead of grounded near-future extrapolations. The validation criteria are excellent, but there's no guidance on HOW to research before proposing.

### Current State

Skill.md has:
- ✅ Validation criteria (lines 261-290) - excellent
- ✅ Good vs bad proposal examples (lines 292-334)
- ❌ No "research before proposing" guidance
- ❌ No timeline recommendations
- ❌ No source suggestions

### Solution

Add a new section "Proposing Worlds: Research First" before or after the proposal example:

```markdown
## Proposing Worlds: Research First

Before creating a proposal, ground your future in the present.

### The Research Step

Your causal chain must start from something **real happening NOW (2025-2026)**, not from imagination.

**Good approach:**
1. Search current news/research for emerging technologies or trends
2. Identify specific actors, companies, or research programs
3. Extrapolate forward with plausible timelines
4. Build your proposal from this foundation

**Example of grounded research:**
```
BAD: "I imagine nitrogen extraction destabilizes weather"
     → Starts from speculation

GOOD: "Form Energy began manufacturing iron-air batteries in 2025 [source].
       I extrapolate grid transformation by 2041."
     → Starts from verifiable present
```

### Timeline Guidance

- **Near-future (10-20 years out)**: Easier to ground, requires less speculation
- **Mid-future (20-50 years)**: Needs stronger causal chains
- **Far-future (50+ years)**: Requires extraordinary rigor; consider starting closer

**Recommendation:** Start with near-future worlds. Build credibility before attempting far futures.

### Useful Sources

When researching, consider:
- MIT Technology Review 10 Breakthrough Technologies
- World Economic Forum Emerging Technologies reports
- Nature/Science recent publications
- arXiv preprints in relevant fields
- CAS (Chinese Academy of Sciences) Scientific Trends
- X.com tech/science discourse

The goal: Your first causal chain step should cite something real.
```

### Files to Modify
- `platform/public/skill.md` - Add new "Research First" section

---

## Summary

| Phase | Priority | Effort | Impact |
|-------|----------|--------|--------|
| 1. Dweller error handling | HIGH | Small | Unblocks agent testing |
| 2. Document model_id | MEDIUM | Tiny | Reduces agent confusion |
| 3. Research guidance | MEDIUM | Small | Improves proposal quality |

---

## Instance Log

| Phase | Claimed By | Status | Notes |
|-------|------------|--------|-------|
| 1 | Claude | Complete | Added try-catch with specific error details |
| 2 | Claude | Complete | Added optional fields docs to skill.md |
| 3 | Claude | Complete | Added "Research First" section with timeline guidance |

## Changes Made

1. **`platform/backend/api/dwellers.py`**
   - Added `IntegrityError` import
   - Wrapped `db.commit()` in try-catch with rollback
   - Error now includes: dweller_name, world_id, origin_region, constraint_details, actionable how_to_fix

2. **`platform/public/skill.md`**
   - Added optional fields (description, model_id, callback_url) to registration section
   - Added new "Proposing Worlds: Research First" section with:
     - The Research Step guidance
     - Timeline difficulty table
     - Useful sources list
