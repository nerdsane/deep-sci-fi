# Trajectories Implementation Checklist
**Track progress through each phase**

---

## Phase 1: Conversation → Trajectory Converter (Week 1)
**Branch:** `feat/trajectory-converter`
**Upstream:** ✅ Letta PR
**Status:** 🔄 IN PROGRESS (80% complete)

### Setup
- [ ] Create feature branch
- [ ] Run database migration locally
- [ ] Test manual trajectory creation
- [ ] Verify LLM processing works

### Implementation
- [x] Create `letta/letta/services/trajectory_converter.py` ✅ DONE (2025-12-31)
  - [x] `from_run()` method (converts Run+Steps+Messages to trajectory)
  - [x] `_extract_metadata()` helper (duration, tokens, tools, models)
  - [x] `_structure_turns()` helper (groups messages by step)
  - [x] `_determine_outcome()` helper (heuristic outcome scoring)
  - [x] `_message_to_dict()` helper (message serialization)
  - [x] Error handling and fallbacks

- [x] Hook into agent execution ✅ DONE (2025-12-31)
  - [x] Found agent completion hook point: `RunManager.update_run_by_id_async` line 348
  - [x] Add trajectory creation call (lines 426-434)
  - [x] Add environment variable toggle: `ENABLE_TRAJECTORY_CAPTURE`
  - [x] Handle failures gracefully (try/catch with logging)

- [ ] Tests
  - [ ] Create `letta/tests/services/test_trajectory_converter.py`
  - [ ] Test message parsing
  - [ ] Test metadata extraction
  - [ ] Test outcome determination
  - [ ] Test error handling
  - [ ] Test various conversation formats

### Documentation
- [ ] Create `letta/docs/trajectories.md`
  - [ ] Explain trajectory format
  - [ ] Show example trajectory_data
  - [ ] Document auto-capture behavior
  - [ ] Add configuration guide

### Validation
- [x] Code compiles successfully ✅ DONE (syntax check passed)
- [ ] Run with real agent conversation
- [ ] Verify trajectory created in DB
- [ ] Check LLM summary quality
- [ ] Check outcome scores are reasonable
- [ ] Verify tests pass
- [ ] Code review ready

### Commits (Planned)
- [ ] Commit 1: Add TrajectoryConverter service core
      - File: letta/services/trajectory_converter.py
      - 229 lines, complete implementation
- [ ] Commit 2: Hook trajectory capture into agent execution
      - File: letta/services/run_manager.py
      - Integration at run completion
      - Environment variable control
- [ ] Commit 3: Add tests for trajectory converter (TODO)
- [ ] Commit 4: Add trajectory documentation (TODO)

---

## Phase 2: Agent-Facing Tools (Week 2)
**Branch:** `feat/trajectory-agent-tools`
**Upstream:** ✅ Letta PR

### Implementation
- [ ] Create `letta/letta/functions/function_sets/trajectories.py`
  - [ ] `search_trajectories()` function
  - [ ] Clear docstring with examples
  - [ ] Parameter validation

- [ ] Create `letta/letta/services/tool_executor/trajectory_tool_executor.py`
  - [ ] Implement actual search logic
  - [ ] Call trajectory service
  - [ ] Format results for agent consumption
  - [ ] Handle errors gracefully

- [ ] Register tools
  - [ ] Update tool registry
  - [ ] Make available to agents (opt-in)
  - [ ] Test tool discovery

- [ ] Tests
  - [ ] Create `letta/tests/functions/test_trajectory_tools.py`
  - [ ] Test search functionality
  - [ ] Test outcome filtering
  - [ ] Test result formatting
  - [ ] Test error cases

### Documentation
- [ ] Update `letta/docs/trajectories.md`
  - [ ] Add "Using Trajectory Tools" section
  - [ ] Show example agent usage
  - [ ] Document tool parameters
  - [ ] Add troubleshooting guide

### Validation
- [ ] Agent can call search_trajectories()
- [ ] Results make sense to agent
- [ ] Filtering works correctly
- [ ] Tests pass
- [ ] Code review ready

