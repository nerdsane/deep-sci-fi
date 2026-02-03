# Agent API Error Handling Audit

**Status**: In Progress
**Created**: 2026-02-02

## Goal

Audit all agent-facing API endpoints and ensure error responses are:
1. Informative - clearly explain what went wrong
2. Actionable - tell the agent how to fix the issue
3. Consistent - use a standard error format across all endpoints

## Findings

### Current State

**Good patterns already in place:**
- `dwellers.py:claim_dweller` - structured error with `how_to_fix`
- `dwellers.py:get_dweller_state` - structured error with `how_to_fix`
- `dwellers.py:take_action` (move validation) - shows available regions
- `proposals.py:submit_proposal` - structured error with context
- `proposals.py:create_validation` - structured error with context

**Needs improvement:**

#### auth.py (Authentication)
- Line 109: "Missing X-API-Key header" - needs how to fix
- Line 119: "Invalid or revoked API key" - needs how to fix
- Line 122: "API key expired" - needs how to fix
- Line 130: "User not found" - needs how to fix

#### agents.py (Agent profiles)
- Line 111: "Agent not found" - needs how to fix
- Line 114: "Not an agent account" - needs how to fix
- Line 276: "Agent not found" - needs how to fix
- Line 279: "Not an agent account" - needs how to fix

#### dwellers.py (Inconsistent patterns)
- Line 208, 250, 284, 378, 909: "World not found" - needs how to fix
- Line 211, 289: "Only the world creator can..." - needs how to fix
- Line 426, 538, 727, 972, etc.: "Dweller not found" - needs how to fix
- Line 543, 729, 974, etc.: "You are not inhabiting this dweller" - needs structured error

#### proposals.py (Some good, some need work)
- Line 225: "Proposal not found" - needs how to fix
- Line 339, 342, 344-348: Various errors need structured format
- Line 408: "Proposal not found" - needs how to fix

## Implementation Plan

### Phase 1: Define Standard Error Format
Add a utility function for consistent error responses.

### Phase 2: Update auth.py
Fix all 4 authentication error messages.

### Phase 3: Update agents.py
Fix all 4 error messages.

### Phase 4: Update dwellers.py
Fix ~20+ error messages to use consistent format.

### Phase 5: Update proposals.py
Fix remaining ~5 error messages.

### Phase 6: Update CLAUDE.md
Add API error handling guidelines for future development.

## Standard Error Format

```python
{
    "error": "Brief description",
    "error_code": "MACHINE_READABLE_CODE",  # optional
    "context": {
        # Relevant IDs, values, etc.
    },
    "how_to_fix": "Actionable guidance for the agent"
}
```

## Completion Checklist
- [x] Phase 1: Error utility - Created `utils/errors.py` with `agent_error()` helper
- [x] Phase 2: auth.py - Updated 4 error messages (missing key, invalid key, expired key, user not found)
- [x] Phase 3: agents.py - Updated 4 error messages (agent not found by ID and username, not an agent account)
- [x] Phase 4: dwellers.py - Updated ~20 error messages across all endpoints
- [x] Phase 5: proposals.py - Updated 5 error messages (not found, not owner, wrong status)
- [x] Phase 6: CLAUDE.md - Added "Agent API Error Handling" section with guidelines
