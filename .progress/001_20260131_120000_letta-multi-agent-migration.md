# Plan: Migrate to Letta Native Multi-Agent Communication

## Status: COMPLETE

## Summary

Enable Dweller and Studio agents to communicate directly using Letta's built-in multi-agent tools and shared memory blocks, replacing the current orchestrator-mediated routing.

## Phases

### Phase 1: Studio Agents (Curator, Architect, Editor) - COMPLETE

- [x] 1.1 Create shared studio blocks (`studio_blocks.py`)
- [x] 1.2 Migrate Architect to Letta (from direct Anthropic API)
- [x] 1.3 Update Curator (production.py) - add multi-agent tools
- [x] 1.4 Update Editor (world_critic.py) - add multi-agent tools

### Phase 2: Per-World Agents (Puppeteer, Storyteller) - COMPLETE

- [x] 2.1 Create per-world shared blocks in WorldSimulator.start()
- [x] 2.2 Update Puppeteer - add multi-agent tools
- [x] 2.3 Update Storyteller - add multi-agent tools

### Phase 3: Dweller Agents (Emergent Conversations) - COMPLETE

- [x] 3.1 Update dweller agent creation with multi-agent tools
- [x] 3.2 Update dweller system prompts with multi-agent instructions
- [x] 3.3 Register dwellers in world directory for agent discovery

---

## Files Modified

| File | Status | Changes |
|------|--------|---------|
| `platform/backend/agents/studio_blocks.py` | NEW | Shared block management for studio + world agents |
| `platform/backend/agents/world_creator.py` | MODIFIED | Migrated from Anthropic → Letta, added multi-agent tools, tags, shared blocks |
| `platform/backend/agents/production.py` | MODIFIED | Added multi-agent tools, tags, shared blocks, brief updates |
| `platform/backend/agents/world_critic.py` | MODIFIED | Added multi-agent tools, tags, shared blocks |
| `platform/backend/agents/puppeteer.py` | MODIFIED | Added multi-agent tools, tags, shared blocks, world state updates |
| `platform/backend/agents/storyteller.py` | MODIFIED | Added multi-agent tools, tags, shared blocks |
| `platform/backend/agents/orchestrator.py` | MODIFIED | Shared block init in start(), dweller multi-agent tools, directory registration |
| `platform/backend/agents/prompts.py` | MODIFIED | Added multi-agent communication instructions to dweller prompt |

---

## Key Changes Summary

### Studio Blocks (Global)
| Block | Purpose | Attached To |
|-------|---------|-------------|
| `studio_briefs` | Production briefs from Curator | Curator, Architect |
| `studio_world_drafts` | Worlds in progress | Architect, Editor |
| `studio_evaluation_queue` | Content awaiting review | Editor |
| `studio_context` | Pipeline state | All studio agents |

### World Blocks (Per-World)
| Block | Purpose | Attached To |
|-------|---------|-------------|
| `world_state_{id}` | Events, conditions, time | Puppeteer, Storyteller, Dwellers |
| `world_knowledge_{id}` | World facts | All agents in world |
| `world_dweller_directory_{id}` | Dweller agent IDs | All Dwellers |

### Agent Tags
| Agent | Tags |
|-------|------|
| Curator | `["studio", "curator"]` |
| Architect | `["studio", "architect"]` |
| Editor | `["studio", "editor", "world_{id}"]` |
| Puppeteer | `["world", "world_{id}", "puppeteer"]` |
| Storyteller | `["world", "world_{id}", "storyteller"]` |
| Dwellers | `["dweller", "world_{id}"]` |

### Multi-Agent Tools Enabled
All agents now have `include_multi_agent_tools=True` which provides:
- `send_message_to_agent_and_wait_for_reply` - Direct messaging with response
- `send_message_to_agent_async` - Fire-and-forget messaging
- `send_message_to_agents_matching_tags` - Broadcast to tag groups

---

## Migration Notes

- **Non-breaking**: Each agent still works independently; multi-agent tools are additive
- **Gradual adoption**: Agents can use direct messaging OR orchestrator routing
- **Shared state**: Blocks enable agents to share knowledge without message passing
- **Discovery**: Tags enable agents to find each other dynamically

## Next Steps (Optional Future Work)

1. Refactor orchestrator `_match_seeking_dwellers()` to let dwellers find each other directly
2. Add `_sync_dweller_conversations()` to capture multi-agent conversations to DB
3. Remove orchestrator message routing once direct agent messaging is proven stable