### Commits
- [ ] Commit 1: Add trajectory function set with search_trajectories
- [ ] Commit 2: Add trajectory tool executor
- [ ] Commit 3: Register trajectory tools in tool registry
- [ ] Commit 4: Add tests for trajectory tools
- [ ] Commit 5: Document trajectory tool usage for agents

---

## Phase 3: Client Integration (letta-code) (Week 3)
**Branch:** `feat/trajectory-capture`
**Upstream:** ✅ letta-code PR

### Implementation
- [ ] Create `letta-code/src/agent/trajectory-client.ts`
  - [ ] `createTrajectory()` method
  - [ ] `updateTrajectory()` method
  - [ ] `completeTrajectory()` method
  - [ ] Error handling
  - [ ] Retry logic

- [ ] Create `letta-code/src/agent/trajectory-formatter.ts`
  - [ ] Convert messages → trajectory format
  - [ ] Keep generic (not DSF-specific)
  - [ ] Include: turns, messages, tool calls, timestamps

- [ ] Hook into message loop
  - [ ] Find message loop entry point
  - [ ] Create trajectory on session start
  - [ ] Update trajectory on each turn
  - [ ] Complete trajectory on session end
  - [ ] Handle interruptions/errors

- [ ] Add trajectory retrieval
  - [ ] Search for similar trajectories at startup
  - [ ] Inject top 2-3 as context
  - [ ] Configurable via env var

- [ ] Configuration
  - [ ] Add `ENABLE_TRAJECTORY_CAPTURE` env var
  - [ ] Add `TRAJECTORY_CONTEXT_COUNT` env var
  - [ ] Update `.env.example`

- [ ] Tests
  - [ ] Create `letta-code/src/tests/trajectory-capture.test.ts`
  - [ ] Test trajectory creation
  - [ ] Test updates during execution
  - [ ] Test completion
  - [ ] Test retrieval at startup
  - [ ] Test error handling

### Documentation
- [ ] Update `letta-code/README.md`
  - [ ] Explain trajectory capture
  - [ ] Show configuration options
  - [ ] Document how agents use context

### Validation
- [ ] Run letta-code agent
- [ ] Verify trajectory created in Letta backend
- [ ] Check trajectory data format
- [ ] Verify retrieval at next run
- [ ] Tests pass
- [ ] Code review ready

### Commits
- [ ] Commit 1: Add trajectory client for Letta API
- [ ] Commit 2: Add trajectory formatter for generic message format
- [ ] Commit 3: Hook trajectory capture into agent message loop
- [ ] Commit 4: Add trajectory retrieval at agent startup
- [ ] Commit 5: Add tests for trajectory capture
- [ ] Commit 6: Document trajectory capture in letta-code

---

## Phase 4: DSF-Specific Enhancements (Week 4)
**Branch:** `feat/dsf-trajectory-ui`
**Upstream:** ❌ DSF-only

### DSF Trajectory Formatting
- [ ] Create `letta-code/src/agent/dsf-trajectory-formatter.ts`
  - [ ] Add phase progression data
  - [ ] Add world checkpoints
  - [ ] Add story segments
  - [ ] Add quality metrics
  - [ ] Extend generic formatter

### Dashboard UI
- [ ] Create `gallery/src/components/TrajectoryDashboard.tsx`
  - [ ] List view with filters
  - [ ] Outcome score chart
  - [ ] Success/failure trends
  - [ ] Search by similarity
  - [ ] Time-based filtering

- [ ] Create `gallery/src/components/TrajectoryDetail.tsx`
  - [ ] Show full execution trace
  - [ ] Display world/story snapshots
  - [ ] Show LLM reasoning
  - [ ] Timeline view

- [ ] Create `gallery/src/api/trajectory-analytics.ts`
  - [ ] Aggregate statistics endpoint
  - [ ] Pattern detection
  - [ ] Success/failure trends

### Integration
- [ ] Add dashboard route to gallery
- [ ] Add navigation menu item
- [ ] Connect to trajectory API
- [ ] Handle loading/error states

### Validation
- [ ] Dashboard loads trajectories
- [ ] Filters work correctly
- [ ] Detail view shows full data
- [ ] Charts/graphs render
- [ ] UI is responsive

