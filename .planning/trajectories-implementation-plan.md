# Trajectories Implementation Plan
**Goal:** Enable agents to learn from execution history through trajectory capture, analysis, and retrieval

**Upstream Strategy:** Push generic trajectory infrastructure to Letta/letta-code. Keep DSF-specific UI separate.

**Last Updated:** 2025-12-31

---

## Current Implementation Status

### ✅ DONE: Letta Backend Infrastructure (40% Complete)

#### Database Layer
- **File:** `letta/alembic/versions/000_add_trajectories_table.py`
- **Status:** ✅ Complete
- **What works:**
  - Trajectories table with pgvector support
  - Indexes: agent_id, outcome_score, created_at, organization_id
  - Flexible JSONB `data` field for any agent type
  - SQLite fallback (no pgvector)

#### ORM & Schemas
- **Files:** `letta/letta/orm/trajectory.py`, `letta/letta/schemas/trajectory.py`
- **Status:** ✅ Complete
- **What works:**
  - `Trajectory` model with agent/org relationships
  - Pydantic schemas: Create, Update, Search, SearchResult
  - Support for embeddings, scores, summaries

#### Service Layer
- **File:** `letta/letta/services/trajectory_service.py`
- **Status:** ✅ Complete
- **What works:**
  - CRUD operations (create, get, list, update, delete)
  - Semantic search using pgvector cosine similarity
  - Filter by agent_id, outcome_score range

#### LLM Processing
- **File:** `letta/letta/services/trajectory_processing.py`
- **Status:** ⚠️ Partial (40% - missing critical input)
- **What works:**
  - `generate_searchable_summary()` - GPT-4o-mini generates 2-3 para summary
  - `score_trajectory()` - Scores 0-1 with reasoning
  - `generate_embedding()` - OpenAI text-embedding-3-small
  - Fallback handling for LLM failures
- **What's missing:**
  - ❌ No code to convert conversations → trajectory_data format
  - ❌ No automatic labeling/tagging
  - ❌ No pattern analysis across trajectories

#### REST API
- **File:** `letta/letta/server/rest_api/routers/v1/trajectories.py`
- **Status:** ✅ Complete
- **Endpoints:**
  - `POST /trajectories/` - Create
  - `GET /trajectories/{id}` - Get one
  - `GET /trajectories/` - List with filters
  - `PATCH /trajectories/{id}` - Update
  - `DELETE /trajectories/{id}` - Delete
  - `POST /trajectories/search` - Semantic search
  - `POST /trajectories/{id}/process` - Trigger LLM processing

---

### ❌ NOT DONE: Critical Missing Pieces (60%)

#### 1. Conversation → Trajectory Converter
- **Status:** ❌ Not started
- **Where:** `letta/letta/services/trajectory_converter.py` (new)
- **What's needed:**
  - Extract messages from agent execution
  - Structure into trajectory format
  - Extract metadata (duration, tools, outcome)
  - Determine completion status

#### 2. Agent-Facing Tools
- **Status:** ❌ Not started
- **Where:** `letta/letta/functions/function_sets/trajectories.py` (new)
- **What's needed:**
  - `search_trajectories()` - Agent searches past runs by outcome
  - `get_successful_examples()` - Retrieve high-scoring trajectories
  - `analyze_failure_patterns()` - Learn from low-scoring trajectories

#### 3. Client Integration (letta-code)
- **Status:** ❌ Not started
- **Where:** `letta-code/src/` (multiple files)
- **What's needed:**
  - Hook into message loop to capture execution
  - Create trajectory on agent start
  - Update trajectory as execution progresses
  - Send to Letta backend API
  - Agent retrieves trajectories at start of new runs

#### 4. Dashboard/Analytics (DSF-specific, not upstream)
- **Status:** ❌ Not started
- **Where:** New gallery UI component
- **What's needed:**
  - Visualize trajectory patterns
  - Success/failure rate charts
  - Filter by outcome, agent, time
  - View execution timelines

#### 5. System Prompt Evolution
- **Status:** ❌ Not started
- **Where:** TBD (future phase)
- **What's needed:**
  - Analyze trajectory patterns
  - Generate system prompt improvements
  - A/B test prompt variants

---

## Implementation Phases

### Phase 1: Conversation → Trajectory Converter (Week 1)
**Goal:** Enable automatic trajectory creation from agent executions
**Upstream Target:** Letta backend
**Branch:** `feat/trajectory-converter`

#### Tasks:
1. **Create `TrajectoryConverter` service**
   - File: `letta/letta/services/trajectory_converter.py`
   - Methods:
     - `from_messages(messages, agent_id, metadata)` → TrajectoryCreate
     - `from_run(run_id)` → TrajectoryCreate (if run system exists)
     - `extract_metadata(messages)` → dict
     - `determine_outcome(messages)` → success/partial/failure
   - Keep generic - works for ANY agent type

