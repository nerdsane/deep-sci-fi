# Trajectories Commit Strategy
**How to structure commits for clean upstream PRs**

---

## Principles

1. **Atomic commits** - Each commit does one thing
2. **Logical progression** - Commits build on each other
3. **Passing tests** - Every commit should compile and pass tests
4. **Clear messages** - Descriptive commit messages with context
5. **No DSF-specific code in upstream commits**

---

## Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `chore`: Changes to build process or auxiliary tools

### Scopes (for trajectories):
- `trajectories`: General trajectory functionality
- `converter`: Trajectory converter service
- `tools`: Agent-facing tools
- `api`: REST API endpoints
- `client`: letta-code client integration
- `ui`: UI components (DSF-only)

### Example:
```
feat(trajectories): add trajectory converter service

Implement TrajectoryConverter to automatically create trajectories
from agent conversations. Supports extracting metadata, determining
outcomes, and handling various message formats.

- Add from_messages() method to convert message list to trajectory
- Add extract_metadata() to compute duration, tool usage
- Add determine_outcome() with heuristic scoring
- Include fallback handling for edge cases

Refs: #123
```

---

## Phase 1: Trajectory Converter

### Branch: `feat/trajectory-converter`

#### Commit 1: Add TrajectoryConverter service core
```
feat(converter): add trajectory converter service

Implement core TrajectoryConverter service to create trajectories
from agent conversations. This enables automatic capture of agent
execution traces.

- Add TrajectoryConverter class
- Add from_messages() method
- Add basic message parsing
- Add TrajectoryData structure

Files:
+ letta/letta/services/trajectory_converter.py
```

#### Commit 2: Add metadata extraction
```
feat(converter): add metadata extraction and outcome detection

Enhance TrajectoryConverter with metadata computation and outcome
determination to enrich trajectory data.

- Add extract_metadata() for duration, message count, tool usage
- Add determine_outcome() with heuristic scoring
- Support for user feedback signals
- Handle edge cases (empty conversations, errors)

Files:
M letta/letta/services/trajectory_converter.py
```

#### Commit 3: Hook converter into agent execution
```
feat(trajectories): auto-capture trajectories from agent runs

Integrate TrajectoryConverter into agent execution flow to
automatically create trajectories when agents complete tasks.

- Add trajectory capture hook in agent completion
- Add ENABLE_TRAJECTORY_CAPTURE environment variable
- Graceful failure handling (log errors, don't break agents)
- Background task to avoid blocking agent response

Files:
M letta/letta/server/server.py (or relevant agent execution file)
M letta/letta/services/trajectory_converter.py
```

#### Commit 4: Add comprehensive tests
```
test(converter): add trajectory converter tests

Add comprehensive test coverage for TrajectoryConverter service.

- Test message parsing with various formats
- Test metadata extraction accuracy
- Test outcome determination heuristics
- Test error handling and edge cases
- Test integration with trajectory service

Files:
+ letta/tests/services/test_trajectory_converter.py
```

#### Commit 5: Add documentation
```
docs(trajectories): add trajectory system documentation

Document trajectory system architecture, usage, and configuration.

- Explain trajectory data format
- Show example trajectory creation
- Document auto-capture configuration
- Add troubleshooting guide
- Include examples for different agent types

Files:
+ letta/docs/trajectories.md
M README.md (add link to trajectories.md)
```

---

## Phase 2: Agent Tools

### Branch: `feat/trajectory-agent-tools`

#### Commit 1: Add trajectory function set
```
feat(tools): add trajectory search tools for agents

Implement trajectory function set to enable agents to search
and learn from past executions.

- Add search_trajectories() function
- Support filtering by outcome score
- Support similarity search by query
- Clear docstrings with examples

Files:
+ letta/letta/functions/function_sets/trajectories.py
```

#### Commit 2: Add tool executor
```
feat(tools): add trajectory tool executor

Implement executor for trajectory tools to handle API calls
and format results for agent consumption.

- Add TrajectoryToolExecutor class
- Implement search logic with TrajectoryService
- Format results clearly for agents
- Handle errors gracefully

Files:
+ letta/letta/services/tool_executor/trajectory_tool_executor.py
```

#### Commit 3: Register trajectory tools
```
feat(tools): register trajectory tools in tool system

Make trajectory tools available to agents through tool registry.

- Add trajectory tools to registry
- Enable opt-in via agent configuration
- Test tool discovery and execution

Files:
M letta/letta/functions/function_sets/__init__.py (or registry file)
M letta/letta/services/tool_executor/__init__.py
```

