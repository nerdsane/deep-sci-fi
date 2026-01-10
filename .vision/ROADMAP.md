# Project Roadmap

**Type:** EVOLVING
**Created:** 2026-01-09
**Last Updated:** 2026-01-09
**Staleness Check:** Ask user if >30 days since update

---

## Overview

High-level phases for Deep Sci-Fi development. This document tracks where we are and where we're going.

---

## Current State: ~45% Complete

**What Works:**
- Database schema with two-tier agent support
- Authentication (email/password + Google OAuth)
- World/Story CRUD via tRPC
- Letta SDK client initialization
- User Agent creation (orchestrator)
- World Agent creation
- Message routing based on context
- Streaming message responses
- Memory block system

**What Doesn't Work Yet:**
- Chat UI integration
- User Agent tools (world_draft_generator needs LLM)
- World Agent tools (not ported from CLI)
- Story viewer/canvas
- Image generation
- Agent-driven UI components

---

## Phase Overview

| Phase | Focus | Status |
|-------|-------|--------|
| 1. Foundation | Database, auth, basic CRUD | ✅ Complete |
| 2A. Agent Architecture | Two-tier agents, routing | ✅ Complete |
| 2A-SDK. Letta Integration | SDK connection, streaming | ✅ Complete |
| 2B. UI Integration | Chat panels, world views | 🔄 Next |
| 2C. World Agent Tools | Port tools from CLI | ⏳ Pending |
| 3. Story Experience | Visual novel, canvas | ⏳ Pending |
| 4. Scientific Grounding | Eval tools integration | ⏳ Pending |
| 5. Polish & Deploy | Testing, CI/CD, production | ⏳ Pending |

---

## Phase 2B: UI Integration (Current Target)

### Goals
- Wire up chat panels to agents
- Enable chat-based world creation
- Build story viewing experience

### Key Tasks
1. Add ChatPanel to worlds list (User Agent)
2. Add ChatPanel to world view (World Agent)
3. Build story viewer page with segments
4. Handle streaming responses in UI
5. Show tool calls and reasoning

### Success Criteria
- [ ] User can chat with User Agent at /worlds
- [ ] User can request world drafts via chat
- [ ] User can chat with World Agent in a world
- [ ] Streaming responses render smoothly
- [ ] Tool results display appropriately

---

## Phase 2C: World Agent Tools

### Goals
- Port essential tools from letta-code
- Enable full world/story management via agents

### Key Tasks
1. Implement `world_draft_generator` (LLM-based)
2. Port `world_manager` (save/load/diff/update)
3. Port `story_manager` (create/save/branch)
4. Port `canvas_ui` (agent-driven components)
5. Stub `image_generator` for later

### Success Criteria
- [ ] Agent can generate world drafts from prompts
- [ ] Agent can save and load worlds
- [ ] Agent can create and manage stories
- [ ] Agent can render UI components

---

## Phase 3: Story Experience

### Goals
- Rich story viewing with visual novel elements
- Agent-assisted story writing
- Canvas integration

### Key Tasks
1. Visual novel reader with segments
2. Character portraits and backgrounds
3. Audio integration (ambient, music)
4. Story editor mode
5. Agent-driven UI in canvas

### Success Criteria
- [ ] Stories play as visual novels
- [ ] Audio enhances immersion
- [ ] Agent can help write stories
- [ ] Canvas renders agent-specified components

---

## Phase 4: Scientific Grounding Tools

### Goals
- Integrate evaluation tools from Letta
- Enable agents to assess scientific plausibility
- Story coherence validation

### Key Tasks
1. Wire up existing Letta eval tools
2. Add scientific grounding tools (assess, trace, validate)
3. Add story coherence tools (add_event, validate_coherence)
4. Agent self-evaluation prompts

### Success Criteria
- [ ] Agent can assess scientific plausibility
- [ ] Agent can trace causal chains
- [ ] Agent can validate cross-domain consistency
- [ ] Stories maintain coherence across perspectives

---

## Phase 5: Polish & Deploy

### Goals
- Production-ready deployment
- Testing infrastructure
- CI/CD pipeline

### Key Tasks
1. Docker configuration for production
2. Proper database migrations
3. Test suite (unit, integration, E2E)
4. CI/CD with GitHub Actions
5. Documentation

### Success Criteria
- [ ] One-command deployment
- [ ] Tests pass in CI
- [ ] No manual steps required
- [ ] Documentation complete

---

## Future Enhancements (Post-MVP)

| Enhancement | Description |
|-------------|-------------|
| CLI Integration | letta-code connects to web agents |
| Multi-user Collaboration | Real-time world editing |
| Advanced Image Gen | Scene illustrations, character art |
| Export Options | EPUB, PDF, audiobook |
| Community Features | Share worlds, fork stories |

---

## Architecture Context

### Three-Tier Component Model

```
Letta (Python Backend)      - Agent execution, evaluation tools
Letta-Code (TypeScript)     - CLI tools, Canvas server
Letta-UI (TypeScript)       - Web dashboard
```

### Two-Tier Agent System

```
User Agent (Orchestrator)   - One per user, handles meta-tasks
World Agent                 - One per world, handles domain work
```

### Key Ports

| Service | Port |
|---------|------|
| Letta Server | 8283 |
| Web App | 3000 |
| Canvas | 3030 |
| Agent Bus | 8284 |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-07 | Two-tier agents | User needs orchestrator before any worlds exist |
| 2026-01-07 | Letta SDK integration | Enables persistence, streaming, tools |
| 2026-01-09 | TigerStyle harness | Reduce drift, ensure quality |

---

## Notes

- This roadmap is intentionally high-level
- Detailed task breakdowns go in `.progress/` plans
- Update this document when phases complete
- Check staleness if >30 days old
