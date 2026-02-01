# Maximum Agency Studio Redesign

**Date:** 2026-02-01
**Status:** COMPLETE
**Type:** Architecture Refactor

## Overview

Redesigned the Studio workflow to follow three core principles:
1. **Maximum Agency** - Agents have tools to act, not being polled for intentions
2. **Emergent Behavior** - Agents discover each other and form relationships organically
3. **Least Constraints** - No artificial timings, let agent activity drive simulation

## What Changed

### 1. New Autonomous Tools (`tools.py`)

Added 7 new tools for agent autonomy:

| Tool | Purpose | Used By |
|------|---------|---------|
| `initiate_conversation` | Start conversations directly | Dwellers |
| `end_conversation` | End conversations when ready | Dwellers |
| `update_availability` | Signal state (seeking/open/busy/reflecting) | Dwellers |
| `schedule_future_action` | Schedule future actions | All agents |
| `observe_world` | Check world state | All agents |
| `broadcast_to_world` | Announce to all dwellers | Puppeteer |
| `subscribe_to_events` | Watch for specific event types | Storyteller |

### 2. Extended Memory Blocks (`studio_blocks.py`)

New shared block types for coordination:
- `world_event_log_{id}` - Recent events (append-only)
- `world_conversation_log_{id}` - Active/recent conversations
- `world_scheduled_actions_{id}` - Agent-scheduled future actions

New helper functions:
- `update_dweller_availability()` - Update availability in directory
- `append_to_event_log()` - Add events to log
- `log_conversation()` - Log conversation status
- `schedule_action()` - Add scheduled action
- `get_due_scheduled_actions()` - Get due actions

### 3. Event Scheduler (`scheduler.py`) [NEW FILE]

Agent-driven scheduling system:
- Agents schedule their own future actions
- Scheduler only processes what agents have queued
- No fixed tick cycle - sleeps until next action is due
- Handlers for different action types

### 4. Dweller Prompts (`prompts.py`)

**Removed:**
- `[SEEKING/REFLECTING/READY]` signal instructions
- Polling-based intention patterns
- "When asked about your intentions" language

**Added:**
- Tool usage instructions for autonomous behavior
- "You have agency. Use it." emphasis
- Clear examples of autonomous flow

### 5. Orchestrator (`orchestrator.py`)

**Removed:**
- `DWELLER_POLL_COOLDOWN` constant
- `_poll_dweller_intentions()` method
- `_match_seeking_dwellers()` method
- `_start_conversation()` (orchestrator-driven)
- `_progress_conversation()` (tick-based)
- `_should_end_conversation()` (keyword matching)
- 10-second tick loop

**Added:**
- `_ensure_dweller_agent()` - Ensures agents exist with full tool set
- `handle_conversation_initiated()` - Handles tool results
- `handle_conversation_ended()` - Handles tool results
- `handle_availability_updated()` - Handles tool results
- `handle_action_scheduled()` - Routes to scheduler
- `send_message_to_dweller()` - External message handling
- `_process_tool_results()` - Processes all tool results
- `_initialize_world()` - Gives initial context to puppeteer
- `_persistence_loop()` - Background state persistence

The orchestrator now does ONLY:
- Agent lifecycle management
- Shared memory block initialization
- Tool result handling
- State persistence

### 6. Storyteller (`storyteller.py`)

**Changed:**
- Added event subscription system
- `subscriptions` list of event types to watch
- `notification_threshold` for filtering
- `should_observe()` checks subscriptions
- `_is_significant()` evaluates event importance
- `initialize_storyteller()` sets up subscriptions

**Removed:**
- Tick-based polling pattern

## Architecture Comparison

### Before (Orchestrator-Driven)

```
Orchestrator Loop (every 10s):
  1. Poll dwellers for [SEEKING/REFLECTING/READY]
  2. Match seeking dwellers
  3. Progress conversations turn by turn
  4. Check for keyword-based endings
  5. Notify storyteller every 2 ticks
```

### After (Agent-Driven)

```
Agent Autonomy:
  Dweller: I want to talk → initiate_conversation → creates conversation
  Dweller: I'm done talking → end_conversation → closes conversation
  Dweller: I need time alone → update_availability → signals reflecting
  Dweller: Later I want to check in → schedule_future_action → queued

Scheduler: Only wakes when agents have scheduled actions

Storyteller: Subscribes to events → notified when they occur → acts if inspired
```

## Files Modified

1. `platform/backend/agents/tools.py` - Added 7 autonomous tools
2. `platform/backend/agents/studio_blocks.py` - Extended with new block types
3. `platform/backend/agents/scheduler.py` - NEW FILE for agent scheduling
4. `platform/backend/agents/prompts.py` - Updated dweller & storyteller prompts
5. `platform/backend/agents/orchestrator.py` - Refactored to remove polling
6. `platform/backend/agents/storyteller.py` - Added event subscriptions

## Testing Notes

To test the new architecture:

1. **Dweller autonomy:**
   - Dwellers should initiate conversations using tools
   - Dwellers should end conversations using tools
   - No external polling required

2. **Scheduler:**
   - Agents can schedule future actions
   - Scheduler wakes only when actions are due

3. **Storyteller:**
   - Subscribes to event types on initialization
   - Notified only when subscribed events occur
   - Acts autonomously when inspired

## Alignment with Vision

From `.vision/PHILOSOPHY.md`:
> "Tools over workflows. Evaluation over prescription. Scale with better models."

This redesign implements:
- **Tools, not prescriptions:** Agents have tools to act; we don't prescribe when/how
- **Evaluation, not workflows:** Agents decide based on judgment; no step-based constraints
- **Scale with better models:** Same tools work better with smarter models
