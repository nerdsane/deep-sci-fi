# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Sci-Fi is an agent that helps create scientifically-grounded sci-fi worlds and explore them through stories. Built as a three-tier architecture:

- **Letta** (Python submodule): Backend agent execution platform with evaluation tools
- **Letta-Code** (TypeScript submodule): Memory-first CLI harness with DSF-specific tools
- **Letta-UI** (TypeScript): Observability dashboard for agent monitoring

## Post-Task Verification (CRITICAL)

**After completing ANY implementation task, always automatically verify:**
- No hacks or temporary workarounds left in code
- No placeholder implementations (TODO, FIXME, stub functions that don't actually work)
- No code that appears to work but doesn't actually function properly
- No silent failures (errors caught but not logged or handled)
- All error handling is explicit and appropriate
- All edge cases are properly handled
- No console.log statements left for debugging
- No commented-out code blocks
- All TypeScript types are properly defined (no `any` unless absolutely necessary)

**This verification happens automatically after task completion. User can also trigger it manually with `/no-cap` command.**

## Vision-Aligned Planning (MANDATORY)

**STOP. Before starting ANY non-trivial task (3+ steps, multi-file, or research required), you MUST follow this workflow. No exceptions.**

### Directories

```
.vision/     → Project vision documents (long-lived north star) - READ FIRST
.progress/   → Timestamped task plans (per-task tracking) - CREATE BEFORE CODING
```

### Before Starting - DO THIS FIRST

1. **Check `.vision/`** - If exists, READ ALL vision files before doing anything else
2. **Check `.progress/`** - Read existing plans to understand current state
3. **Create plan** - ALWAYS save `.progress/YYYYMMDD_HHMMSS_task-name.md` BEFORE writing any code
4. **If no `.vision/`** and task is significant: ASK user if they want a vision interview

**DO NOT skip planning. DO NOT start coding without a plan file. This is non-negotiable.**

### During Execution

1. **Update plan after each phase** - Mark complete, log findings
2. **Re-read plan before major decisions** - Keeps goals in attention window
3. **Document deviations** - If implementation differs from plan, note why

### Before Completion

1. **Run `/no-cap`** - MANDATORY for any code changes
2. **Check vision alignment** - Does result match vision constraints?
3. **Update plan status** - Mark complete with verification status

### Multi-Instance Coordination

When multiple Claude instances collaborate:
- Read `.progress/` FIRST before starting any work
- Claim phases explicitly in Instance Log section
- Update status frequently to avoid conflicts
- Share discoveries in findings section

### Commands

- `/planning-with-files` - Full workflow details (vision interview, multi-instance, etc.)
- `/no-cap` - Verify implementation quality

## Git Workflow (IMPORTANT)

**After implementing any fix, change, or feature that has been discussed and completed:**

1. **Always commit your changes** with a clear, descriptive message using conventional commit format:
   ```bash
   git add .
   git commit -m "feat: description of feature"
   # or
   git commit -m "fix: description of bug fix"
   # or
   git commit -m "refactor: description of refactoring"
   ```

2. **Always push to the current branch**:
   ```bash
   git push
   ```

**Conventional commit types:**
- `feat:` for new features
- `fix:` for bug fixes
- `refactor:` for code refactoring
- `docs:` for documentation changes
- `chore:` for maintenance tasks

**This applies to:**
- Bug fixes that have been tested and verified
- New features that have been implemented and work as expected
- Refactoring that has been completed
- Documentation updates
- Any other changes that represent completed work

**Do NOT commit/push:**
- Work in progress that is not yet functional
- Experimental changes that haven't been discussed
- Changes that break existing functionality

## Startup & Shutdown

Start the entire stack (Letta server, Web UI, Agent Bus, Canvas):
```bash
./start.sh
```

This will:
1. Validate prerequisites (Docker, docker-compose, Bun)
2. Set up environment variables from `.env` (creates from `.env.example` if needed)
3. Start Letta Server in Docker (http://localhost:8283)
4. Start Letta Web UI (http://localhost:3000)
5. Start Agent Bus WebSocket server (ws://localhost:8284)
6. Start Story Explorer Gallery (http://localhost:3030)
7. Launch letta-code CLI in foreground

Stop all services:
```bash
./stop.sh
```

Or manually:
```bash
# Stop Letta server
cd letta && docker compose -f dev-compose.yaml down

# Stop Web UI
kill $(cat letta-ui/.ui.pid)

# Stop Agent Bus
kill $(cat letta-code/.agent-bus.pid)

# Stop Gallery
kill $(cat letta-code/.gallery.pid)
```

## Development Commands

### Letta (Python Backend)
Located in `letta/` submodule (git: https://github.com/nerdsane/letta.git, branch: main)

```bash
cd letta

# Start server in Docker (builds from source on main branch)
docker compose -f dev-compose.yaml up -d --build

# View logs
docker compose -f dev-compose.yaml logs -f

# Stop server
docker compose -f dev-compose.yaml down
```

### Letta-Code (TypeScript CLI)
Located in `letta-code/` submodule (git: https://github.com/nerdsane/letta-code.git, branch: main)

```bash
cd letta-code

# Run CLI in dev mode
bun run dev

# Start Canvas UI (story/world explorer)
bun run canvas              # http://localhost:3030

# Start Agent Bus (WebSocket broker)
bun run agent-bus           # ws://localhost:8284

# Linting and formatting
bun run lint                # Check code with Biome
bun run fix                 # Auto-format with Biome
bun run typecheck           # TypeScript type checking

# Build for distribution
bun run build               # Creates deep-scifi.js executable
```

### Letta-UI (TypeScript Dashboard)
Located in `letta-ui/` (not a submodule, part of main repo)

```bash
cd letta-ui

# Start dev server
LETTA_BASE_URL=http://localhost:8283 bun run dev  # http://localhost:3000

# Build for production
bun run build               # Outputs to dist/

# Type checking
bun run typecheck
```

## Architecture Overview

### Three-Tier Component Model

**Letta (Backend)**
- Agent execution platform with state persistence
- Evaluation tools: `assess_output_quality`, `check_logical_consistency`, `compare_versions`, `analyze_information_gain`
- LLM integration (Anthropic Claude, OpenAI GPT, Google Gemini)
- REST API on port 8283
- Memory system with user/agent blocks

**Letta-Code (CLI/Tools)**
- Memory-first CLI harness built on Letta API
- **DSF Tools**: `world_manager`, `story_manager`, `asset_manager`, `image_generator`
- **Agent Bus Server** (WebSocket on port 8284): Bidirectional message broker between CLI and Canvas UI
- **Canvas Server**: Immersive story/world exploration interface
- Profile management: global (`~/.config/letta/settings.json`), local (`.letta/settings.local.json`)

**Letta-UI (Dashboard)**
- Observability dashboard connecting to Letta Server
- Agent monitoring, run inspection, memory visualization
- Earth-tone design (sand, rust, sage, midnight)

### Agent Bus Communication Pattern

The Agent Bus solves bidirectional communication between headless CLI agents and web Canvas UI:

**Message Types** (defined in `letta-code/src/agent-bus/types.ts`):
- `CanvasUIMessage`: Agent → Canvas (create/update/remove UI components at mount points)
- `InteractionMessage`: Canvas → Agent (user interactions from UI)
- `StateChangeMessage`: Bidirectional (story_started, world_entered, agent_thinking, etc.)
- `SuggestionMessage`: Agent → Canvas (proactive suggestions with priority)
- `ConnectionMessage`: Lifecycle management

**Flow**:
1. CLI agent and Canvas UI both connect to Agent Bus (WebSocket clients)
2. Agent sends `canvas_ui` messages to dynamically render UI components
3. Canvas renders components at specified mount points (overlay, fullscreen, inline)
4. User interactions create `interaction` messages sent back to agent
5. Agent can send `suggestion` messages for proactive guidance

### DSF Domain Model (Scientifically-Grounded Sci-Fi)

**Storage Structure**:
```
.dsf/
├── worlds/         # World checkpoints (JSON)
├── stories/        # Story data with segment branching
└── assets/         # Generated/uploaded media
```

**World Manager** (`letta-code/src/tools/impl/world_manager.ts`)
- Operations: `save`, `load`, `diff`, `update`
- Worlds follow "iceberg model" (professional sci-fi approach):
  - **Surface**: opening_scene, visible_elements, revealed_in_story
  - **Foundation**: core_premise, deep_focus_areas, rules, technology, history/geography/culture, working_notes
  - **Metadata**: development state (sketch → draft → detailed), version tracking

**Story Manager** (`letta-code/src/tools/impl/story_manager.ts`)
- Operations: `create`, `save_segment`, `load`, `list`, `branch`, `continue`, `update_metadata`
- Story segments with parent pointers for versioning
- World contributions tracking (which elements/rules were tested)
- Multimedia asset linking

**Asset Manager** (`letta-code/src/tools/impl/asset_manager.ts`)
- Operations: `save`, `load`, `list`, `delete`
- Manages `.dsf/assets/` for generated/uploaded media

**Core Domain Concepts**:
1. **Elements** (characters, locations, tech): Linked with relationships, detail levels, version tracking
2. **Rules** (world constraints): Scope (universal/local/conditional), certainty (tentative/established/fundamental), tested in stories
3. **Evaluation Reports**: ConsistencyReport, DepthAssessment, NoveltyReport, AbstractionReport, NarrativeEvaluation

### Canvas UI Dynamic Rendering

**Key Files** (`letta-code/src/canvas/`):
- `app.tsx` (52KB): Main React app with state management
- `server.ts`: Bun server hosting Canvas React app with HMR
- `components/DynamicRenderer`: Renders agent-specified UI specs
- `components/MountPoint`: Named slots for component placement
- `components/ImmersiveStoryReader`: Full-screen story reading
- `components/WorldSpace`: Immersive world visualization

## Tool Ecosystem

**DSF-Specific Tools**:
- `world_manager`: World checkpoint management
- `story_manager`: Story and segment lifecycle
- `asset_manager`: Multimedia asset management
- `canvas_ui`: Send UI updates to Canvas
- `get_canvas_interactions`: Poll for user interactions
- `image_generator`: Generate images for worlds/stories
- `send_suggestion`: Send suggestions to Canvas UI

**Tool Management** (`letta-code/src/tools/toolset.ts`):
- Model-specific toolsets: Anthropic (44 tools), OpenAI (35 tools)
- Tool name mapping for backwards compatibility
- Dynamic toolset selection based on model

## Environment Setup

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Required API keys in `.env`:
```
ANTHROPIC_API_KEY=     # For Claude models (required)
GOOGLE_API_KEY=        # For Gemini image generation (preferred)
OPENAI_API_KEY=        # Alternative for GPT image generation
```

3. Run `./setup-env.sh` to distribute variables to submodules (letta, letta-code)

## Submodule Management

Update submodules to latest:
```bash
git submodule update --remote --merge
```

Commit submodule updates:
```bash
git add letta letta-code
git commit -m "Update submodules: <description>"
```

## What Makes This "Scientifically-Grounded"

1. **Explicit Rules System**: Worlds define universal rules with certainty levels, testable in stories
2. **Contradiction Detection**: Evaluation tools find logical inconsistencies
3. **Depth Tracking**: Rules marked by research depth level (surface/medium/deep)
4. **Change Tracking**: Every modification versioned with reason and changelog
5. **Grounding Evaluation**: NarrativeEvaluation checks story adherence to world rules
6. **Technology Specifications**: Documented systems with limitations, not vague "magic"
7. **Working Notes**: Explicit tracking of contradictions to resolve

## Common Development Tasks

**View logs**:
```bash
# Letta server
docker compose -f letta/dev-compose.yaml logs -f

# Web UI
tail -f letta-ui/.ui.log

# Agent Bus
tail -f letta-code/.agent-bus.log

# Canvas/Gallery
tail -f letta-code/.gallery.log
```

**Access services**:
- Letta Server API: http://localhost:8283
- Letta Web UI: http://localhost:3000
- Story Explorer Gallery: http://localhost:3030
- Agent Bus: ws://localhost:8284
- PostgreSQL: localhost:5432

**Rebuild Letta server from source**:
```bash
cd letta
docker compose -f dev-compose.yaml up -d --build
```

**Working with worlds/stories in CLI**:
The agent has access to DSF tools (`world_manager`, `story_manager`) and will use them autonomously. Worlds and stories are saved to `.dsf/` directories.