2. **Add automatic trajectory capture hook**
   - File: `letta/letta/server/server.py` or agent execution code
   - On agent execution complete → create trajectory
   - Optional: environment var to enable/disable

3. **Write tests**
   - File: `letta/tests/services/test_trajectory_converter.py`
   - Test various conversation formats
   - Test metadata extraction
   - Test outcome determination

4. **Documentation**
   - File: `letta/docs/trajectories.md`
   - Explain trajectory format
   - Show example trajectory_data structure
   - Document auto-capture behavior

#### Commit Structure:
```
commit 1: Add TrajectoryConverter service with message parsing
commit 2: Add metadata extraction and outcome determination
commit 3: Hook trajectory capture into agent execution
commit 4: Add tests for trajectory converter
commit 5: Add trajectory documentation
```

#### Upstream Ready: ✅ Yes (generic, no DSF-specific code)

---

### Phase 2: Agent-Facing Tools (Week 2)
**Goal:** Enable agents to search and learn from past trajectories
**Upstream Target:** Letta backend
**Branch:** `feat/trajectory-agent-tools`

#### Tasks:
1. **Create trajectory function set**
   - File: `letta/letta/functions/function_sets/trajectories.py`
   - Functions:
     ```python
     def search_trajectories(
         agent_state: AgentState,
         query: str,
         min_score: Optional[float] = None,
         max_score: Optional[float] = None,
         limit: int = 5
     ) -> str:
         """
         Search past trajectories by similarity and outcome score.

         Use this to find similar situations and learn from past successes/failures.

         Examples:
           - Find successes: search_trajectories("user wants X", min_score=0.7)
           - Find failures: search_trajectories("user wants X", max_score=0.4)
         """
     ```

2. **Create tool executor**
   - File: `letta/letta/services/tool_executor/trajectory_tool_executor.py`
   - Implement actual API calls
   - Format results for agent consumption

3. **Register tools**
   - Update tool registry to include trajectory tools
   - Make available to all agents (opt-in via agent config)

4. **Write tests**
   - File: `letta/tests/functions/test_trajectory_tools.py`
   - Test search functionality
   - Test filtering by score
   - Test result formatting

5. **Documentation**
   - Update `letta/docs/trajectories.md`
   - Add "Using Trajectory Tools" section
   - Show example agent usage

#### Commit Structure:
```
commit 1: Add trajectory function set with search_trajectories
commit 2: Add trajectory tool executor
commit 3: Register trajectory tools in tool registry
commit 4: Add tests for trajectory tools
commit 5: Document trajectory tool usage for agents
```

#### Upstream Ready: ✅ Yes (generic tool design)

---

### Phase 3: Client Integration (letta-code) (Week 3)
**Goal:** Capture trajectories during letta-code agent execution
**Upstream Target:** letta-code
**Branch:** `feat/trajectory-capture`

#### Tasks:
1. **Add trajectory capture to message loop**
   - File: `letta-code/src/agent/index.ts` or message handling code
   - Create trajectory on agent session start
   - Update trajectory with each turn
   - Mark complete on session end

2. **Create trajectory client**
   - File: `letta-code/src/agent/trajectory-client.ts`
   - Methods:
     - `createTrajectory(agentId, initialData)`
     - `updateTrajectory(trajectoryId, turnData)`
     - `completeTrajectory(trajectoryId, outcome)`
   - Handle API errors gracefully

3. **Structure trajectory data generically**
   - File: `letta-code/src/agent/trajectory-formatter.ts`
   - Convert letta-code messages → trajectory format
   - Keep generic (not DSF-specific)
   - Include: turns, messages, tool calls, timestamps

4. **Add trajectory retrieval at startup**
   - On new agent run, search for similar past trajectories
   - Inject top 2-3 successful examples as context
   - Configurable via environment var

5. **Write tests**
   - File: `letta-code/src/tests/trajectory-capture.test.ts`
   - Test trajectory creation/updates
   - Test formatting
   - Test retrieval integration

6. **Documentation**
   - File: `letta-code/README.md` update
   - Explain trajectory capture
   - Show how to enable/disable
   - Show how agents use trajectory context

#### Commit Structure:
```
commit 1: Add trajectory client for Letta API
commit 2: Add trajectory formatter for generic message format
commit 3: Hook trajectory capture into agent message loop
commit 4: Add trajectory retrieval at agent startup
commit 5: Add tests for trajectory capture
commit 6: Document trajectory capture in letta-code
```

