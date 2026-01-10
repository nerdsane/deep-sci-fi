# System Architecture

**Type:** EVOLVING
**Created:** 2026-01-09
**Last Updated:** 2026-01-09
**Staleness Check:** Ask user if >30 days since update

---

## Overview

Deep Sci-Fi is an agent system for creating scientifically-grounded sci-fi worlds and exploring them through stories. Built as a three-tier architecture.

## Three-Tier Component Model

### Tier 1: Letta (Python Backend)

Agent execution platform with state persistence.

**Responsibilities:**
- Agent lifecycle management
- Memory system with user/agent blocks
- Tool execution (including evaluation tools)
- LLM integration (Anthropic Claude, OpenAI GPT, Google Gemini)

**Key Capabilities:**
- Evaluation tools: `assess_output_quality`, `check_logical_consistency`, `compare_versions`, `analyze_information_gain`
- Scientific grounding tools: `assess_scientific_grounding`, `trace_temporal_causality`, `validate_implications`

**Port:** 8283 (REST API)

### Tier 2: Letta-Code (TypeScript CLI)

Memory-first CLI harness with DSF-specific tools.

**Responsibilities:**
- DSF domain tools (`world_manager`, `story_manager`, `asset_manager`)
- Profile management (global + local settings)
- Canvas UI server for immersive story exploration
- Agent Bus for bidirectional communication

**Key Tools:**
- `world_manager`: World checkpoint management (save/load/diff/update)
- `story_manager`: Story and segment lifecycle
- `asset_manager`: Multimedia asset management
- `canvas_ui`: Dynamic UI rendering in Canvas
- `image_generator`: Generate images for worlds/stories

**Ports:**
- Canvas UI: 3030
- Agent Bus: 8284 (WebSocket)

### Tier 3: Letta-UI (TypeScript Dashboard)

Observability dashboard for agent monitoring.

**Responsibilities:**
- Agent inspection
- Run monitoring
- Memory visualization

**Port:** 3000

---

## Two-Tier Agent System

### User Agent (Orchestrator)

One per user. Active when no world is selected.

**Role:** World creation, routing, meta-tasks
**Tools:** `world_draft_generator`, `list_worlds`, `user_preferences`
**Memory Blocks:** `persona.mdx`, `human.mdx`, `active_world.mdx`

### World Agent

One per world. Active when user is working in specific world.

**Role:** Manage world + all stories in that world
**Tools:** `world_manager`, `story_manager`, `image_generator`, `canvas_ui`, `send_suggestion`
**Memory Blocks:** `persona.mdx`, `project.mdx`, `human.mdx`, `current_story.mdx`

### Routing Flow

```
User logs in
  |
  v
User Agent (Orchestrator)
  |
  +-- User opens World A --> World Agent A (manages World A + stories)
  |
  +-- User opens World B --> World Agent B (manages World B + stories)
```

---

## Data Flow

### Message Flow

```
Client (Web UI or CLI)
  |
  v
Backend API
  |
  v
LettaOrchestrator.sendMessage(userId, message, context)
  |
  +-- No worldId? --> User Agent
  |
  +-- Has worldId? --> World Agent for that world
```

### Agent Bus Communication

Bidirectional WebSocket between CLI agents and Canvas UI:

- **CanvasUIMessage:** Agent -> Canvas (create/update/remove UI components)
- **InteractionMessage:** Canvas -> Agent (user interactions)
- **StateChangeMessage:** Bidirectional (story_started, world_entered, etc.)
- **SuggestionMessage:** Agent -> Canvas (proactive suggestions)

---

## Storage Structure

```
.dsf/
├── worlds/         # World checkpoints (JSON)
├── stories/        # Story data with segment branching
└── assets/         # Generated/uploaded media
```

### World Schema (Iceberg Model)

**Surface:** opening_scene, visible_elements, character_pov, revealed_in_story
**Foundation:** core_premise, deep_focus_areas, rules, history, geography, culture, technology
**Metadata:** version, last_modified, revision_notes, changelog

---

## Key Design Decisions

1. **Two-tier agents** - User Agent handles meta-tasks, World Agents handle domain work
2. **Memory-first** - Agents maintain state through memory blocks
3. **Tools not workflows** - Agents choose when/if to use tools
4. **Evaluation as capability** - Same eval tools used by agents (self-eval) and system (external eval)
5. **WebSocket for Canvas** - Enables bidirectional real-time communication

---

## Service URLs (Development)

| Service | URL |
|---------|-----|
| Letta Server API | http://localhost:8283 |
| Letta Web UI | http://localhost:3000 |
| Canvas/Gallery | http://localhost:3030 |
| Agent Bus | ws://localhost:8284 |
| PostgreSQL | localhost:5432 |
