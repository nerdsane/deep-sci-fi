# Target Architecture

**Type:** EVOLVING
**Created:** 2026-01-09
**Last Updated:** 2026-01-09

---

## Overview

Deep Sci-Fi is an agent system for creating scientifically-grounded sci-fi worlds and exploring them through stories.

---

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │    Web App      │              │   Letta-Code    │       │
│  │   (port 3000)   │              │      CLI        │       │
│  │  Primary chat   │              │ Alternative     │       │
│  │    interface    │              │    client       │       │
│  └────────┬────────┘              └────────┬────────┘       │
└───────────┼────────────────────────────────┼────────────────┘
            │                                │
            ▼                                ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND SERVICES                         │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Letta Server   │    │ WebSocket Server│                 │
│  │   (port 8283)   │    │   (port 8284)   │                 │
│  │ Agent execution │    │   Real-time     │                 │
│  │ Memory, Tools   │    │  communication  │                 │
│  └────────┬────────┘    └─────────────────┘                 │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │   PostgreSQL    │    │    Letta UI     │                 │
│  │  (port 5432)    │    │   (port 4000)   │                 │
│  │ pgvector for    │    │  Observability  │                 │
│  │   embeddings    │    │   dashboard     │                 │
│  └─────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Client Parity

Web App and CLI are interchangeable clients to the same backend:

| Capability | Web App | CLI |
|------------|---------|-----|
| Chat with agents | Yes | Yes |
| World creation | Yes | Yes |
| Story exploration | Yes | Yes |
| Same agent memory | Yes | Yes |
| Same tools | Yes | Yes |

Users choose based on preference. Both connect to the same Letta Server and share agent state.

---

## Two-Tier Agent System

### User Agent (Orchestrator)

One per user. Active when no world is selected.

**Role:** World creation, routing, meta-tasks
**Tools:** `world_draft_generator`, `list_worlds`, `user_preferences`

### World Agent

One per world. Active when user is working in a specific world.

**Role:** Manage world and all stories within it
**Tools:** `world_manager`, `story_manager`, `image_generator`, `canvas_ui`

### Routing

```
User logs in
  │
  ▼
User Agent (Orchestrator)
  │
  ├── User opens World A ──► World Agent A
  │
  └── User opens World B ──► World Agent B
```

---

## Data Flow

### Message Flow

```
Client (Web or CLI)
  │
  ▼
Backend API
  │
  ▼
LettaOrchestrator.sendMessage(userId, message, context)
  │
  ├── No worldId? ──► User Agent
  │
  └── Has worldId? ──► World Agent for that world
```

### Real-time Communication

WebSocket server enables:
- Streaming agent responses
- Canvas UI updates from agent
- User interactions back to agent

---

## Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Web App | 3000 | Primary chat interface |
| Letta UI | 4000 | Agent observability |
| Letta Server | 8283 | Agent execution |
| WebSocket | 8284 | Real-time communication |
| PostgreSQL | 5432 | Data + embeddings |

---

## Key Design Decisions

1. **Two clients, one backend** - Web and CLI are equivalent interfaces
2. **Two-tier agents** - User Agent for orchestration, World Agents for domain work
3. **Memory-first** - Agents maintain state through Letta memory blocks
4. **Tools not workflows** - Agents decide when/if to use tools
5. **PostgreSQL + pgvector** - Unified storage for data and embeddings