#### Upstream Ready: ✅ Yes (generic, framework-level feature)

---

### Phase 4: DSF-Specific Enhancements (Week 4)
**Goal:** Add DSF-specific trajectory structure and UI
**Upstream Target:** ❌ None (stays in dsf-agent repo)
**Branch:** `feat/dsf-trajectory-ui`

#### Tasks:
1. **Enhance trajectory data for DSF**
   - File: `letta-code/src/agent/dsf-trajectory-formatter.ts` (DSF-specific)
   - Add DSF-specific fields:
     - Phase progression (questions → research → world → story)
     - World checkpoints
     - Story segments
     - Quality metrics (consistency, depth, abstraction)

2. **Create trajectory dashboard UI**
   - File: `gallery/src/components/TrajectoryDashboard.tsx` (new)
   - Features:
     - List all trajectories
     - Filter by outcome score
     - View execution timeline
     - Show success/failure patterns
     - Search by similarity

3. **Add trajectory detail view**
   - File: `gallery/src/components/TrajectoryDetail.tsx` (new)
   - Show full execution trace
   - Display world/story snapshots
   - Show LLM reasoning at each step

4. **Add analytics endpoint**
   - File: `gallery/src/api/trajectory-analytics.ts` (new)
   - Aggregate statistics
   - Pattern detection
   - Success/failure trends over time

#### Commit Structure:
```
commit 1: Add DSF-specific trajectory formatting
commit 2: Create trajectory dashboard UI component
commit 3: Add trajectory detail view
commit 4: Add trajectory analytics endpoint
commit 5: Integrate trajectory UI into gallery
```

#### Upstream Ready: ❌ No (DSF-specific UI and formatting)

---

### Phase 5: Advanced Features (Future)
**Goal:** Pattern analysis and system prompt evolution
**Timeline:** After Phase 1-4 complete and proven

#### Future Tasks:
1. **Pattern Analysis Service**
   - Analyze trajectories for common patterns
   - Identify recurring failure modes
   - Extract success strategies

2. **System Prompt Evolution**
   - Generate prompt improvements from patterns
   - A/B test prompt variants
   - Track improvement over time

3. **Trajectory Clustering**
   - Group similar trajectories
   - Find representative examples
   - Detect anomalies

4. **LLM Tagging/Labeling**
   - Auto-generate tags for trajectories
   - Classify by task type
   - Theme extraction

---

## Technical Decisions

### 1. Trajectory Data Format (Generic)
```json
{
  "agent_id": "agent-uuid",
  "data": {
    "metadata": {
      "start_time": "ISO-8601",
      "end_time": "ISO-8601",
      "duration_ms": 45000,
      "message_count": 12,
      "tool_calls": 8,
      "outcome": "success" | "partial_success" | "failure"
    },
    "turns": [
      {
        "turn_id": 1,
        "timestamp": "ISO-8601",
        "user_message": "...",
        "assistant_messages": [
          {
            "role": "assistant",
            "content": "...",
            "tool_calls": [...]
          }
        ],
        "tool_results": [...]
      }
    ],
    "initial_context": "...",
    "final_state": "..."
  }
}
```

### 2. When to Create Trajectories
- **On agent session end** (preferred for completeness)
- OR **Streaming updates** during execution (for real-time)
- Configurable via `ENABLE_TRAJECTORY_CAPTURE=true`

### 3. Storage Strategy
- Store in Postgres with pgvector
- Fallback to SQLite for dev (no similarity search)
- Retention: Keep all for now, add pruning later

### 4. Agent Search Strategy
- **At startup:** Search for top 3 similar successful trajectories
- **Inject as context:** "Here are similar situations and how they succeeded"
- **Agent decides:** Whether to use the examples (not forced)

---

## Upstream Contribution Strategy

### Letta Backend PRs

#### PR 1: Trajectory Converter Service
- **Title:** "feat: Add trajectory converter for automatic capture from conversations"
- **Files:**
  - `letta/letta/services/trajectory_converter.py`
  - `letta/tests/services/test_trajectory_converter.py`
  - `letta/docs/trajectories.md`
- **Why upstream ready:** Generic converter works for any agent framework
- **Size:** ~500 lines

#### PR 2: Agent Trajectory Tools
- **Title:** "feat: Add trajectory search tools for agent self-improvement"
- **Files:**
  - `letta/letta/functions/function_sets/trajectories.py`
  - `letta/letta/services/tool_executor/trajectory_tool_executor.py`
  - `letta/tests/functions/test_trajectory_tools.py`
  - Update docs
- **Why upstream ready:** Generic tools, useful for all agents
- **Size:** ~400 lines

### Letta-code PR

