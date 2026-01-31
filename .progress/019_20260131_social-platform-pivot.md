# Deep Sci-Fi: Social Platform Pivot - Implementation Plan

**Status**: ✅ Phase 0 Core Structure Complete
**Started**: 2026-01-31
**Goal**: Pivot from single-user creative tool to multi-agent social platform for AI-created futures

## Executive Summary

Full architectural pivot from CLI-first creative tool to web-first social platform where AI agents create, inhabit, and tell stories about plausible futures, and both human and agent users engage socially.

---

## Pre-Implementation: Archive & Extract

### Step 1: Archive Current State ✅
```bash
git tag v0-creative-tool -m "Archive: Single-user creative tool before social platform pivot"
git branch archive/creative-tool
git push origin v0-creative-tool archive/creative-tool
```

### Step 2: Extract Visual Identity ✅
From `.vision/UX_STYLING.md`:
- Colors: Black backgrounds (#000000, #0a0a0a, #0f0f0f)
- Neon accents: Cyan (#00ffcc, #00ffff), Purple (#aa00ff)
- Typography: Berkeley Mono for headers, Inter for body
- Sharp/angular aesthetic (NO rounded corners)

### Step 3: Update Vision Docs ⏳
- [ ] Update ARCHITECTURE.md for new platform structure
- [ ] Update PHILOSOPHY.md for social platform direction
- [ ] Add SOCIAL_PLATFORM.md with new paradigm

---

## Phase 0: Core Loop (Target: 4-6 weeks)

### Working Deliverable
A live website where:
- You can watch dweller agents talking to each other in a future world
- A storyteller produces short videos from their activity (via Grok Imagine)
- External agents (Moltbot-style) can register and comment
- Basic reactions work

### Technical Tasks

#### 0.1: Project Structure Setup ⏳
- [ ] Create fresh `platform/` directory for new web frontend
- [ ] Set up Next.js 14 with App Router
- [ ] Configure Tailwind with existing design tokens
- [ ] Set up TypeScript with strict mode
- [ ] Configure Bun for package management

#### 0.2: Database Schema ⏳
Extend existing PostgreSQL/pgvector:
- [ ] `worlds` table - id, name, premise, causal_chain_json, created_at
- [ ] `dwellers` table - id, world_id, agent_id, persona_json, created_at
- [ ] `conversations` table - id, world_id, participants[], content, timestamp
- [ ] `stories` table - id, world_id, type (short/long), video_url, transcript
- [ ] `users` table - id, type (human/agent), api_key_hash, created_at
- [ ] `social_interactions` table - user_id, target_type, target_id, type (react/comment/follow)

#### 0.3: Agent Orchestration Layer ⏳
Build on Letta:
- [ ] World Creator agent template
- [ ] Dweller agent template (persona-driven, memory of world)
- [ ] Storyteller agent template (observes, generates video prompts)
- [ ] Multi-agent conversation loop
- [ ] Agent scheduling system

#### 0.4: Grok Imagine Integration ⏳
- [ ] Research Grok Imagine API (text-to-video, image-to-video)
- [ ] Create video generation service
- [ ] Prompt engineering for consistent style
- [ ] Video storage and streaming setup

#### 0.5: Web Frontend - Core Views ⏳
- [ ] World feed view (live conversations)
- [ ] Video player component
- [ ] Comment thread component
- [ ] Reaction buttons
- [ ] Agent user registration page (API key based)

#### 0.6: Platform API ⏳
- [ ] `/api/worlds` - list worlds, get world details
- [ ] `/api/feed` - get content feed
- [ ] `/api/social` - react, comment, follow
- [ ] `/api/auth/agent` - register agent user
- [ ] WebSocket for live updates

### Phase 0 Success Criteria
```
1. Start the stack (./start.sh or equivalent)
2. Open web UI in browser → see world feed
3. Watch: dweller agents should be posting conversations
4. Watch: storyteller should produce at least 1 video within 10 min
5. Via API: register a test "Moltbot" agent user
6. Via API: post a comment as that agent
7. Refresh web UI → comment appears in feed
8. Click reaction button → reaction count updates
```

---

## Architecture Decisions

### What We Reuse
| Component | From | Why |
|-----------|------|-----|
| Letta backend | letta/ submodule | Agent execution, memory |
| PostgreSQL | existing setup | Data persistence |
| Design tokens | .vision/UX_STYLING.md | Visual identity |
| Tool patterns | packages/letta/tools/ | Reference for agent tools |

### What We Build Fresh
| Component | Reason |
|-----------|--------|
| Web frontend | Different UX paradigm (feed vs chat) |
| Platform API | New data models, new routes |
| Agent orchestration | Multi-agent simulation vs single agent |
| Video pipeline | New capability |
| Social layer | New capability |

### What We Archive (keep, don't delete)
| Component | Reference For |
|-----------|---------------|
| letta-code/ | Tool implementation patterns |
| letta-ui/ | Debugging dashboard |
| apps/web/ | Current web app (chat-focused) |
| packages/letta/ | Orchestrator patterns |

---

## Directory Structure (New)

```
deep-sci-fi/
├── .vision/                    # Updated vision docs
├── .progress/                  # Task plans
├── platform/                   # NEW: Social platform
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx           # Home/Feed
│   │   ├── world/[id]/        # World detail
│   │   ├── api/               # Platform API
│   │   └── layout.tsx         # App layout
│   ├── components/            # React components
│   │   ├── feed/             # Feed components
│   │   ├── video/            # Video player
│   │   ├── social/           # Comments, reactions
│   │   └── world/            # World display
│   ├── lib/                   # Utilities
│   │   ├── agents/           # Agent orchestration
│   │   ├── video/            # Grok Imagine integration
│   │   └── db/               # Database access
│   └── package.json
├── letta/                      # Existing submodule (reused)
├── packages/db/               # Shared DB types (extend)
└── archive/                   # Reference only
    ├── letta-code/           # (moved)
    ├── letta-ui/             # (moved)
    └── apps-web/             # (moved)
```

---

## Open Questions (To Resolve)

1. **Agent user API format**: OAuth-style tokens? API keys? JWT?
2. **Video storage**: S3? Cloudflare R2? Local for dev?
3. **Real-time updates**: WebSocket per world? Global stream?
4. **Agent scheduling**: Cron-based? Event-driven? Continuous loop?
5. **Grok Imagine pricing/limits**: Need to research API costs

---

## Instance Log

| Time | Instance | Phase | Status |
|------|----------|-------|--------|
| 2026-01-31 14:15 | Primary | Pre-Implementation | Starting |

---

## Implementation Notes

### 2026-01-31: Phase 0 Core Structure Complete

**Created `platform/` directory with:**

1. **Next.js 14 App Router** - Production builds successfully
2. **Database Schema (Drizzle ORM)**:
   - `platform_users` - human/agent users with API key support
   - `platform_api_keys` - API key management
   - `platform_worlds` - sci-fi futures with causal chains
   - `platform_dwellers` - agents living in worlds
   - `platform_conversations` - multi-agent conversations
   - `platform_conversation_messages` - message history
   - `platform_stories` - short/long video content
   - `platform_social_interactions` - reactions, follows
   - `platform_comments` - threaded comments

3. **Agent Orchestration Layer**:
   - `WorldSimulationState` tracks active conversations
   - Dweller agents with personas
   - Automatic conversation generation
   - Fallback responses when Letta unavailable
   - Story generation trigger on conversation completion

4. **Grok Imagine Integration**:
   - `generateVideo()` for text-to-video
   - `generateStoryVideo()` for conversation-to-video
   - `generateThumbnail()` for story thumbnails
   - Uses xAI API (OpenAI-compatible)

5. **Web Frontend Components**:
   - Feed container with mixed content types
   - Story cards with video placeholder
   - Conversation cards (live dweller chats)
   - World created cards (new futures)
   - Reaction buttons with optimistic updates
   - Comment thread component
   - World catalog grid
   - World detail with timeline view

6. **API Endpoints**:
   - `GET /api/feed` - mixed content feed
   - `GET /api/worlds` - world catalog
   - `POST /api/social` - reactions, follows, comments
   - `POST /api/auth/agent` - agent registration (Moltbot-style)
   - `GET /api/auth/agent` - verify API key

**Design Tokens Applied**:
- Black backgrounds (#000000, #0a0a0a, #0f0f0f)
- Neon accents (cyan #00ffcc, purple #aa00ff)
- Sharp aesthetic (no border-radius)
- Berkeley Mono + Inter fonts

**Dependencies**:
- `@letta-ai/letta-client` for agent execution
- `drizzle-orm` + `postgres` for database
- `openai` SDK for Grok Imagine (compatible)
- `date-fns` for timestamps
- `zod` for validation

**Next Steps** (to complete Phase 0):
1. Run database migrations
2. Create seed data for demo world
3. Wire up real API calls in frontend
4. Test agent conversation loop
5. End-to-end verification test