### Commits
- [ ] Commit 1: Add DSF-specific trajectory formatting
- [ ] Commit 2: Create trajectory dashboard UI component
- [ ] Commit 3: Add trajectory detail view
- [ ] Commit 4: Add trajectory analytics endpoint
- [ ] Commit 5: Integrate trajectory UI into gallery

---

## Upstream PR Preparation

### Letta PR 1: Trajectory Converter
- [ ] All Phase 1 tasks complete
- [ ] Tests pass on CI
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] Clean commit history
- [ ] PR description written
- [ ] Examples included
- [ ] Breaking changes documented (none expected)

### Letta PR 2: Agent Tools
- [ ] All Phase 2 tasks complete
- [ ] Tests pass on CI
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] Clean commit history
- [ ] PR description written
- [ ] Agent usage examples
- [ ] Tool registry integration tested

### letta-code PR: Trajectory Capture
- [ ] All Phase 3 tasks complete
- [ ] Tests pass on CI
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] Clean commit history
- [ ] PR description written
- [ ] Configuration guide
- [ ] Migration guide

---

## Pre-PR Checklist (For Each PR)

### Code Quality
- [ ] Linting passes
- [ ] Type checking passes
- [ ] All tests pass
- [ ] No console.log/print debugging
- [ ] Error handling complete
- [ ] Edge cases handled

### Documentation
- [ ] README updated
- [ ] API docs updated
- [ ] Examples provided
- [ ] Migration guide (if needed)
- [ ] Configuration guide

### Testing
- [ ] Unit tests written
- [ ] Integration tests written
- [ ] Manual testing done
- [ ] Edge cases tested
- [ ] Error paths tested

### Git
- [ ] Clean commit history
- [ ] Descriptive commit messages
- [ ] No merge commits (rebase)
- [ ] Branch up to date with main

### PR Description
- [ ] Problem statement clear
- [ ] Solution explained
- [ ] Examples included
- [ ] Breaking changes listed
- [ ] Testing instructions
- [ ] Screenshots (if UI)

---

## Testing Checklist

### Backend Testing (Phase 1-2)
- [ ] Database migration runs successfully
- [ ] Trajectory created from sample conversation
- [ ] LLM summary looks good
- [ ] Outcome score is reasonable (0.4-0.8)
- [ ] Search by similarity works
- [ ] Filter by outcome score works
- [ ] Agent can call search_trajectories()
- [ ] Tool returns useful results

### Client Testing (Phase 3)
- [ ] letta-code captures trajectory
- [ ] Trajectory appears in Letta backend
- [ ] Data format is correct
- [ ] Agent retrieves past trajectories at startup
- [ ] Context injection works
- [ ] Works with multiple runs

### DSF Testing (Phase 4)
- [ ] Dashboard loads trajectories
- [ ] Filters work (outcome, agent, date)
- [ ] Search works
- [ ] Detail view shows full trace
- [ ] Charts render correctly
- [ ] DSF-specific data captured

### End-to-End Testing
- [ ] Run DSF agent 5 times
- [ ] Verify all 5 trajectories captured
- [ ] Check summaries are good
- [ ] Verify outcome scores vary
- [ ] Test similarity search finds relevant ones
- [ ] Agent uses past examples in 6th run
- [ ] Dashboard shows patterns

---

## Post-Implementation

### Monitoring
- [ ] Add metrics for trajectory capture rate
- [ ] Add metrics for LLM processing failures
- [ ] Add metrics for agent tool usage
- [ ] Set up alerts for failures

### Documentation
- [ ] Write blog post about trajectories
- [ ] Create video demo
- [ ] Update main project README
- [ ] Add to Letta docs site

### Future Work
- [ ] Pattern analysis service
- [ ] System prompt evolution
- [ ] Trajectory clustering
- [ ] Auto-tagging/labeling
- [ ] Retention policies
- [ ] Cost optimization

---

## Blockers / Issues

### Current Blockers
- [ ] None yet

### Resolved
- [ ] (Track resolved blockers here)

---

## Notes / Learnings

- (Add notes as you go)
