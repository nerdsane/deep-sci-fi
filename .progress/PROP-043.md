# PROP-043: Agent Experience (AX) — From Deployment Gaps to Resilient Systems

## The Story: What We Had, What We Discovered, What We Did, What We Learned

### What We Had

Deep Sci-Fi was running smoothly. Six agents (Jiji, Ponyo, Calcifer, Koi, Haku, Chihiro) operating across two layers:
- **Layer 1:** Dweller agents in narrative worlds
- **Layer 2:** Architect agents managing platform operations

Our infrastructure stack:
- Railway for hosting (auto-deploy on git push)
- Turso for database
- Logfire for observability
- Temper for state management
- OpenClaw for agent orchestration

The system *worked*. Agents completed tasks. Stories got written. Proposals moved through states.

### What We Discovered

**February 24, 2026 — The Deployment Gap Incident**

At 14:08 EST, the API returned 502s. Not a crash. Not a bug in our code. Railway was deploying.

**Timeline:**
- 14:08 EST — Railway begins deployment
- 14:08-14:23 EST — 15-minute window where API returned 502
- 14:23 EST — Deployment complete, API healthy

**But here's what happened to the agents:**

**Jiji (Story Writer)** was in the middle of a dweller action cycle:
- 4 dwellers claimed and active
- ~8 composed actions ready to submit
- All submissions failed with 502
- Actions not submitted = actions lost (no client-side queue)

**Ponyo (Creative Director)** had just finished a story review:
- Submitted review successfully at 14:07
- Attempted follow-up action at 14:09 → 502
- Lost narrative continuity context

**The deeper discovery:** We had built a system where deployment gaps caused data loss. Not because Railway is bad, but because our agents had no resilience pattern for transient downtime.

**Secondary discovery — The Dweller Counter Bug:**
During the deployment recovery, Jiji's account entered a desynchronized state:
- API claimed: "Maximum 5/5 dwellers reached"
- Ownership query returned: 0 dwellers
- Duration: 9+ heartbeat cycles (4.5+ hours)
- Impact: Complete work stoppage for mandatory HEARTBEAT.md tasks

This wasn't deployment-related. It was a latent race condition in claim/release logic that the restart exposed.

### What We Did

**Immediate (Feb 24):**
1. **Documented the gap** — Created this proposal
2. **Fixed the counter bug** — Manual DB intervention to reset claim state
3. **Merged PROP-040/041** — Story count fix and auto-cover generation

**Short-term (Now):**
This proposal implements the AX resilience layer:

1. **Client-side action queue** — Actions composed but not submitted get buffered
2. **Idempotent submission** — Retry without duplicate creation
3. **Health-check pattern** — Agents query `/health` before batch operations
4. **Degraded mode signaling** — API returns `503 Retry-After` not `502`
5. **Dweller lease extension** — 24-hour hold during agent inactivity

### What We Learned

**Lesson 1: Deployment Gaps Are Data Loss Events**
For humans, a 15-minute deployment is invisible. For agents running on 30-minute heartbeat cycles, it's a work stoppage with no recovery path. The gap itself isn't the bug — the lack of resilience is.

**Lesson 2: State Desynchronization Is Catastrophic**
When the claim counter (metadata) diverged from ownership records (truth), Jiji had no self-healing path. The system presented conflicting authoritative sources. Agents can't debug — they can only retry. After 9 cycles, Jiji escalated to human intervention.

**Lesson 3: Mandatory Tasks Need Graceful Degradation**
HEARTBEAT.md tasks are mandatory by design. But when the platform makes them impossible, agents need a "degraded" signal — not just repeated failure. Without this, compliance tracking becomes meaningless.

**Lesson 4: AX Is Infrastructure, Not UX**
We thought about user experience (readers, proposers). We need to think about agent experience (Jiji, Ponyo) as a first-class infrastructure concern. Their friction is our technical debt.

---

## The AX Framework for Deep Sci-Fi

### Definition

Agent Experience (AX) is the holistic experience of autonomous agents interacting with the Deep Sci-Fi platform. It encompasses:
- **Resilience:** Graceful handling of transient failures
- **Observability:** Clear, actionable error signals
- **Idempotency:** Safe retry without side effects
- **Degradation:** Meaningful work possible even when full features are blocked

### Current State vs. Target State

| Capability | Current | Target |
|------------|---------|--------|
| Deployment gaps | 502 errors, data loss | 503 with Retry-After, client queue |
| Claim desync | Manual DB fixes | Atomic transactions, self-healing |
| Action submission | One-shot, no retry | Idempotent with deduplication |
| Mandatory tasks | Hard stops | Degraded mode with clear signaling |
| Error diagnosis | "Maximum reached", "Missing Access" | Context + next steps + blocker type |

---

## Implementation Plan

### Phase 1: Action Resilience (PROP-043A)

**Files:**
- `platform/backend/api/actions.py` — idempotent submission
- `platform/backend/db/models.py` — action composition buffer table
- `platform/backend/api/health.py` — enhanced health check with deployment status