#### PR 3: Trajectory Capture Integration
- **Title:** "feat: Capture agent execution trajectories for learning"
- **Files:**
  - `letta-code/src/agent/trajectory-client.ts`
  - `letta-code/src/agent/trajectory-formatter.ts`
  - Integration into message loop
  - Tests and docs
- **Why upstream ready:** Framework-level feature, not app-specific
- **Size:** ~600 lines

---

## Testing Strategy

### Unit Tests
- Trajectory converter (message parsing, metadata extraction)
- Trajectory tools (search, filtering, formatting)
- Trajectory client (API calls, error handling)

### Integration Tests
- End-to-end trajectory capture during agent run
- Agent retrieval and use of past trajectories
- LLM processing pipeline

### Manual Testing
- Run DSF agent multiple times
- Verify trajectories captured correctly
- Test agent learns from past runs
- Verify dashboard shows patterns

---

## Success Metrics

### Phase 1-2 (Backend)
- ✅ Trajectories auto-captured from all agent runs
- ✅ LLM summaries generated correctly
- ✅ Outcome scores calibrated (0.4-0.8 range)
- ✅ Agent can search and retrieve trajectories

### Phase 3 (Client)
- ✅ letta-code captures trajectories seamlessly
- ✅ Agents retrieve relevant past examples
- ✅ Trajectory data formatted generically
- ✅ <5% capture failure rate

### Phase 4 (DSF UI)
- ✅ Dashboard shows all DSF trajectories
- ✅ Patterns visible (success/failure trends)
- ✅ Detail view shows full execution trace

### Phase 5 (Advanced)
- ✅ System prompt improvements from patterns
- ✅ Measurable quality increase over time

---

## Open Questions

### Q1: When to trigger LLM processing?
**Options:**
- Immediately on trajectory creation (blocking)
- Async background job (preferred)
- On-demand via `/process` endpoint
- Batch processing (hourly)

**Decision:** Start with background job, add batch later

### Q2: How to handle trajectory size?
**Options:**
- Truncate messages (keep first/last N)
- Compress/summarize long tool outputs
- Store full data, summarize for embeddings

**Decision:** Store full data, truncate for LLM processing (2000 chars)

### Q3: Agent tool adoption strategy?
**Options:**
- Auto-inject in all agents (intrusive)
- Opt-in via agent config (preferred)
- Opt-in via system prompt mention

**Decision:** Opt-in via agent config, document in system prompt examples

### Q4: Migration path for existing Letta users?
- Backward compatible (new feature, doesn't break existing)
- Off by default (opt-in with env var)
- Migration guide for enabling

---

## Timeline

| Phase | Duration | Deliverable | Upstream |
|-------|----------|-------------|----------|
| Phase 1 | Week 1 | Trajectory converter | ✅ Letta PR |
| Phase 2 | Week 2 | Agent tools | ✅ Letta PR |
| Phase 3 | Week 3 | Client integration | ✅ letta-code PR |
| Phase 4 | Week 4 | DSF UI & analytics | ❌ DSF-only |
| Phase 5 | Future | Advanced features | TBD |

**Total:** 4 weeks for core functionality + UI

---

## Dependencies

### External:
- OpenAI API (for summaries, scores, embeddings)
- pgvector extension (Postgres)

### Internal:
- Letta backend (existing trajectory infrastructure)
- letta-code message loop
- DSF gallery server

---

## Risk Mitigation

### Risk 1: LLM processing cost
- **Mitigation:** Use GPT-4o-mini (cheap), batch processing
- **Fallback:** Heuristic scoring without LLM

### Risk 2: Storage cost (many trajectories)
- **Mitigation:** Retention policy (prune old low-value trajectories)
- **Fallback:** Sampling (capture 50% of runs)

### Risk 3: Agent ignores trajectory context
- **Mitigation:** Test with prompts emphasizing learning from examples
- **Fallback:** Explicit system prompt instruction

### Risk 4: Upstream rejection
- **Mitigation:** Engage maintainers early, share design doc
- **Fallback:** Keep in fork, maintain separate

---

## Next Steps

1. **Review this plan** - Get alignment on approach
2. **Set up branches** - Create feature branches for each phase
3. **Start Phase 1** - Implement trajectory converter
4. **Test with DSF** - Validate approach with real usage
5. **Iterate** - Refine based on learnings
6. **Upstream PRs** - Submit when proven

---

## Notes

- **Keep it generic:** Every upstream contribution must work for ANY agent
- **Document well:** Clear examples, docstrings, README updates
- **Test thoroughly:** Unit + integration tests for all new code
- **Engage early:** Share design with Letta maintainers before large PRs
- **Iterate in public:** Use DSF as reference implementation to prove value