#### Commit 4: Add tool tests
```
test(tools): add trajectory tool tests

Add comprehensive test coverage for trajectory tools.

- Test search_trajectories() functionality
- Test outcome filtering
- Test similarity search
- Test result formatting
- Test error handling

Files:
+ letta/tests/functions/test_trajectory_tools.py
```

#### Commit 5: Document trajectory tools
```
docs(tools): document trajectory tool usage for agents

Document how agents can use trajectory tools to learn from
past executions.

- Add "Agent Tools" section to trajectories.md
- Show example agent usage patterns
- Document tool parameters
- Add success/failure search examples

Files:
M letta/docs/trajectories.md
```

---

## Phase 3: Client Integration

### Branch: `feat/trajectory-capture`

#### Commit 1: Add trajectory API client
```
feat(client): add trajectory API client for letta-code

Implement client to interact with Letta trajectory API from
letta-code agent execution.

- Add TrajectoryClient class
- Implement createTrajectory() method
- Implement updateTrajectory() method
- Implement completeTrajectory() method
- Add error handling and retry logic

Files:
+ letta-code/src/agent/trajectory-client.ts
```

#### Commit 2: Add trajectory formatter
```
feat(client): add generic trajectory formatter

Implement formatter to convert letta-code messages into
trajectory format for Letta backend.

- Add TrajectoryFormatter class
- Convert messages to trajectory turns
- Extract metadata (duration, tools, timestamps)
- Keep generic (works for any agent)

Files:
+ letta-code/src/agent/trajectory-formatter.ts
```

#### Commit 3: Hook trajectory capture into message loop
```
feat(client): capture trajectories during agent execution

Integrate trajectory capture into letta-code message loop
to automatically record agent executions.

- Create trajectory on session start
- Update trajectory on each turn
- Complete trajectory on session end
- Handle interruptions and errors gracefully
- Add ENABLE_TRAJECTORY_CAPTURE env var

Files:
M letta-code/src/agent/index.ts (or message handler)
M letta-code/src/agent/trajectory-client.ts
```

#### Commit 4: Add trajectory retrieval at startup
```
feat(client): retrieve past trajectories at agent startup

Enable agents to learn from past executions by retrieving
similar successful trajectories at startup.

- Search for similar trajectories when agent starts
- Inject top 2-3 as context
- Add TRAJECTORY_CONTEXT_COUNT env var
- Configurable (opt-in)

Files:
M letta-code/src/agent/index.ts
M letta-code/src/agent/trajectory-client.ts
```

#### Commit 5: Add client tests
```
test(client): add trajectory capture tests

Add comprehensive test coverage for trajectory capture
functionality.

- Test trajectory creation
- Test updates during execution
- Test completion handling
- Test retrieval at startup
- Test error handling and retries

Files:
+ letta-code/src/tests/trajectory-capture.test.ts
```

#### Commit 6: Document trajectory capture
```
docs(client): document trajectory capture in letta-code

Document how trajectory capture works in letta-code and
how to configure it.

- Explain automatic capture
- Show configuration options
- Document environment variables
- Add troubleshooting guide

Files:
M letta-code/README.md
+ letta-code/docs/trajectories.md (optional)
M letta-code/.env.example
```

---

## Phase 4: DSF-Specific (Not Upstream)

### Branch: `feat/dsf-trajectory-ui`

#### Commit 1: Add DSF trajectory formatter
```
feat(dsf): add DSF-specific trajectory formatting

Extend generic trajectory formatter with DSF-specific data
(phases, worlds, stories).

- Add DsfTrajectoryFormatter extending base formatter
- Include phase progression
- Include world checkpoints
- Include story segments
- Add quality metrics

Files:
+ letta-code/src/agent/dsf-trajectory-formatter.ts
M letta-code/src/agent/index.ts (use DSF formatter)
```

#### Commit 2: Create trajectory dashboard UI
```
feat(ui): add trajectory dashboard component

Create dashboard UI to visualize and explore trajectories.

- Add TrajectoryDashboard component
- List view with filters
- Outcome score charts
- Success/failure trends
- Search by similarity

Files:
+ gallery/src/components/TrajectoryDashboard.tsx
+ gallery/src/styles/trajectory-dashboard.css
```

#### Commit 3: Add trajectory detail view
```
feat(ui): add trajectory detail view

Create detailed view to show full trajectory execution trace.

- Add TrajectoryDetail component
- Show full execution timeline
- Display world/story snapshots
- Show LLM reasoning at each step
- Link to related trajectories

Files:
+ gallery/src/components/TrajectoryDetail.tsx
+ gallery/src/styles/trajectory-detail.css
```

