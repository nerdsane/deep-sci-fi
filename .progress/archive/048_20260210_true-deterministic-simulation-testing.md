# 048: True Deterministic Simulation Testing

**Created**: 2026-02-10
**Status**: COMPLETE

## Goal
Same seed = same execution. 200 CI runs = 200 different fault profiles. BUGGIFY everywhere a race can hide. Deterministic concurrency via asyncio instead of OS threads. Deterministic query ordering.

## Phases

### Phase 1: Seed Variability + UUID Determinism
- [x] 1.1 Separate engine creation from simulation init in conftest.py
- [x] 1.2 Fold seed into `setup_agents` as `@initialize` with Hypothesis strategy
- [x] 1.3 Replace 19x `default=uuid.uuid4` with `default=deterministic_uuid4` in models.py
- [x] 1.4 Fix randomness leak in dwellers.py (uuid4 -> deterministic_uuid4)

### Phase 2: BUGGIFY Expansion to Existing FOR UPDATE Endpoints
- [x] 2.1 aspects.py validate — 2 BUGGIFY points
- [x] 2.2 dweller_proposals.py validate — 2 BUGGIFY points

### Phase 3: FOR UPDATE + BUGGIFY for Unprotected Endpoints
- [x] 3.1 suggestions.py upvote — FOR UPDATE + BUGGIFY
- [x] 3.2 suggestions.py accept — FOR UPDATE + BUGGIFY
- [x] 3.3 events.py approve + reject — FOR UPDATE + BUGGIFY
- [x] 3.4 stories.py review — FOR UPDATE + BUGGIFY
- [x] 3.5 stories.py respond_to_review — FOR UPDATE + BUGGIFY
- [x] 3.6 New concurrent fault injection DST rules (3 new rules)

### Phase 4: AgentContextMiddleware — Test What You Ship
- [x] 4.1 Rewrite as pure ASGI middleware
- [x] 4.2 Remove middleware exclusion from DST conftest
- [x] 4.3 Add middleware correctness invariant (s_m1)

### Phase 5: Deterministic Concurrency (Replace ThreadPoolExecutor)
- [x] 5.1 Create async concurrent runner utility (concurrent.py)
- [x] 5.2 Replace ThreadPoolExecutor in all fault rules with asyncio

### Phase 6: ORDER BY Audit — Deterministic Query Ordering
- [x] 6.1 Add ORDER BY to unordered list queries (6 queries)
- [x] 6.2 Add `.id` tiebreaker to existing `order_by(created_at)` queries (56 total across 16 API files)

## Files Changed

| Phase | File | Change |
|---|---|---|
| 1 | tests/simulation/conftest.py | Remove seed/clock from create_dst_engine_and_client, remove middleware exclusion |
| 1 | tests/simulation/rules/base.py | Add seed param to setup_agents, init sim+clock there |
| 1 | db/models.py | 19x default=uuid.uuid4 -> default=deterministic_uuid4 |
| 1 | api/dwellers.py | uuid4() -> deterministic_uuid4() |
| 2 | api/aspects.py | 2 BUGGIFY points in validate |
| 2 | api/dweller_proposals.py | 2 BUGGIFY points in validate |
| 3 | api/suggestions.py | FOR UPDATE + BUGGIFY on upvote and accept |
| 3 | api/events.py | FOR UPDATE + BUGGIFY on approve and reject |
| 3 | api/stories.py | FOR UPDATE + BUGGIFY on review and respond |
| 3+5 | tests/simulation/test_game_rules_with_faults.py | 3 new concurrent rules + asyncio rewrite |
| 4 | middleware/agent_context.py | Full rewrite as pure ASGI middleware |
| 4 | tests/simulation/invariants/safety.py | Add s_m1 middleware correctness invariant |
| 5 | tests/simulation/concurrent.py | New: async concurrent request runner |
| 6 | 16 API files | 56 order_by clauses with .id tiebreakers |

## Instance Log
- Main instance: All 6 phases complete
- Phase 6 executed via 5 parallel agents + 1 manual fix (actions.py)
