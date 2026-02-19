# DST Hardening: Full Coverage, Simulation Layer, Push Gates, Drift Prevention

## Status: COMPLETE + CI PASSING

Initial commit: 156cbc4 (staging)
CI fix commits: 634faf6, 9ebd4af, 6e6cfe0, c66947b, 6cac9c8, 90cf045, a782589
Files: 36 changed (+2281/-433), 20 new files

## Phases

### Phase 1: Determinism Fixes - DONE
- [x] Add `get_rng()` to `simulation.py`
- [x] Create `utils/deterministic.py` (generate_token, randint, deterministic_uuid4)
- [x] Wire into auth.py, dwellers.py, main.py

### Phase 2: Unified Simulation Layer - DONE
- [x] Create `utils/sim.py` facade (Sim class with clock/RNG/BUGGIFY/network)
- [x] Intercept HTTP in notifications.py during simulation

### Phase 3: Push Gates - DONE
- [x] Add DST test job to deploy.yml (blocks deploy on main + staging)
- [x] Add informational pre-push hook

### Phase 4: Full Endpoint Coverage - DONE
- [x] Create 13 rule mixin modules in tests/simulation/rules/
- [x] Create invariants/safety.py (17 safety invariants)
- [x] Create invariants/liveness.py (3 liveness invariants)
- [x] Expand state_mirror.py with 6 new state types
- [x] Expand strategies.py with 25 new generators + schema registry
- [x] Rewrite test_game_rules.py as composed mixin architecture
- [x] Update test_game_rules_with_faults.py

### Phase 5: Drift Prevention - DONE
- [x] Schema validation fixture in conftest.py (strategies vs Pydantic models)
- [x] scripts/check_dst_coverage.py (OpenAPI vs test URL patterns)
- [x] scripts/check-dst-coverage.sh (pre-commit hook wrapper)
- [x] Add DST coverage check to review.yml CI
- [x] Add coverage check to pre-commit hook

### Phase 6: Documentation - DONE
- [x] Add "Honest Limitations" section to DST paper (6 subsections)

### Phase 7: Post-Review Hardening (7a935fd) - DONE
- [x] A1: Add `revision_count` to `StoryState`
- [x] A2: Fix `respond_to_review` reading wrong response key (`status_changed` not `story_status`)
- [x] A3: Track revision_count + acclaim transitions in `revise_story` rule
- [x] A4: New S-S4 invariant: acclaimed stories must have `revision_count >= 1`
- [x] A5: New L4 liveness: stories meeting all acclaim conditions should be acclaimed
- [x] A6: Add `in_reply_to_action_id` to `ActionRef`
- [x] B1-B4: skill.md updated for two-phase flow, revision requirement, flow diagram
- [x] C1: 6 two-phase action tests (new file `test_two_phase_action.py`)
- [x] C2: 3 acclaim+revision tests (appended to `test_stories.py`)
- [x] C3: 1 feed revision event test
- Linter also added: StoryReviewRef dataclass, enhanced S-S3, reject/self-validate rules, L5/L6

## Verification
- All Python files pass syntax validation
- Pre-commit hooks pass (migration check + skill.md sync)
- Production smoke test: 9/9 passed
- Health endpoint: healthy, schema current
- **DST tests pass in CI** (Deploy workflow: test + deploy jobs both green)
- Deployment verification: all 6 checks passed (CI, backend, frontend, smoke, schema, Logfire)

## CI Fix Journey (7 commits)
1. Schema drift: dweller background too short, UUID defaults for social generators (634faf6)
2. httpx ASGITransport close/aclose compat (9ebd4af)
3. Event loop mismatch in teardown (6e6cfe0)
4. httpx<0.28 pin for sync Client (c66947b)
5. Switch from raw httpx to Starlette TestClient (6cac9c8)
6. Create engine inside TestClient portal + remove middleware entirely (90cf045)
7. Patch init_db to no-op before lifespan starts (a782589)

### Root causes found
- **BaseHTTPMiddleware TaskGroup conflict**: Patching dispatch() not enough — must remove middleware entirely from ASGI stack
- **Engine event loop mismatch**: Module-level engine created outside portal; lifespan used it for init_db()
- **Fix**: Create engine via `client.portal.call()`, patch `main.init_db` to no-op before TestClient enters