#### Commit 4: Add trajectory analytics API
```
feat(ui): add trajectory analytics endpoint

Create API endpoint for trajectory aggregate statistics
and patterns.

- Add analytics endpoint
- Compute success/failure rates
- Detect common patterns
- Generate trend data

Files:
+ gallery/src/api/trajectory-analytics.ts
```

#### Commit 5: Integrate trajectory UI into gallery
```
feat(ui): integrate trajectory dashboard into gallery

Wire up trajectory UI to gallery navigation and routing.

- Add /trajectories route
- Add navigation menu item
- Connect to backend API
- Add loading states
- Add error handling

Files:
M gallery/src/App.tsx (or router)
M gallery/src/components/Navigation.tsx
M gallery/src/api/client.ts
```

---

## PR Submission Order

### PR 1: Letta Backend - Trajectory Converter
**Target:** Letta repository
**Branch:** `feat/trajectory-converter`
**Base:** `main`

**Commits:**
1. Add TrajectoryConverter service core
2. Add metadata extraction and outcome detection
3. Hook converter into agent execution
4. Add comprehensive tests
5. Add documentation

**Checklist before submitting:**
- [ ] All commits are clean and logical
- [ ] Tests pass
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] PR description written

---

### PR 2: Letta Backend - Agent Tools
**Target:** Letta repository
**Branch:** `feat/trajectory-agent-tools`
**Base:** `main` (or after PR 1 merged)

**Commits:**
1. Add trajectory function set
2. Add tool executor
3. Register trajectory tools
4. Add tool tests
5. Document trajectory tools

**Checklist before submitting:**
- [ ] All commits are clean and logical
- [ ] Tests pass
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] PR description written

---

### PR 3: letta-code - Trajectory Capture
**Target:** letta-code repository
**Branch:** `feat/trajectory-capture`
**Base:** `main` (or after backend PRs merged)

**Commits:**
1. Add trajectory API client
2. Add generic trajectory formatter
3. Hook trajectory capture into message loop
4. Add trajectory retrieval at startup
5. Add client tests
6. Document trajectory capture

**Checklist before submitting:**
- [ ] All commits are clean and logical
- [ ] Tests pass
- [ ] Documentation complete
- [ ] No DSF-specific code
- [ ] PR description written

---

## Commit Hygiene

### Before Committing:
- [ ] Run linter
- [ ] Run type checker
- [ ] Run tests
- [ ] Remove debug code
- [ ] Add docstrings
- [ ] Update relevant docs

### Commit Message Checklist:
- [ ] Type and scope present
- [ ] Subject is imperative mood ("add" not "added")
- [ ] Subject is under 50 chars
- [ ] Body explains why, not what
- [ ] Body wraps at 72 chars
- [ ] Footer includes issue refs if applicable

### Before Pushing:
- [ ] Rebase on latest main
- [ ] Squash fixup commits
- [ ] Verify commit messages
- [ ] Verify no merge commits
- [ ] Run full test suite

---

## Rebase Strategy

When upstream changes require rebase:

```bash
# Update main
git checkout main
git pull upstream main

# Rebase feature branch
git checkout feat/trajectory-converter
git rebase main

# If conflicts, resolve and continue
git rebase --continue

# Force push (your branch only!)
git push --force-with-lease origin feat/trajectory-converter
```

---

## Squashing Commits

To clean up commits before PR:

```bash
# Interactive rebase last N commits
git rebase -i HEAD~5

# Mark commits as:
# pick (keep)
# squash (merge into previous)
# fixup (merge, discard message)
# reword (edit message)

# Save and close editor
# Resolve conflicts if any
# Force push
git push --force-with-lease origin feat/trajectory-converter
```

---

## PR Description Template

```markdown
## Description
[Clear description of what this PR does]

## Motivation
[Why is this change needed? What problem does it solve?]

## Changes
- [List of changes]
- [Be specific]

## Examples
[Code examples showing how to use the new feature]

## Testing
[How did you test this? How can reviewers test?]

## Checklist
- [ ] Tests added/updated
- [ ] Documentation added/updated
- [ ] Backward compatible (or breaking changes documented)
- [ ] All tests pass
- [ ] Linting passes

## Screenshots
[If applicable]

## Related Issues
Closes #XXX
```

---

## Notes

- **Keep PRs focused** - One feature per PR
- **Small is better** - Easier to review
- **Test everything** - No untested code
- **Document as you go** - Don't leave it for later
- **Engage early** - Share design before large PRs