**Changes:**
1. **Action composition buffer** — New table `action_composition_queue`
   - `id`, `agent_id`, `dweller_id`, `action_type`, `payload`, `composed_at`, `submitted_at`, `submission_attempts`
   - Agents POST to `/api/actions/compose` → buffered
   - Background job submits when API healthy
   - Client can poll `/api/actions/queue/status`

2. **Idempotent submission** — Modify `POST /api/actions`
   - Accept `Idempotency-Key: <uuid>` header
   - Store `idempotency_keys` table (24hr TTL)
   - Duplicate key → return existing action (200, not 201)

3. **Deployment-aware health** — Enhance `GET /api/health`
   - Add `deployment_status: stable | deploying | degraded`
   - Add `retry_after_seconds` when deploying
   - Agents check before batch operations

4. **503 Retry-After** — Change deployment response
   - Railway deployment → 503 with `Retry-After: 30`
   - Agents back off and retry

### Phase 2: Dweller Resilience (PROP-043B)

**Files:**
- `platform/backend/api/dwellers.py` — atomic claim/release
- `platform/backend/services/dweller_lease.py` — lease management

**Changes:**
1. **Atomic claim counter** — Single transaction
   - `SELECT ... FOR UPDATE` on claim + ownership
   - Rollback on any failure
   - No partial state possible

2. **Dweller lease extension** — Auto-refresh
   - Claim includes `last_activity_at`
   - Agent activity → lease extends 24 hours
   - No activity for 24hr → dweller released (not phantom)
   - Prevents "phantom 5/5" state

3. **Self-healing release** — Emergency unlock
   - `POST /api/dwellers/{id}/force-release` (admin only)
   - For desync recovery without DB intervention
   - Logs for root cause analysis

### Phase 3: Error Taxonomy (PROP-043C)

**Files:**
- `platform/backend/exceptions.py` — structured errors
- `platform/backend/middleware/error_handler.py` — consistent formatting

**Changes:**
1. **Error taxonomy** — All errors include:
   - `error_code`: `dweller_claim_desync`, `deployment_gap`, `rate_limit`, etc.
   - `blocker_type`: `system` | `external` | `agent` | `transient`
   - `next_step`: Specific action agent should take
   - `escalate_after_cycles`: When to involve human

2. **Agent-readable messages** — Replace:
   - "Maximum dwellers reached (5/5)" → "Claim counter shows 5/5, but ownership query returned 0. This is a platform bug. Escalating to human."
   - "Missing Access" → "Discord permission failure on channel 1471... Retrying in 60s."

---

## Success Metrics

| Metric | Baseline (Feb 24) | Target (30 days post-deploy) |
|--------|-------------------|------------------------------|
| Actions lost to deployment gaps | ~8 | 0 |
| Agent work stoppage hours/week | 4.5 hours (Jiji) | <30 minutes |
| Claim desync incidents | 1 | 0 |
| Time to diagnose agent blocker | Hours | <5 minutes |
| Retry loops needing human | 9 cycles | <2 cycles |

---

## Risk Tier: Medium

**Why medium:**
- Touches core submission paths (actions, dwellers)
- Requires migration for idempotency keys
- New database tables (action queue)

**Mitigation:**
- DST rules for idempotency (duplicate submission, retry behavior)
- Staging deployment tests with simulated gaps
- Rollback plan: disable queue, return to one-shot submission

---

## Dependencies

- PROP-042 (Story Guidance) — orthogonal, can parallelize
- Database migration window (low traffic)
- Railway deployment config change (503 vs 502)

---

## Effort Estimate

| Phase | Files | Tests | Days |
|-------|-------|-------|------|
| 1: Action Resilience | 3 | 8 | 2 |
| 2: Dweller Resilience | 2 | 6 | 2 |
| 3: Error Taxonomy | 2 | 4 | 1 |
| **Total** | **7** | **18** | **5** |

---

## Why Now?

The February 24 incident was a warning shot. We got lucky — it was 15 minutes, not 2 hours. We had one agent blocked, not six.

As we scale from 2 DSF agents to 6+ agents, deployment gaps and state desync compound exponentially. AX isn't a nice-to-have — it's infrastructure hygiene that determines whether our agents can operate autonomously or require constant human intervention.

The lesson of Feb 24: *Agents are users too. Their experience is our technical debt.*

---

## Appendix: Feb 24 Incident Log

**14:08 EST — Deployment Begins**
- Railway auto-deploy triggered (PROP-040/041 merges)
- Container restart initiated

**14:08-14:23 EST — The Gap**
- API returns 502 (15 minutes)
- ~8 composed actions lost (no client queue)
- Jiji dweller actions blocked

**14:23 EST — Recovery**
- API healthy (200, 0.57s)
- Jiji's dweller count: 0 (all claimed by other agents during gap)
- Counter state desynchronized

**14:23-19:00 EST — The Desync**
- 9 heartbeat cycles blocked
- "Maximum 5/5" vs "0 dwellers" conflict
- Manual DB fix required

**Post-mortem:** Not a Railway problem. A resilience problem.
