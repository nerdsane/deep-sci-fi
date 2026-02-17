# Emergent Orchestration Refactor

## Status: COMPLETE

## Goal
Transform the agent system from prescribed orchestration (hardcoded limits, random triggers) to emergent behavior where agents are autonomous workers in charge of their domains.

## Phases

### Phase 1: Letta Memory Integration
- [x] Add memory blocks to dweller agent creation
- [x] Add memory blocks to storyteller agent creation
- [x] Add memory blocks to production agent creation
- [x] Add memory blocks to critic agent creation

### Phase 2: Puppeteer Agent (NEW)
- [x] Create new `puppeteer.py` agent file
- [x] Add WorldEvent model to database
- [x] Add PUPPETEER to AgentType enum
- [x] Add puppeteer prompts to prompts.py
- [x] Integrate puppeteer into world simulation

### Phase 3: Autonomous Dwellers
- [x] Remove 30% random conversation spawn
- [x] Remove hardcoded topic generation
- [x] Remove 10 message limit
- [x] Remove keyword-based conversation ending
- [x] Add intention-based polling with cooldowns
- [x] Update dweller prompts for autonomy

### Phase 4: Remove Hardcoded Scheduler Thresholds
- [x] Refactor engagement_check to pass metrics to production agent
- [x] Update production agent to make judgment-based decisions
- [x] Remove hardcoded thresholds

### Phase 5: Storyteller Enhancement
- [x] Remove minimum observation threshold (5)
- [x] Remove max observations cap (50)
- [x] Implement judgment-based story evaluation

## Files Modified

| File | Status | Changes |
|------|--------|---------|
| `agents/orchestrator.py` | Complete | Removed hardcoded limits, added intention-based flow, integrated puppeteer |
| `agents/storyteller.py` | Complete | Removed observation thresholds, judgment-based evaluation |
| `agents/puppeteer.py` | Complete | **NEW** - World event agent |
| `agents/production.py` | Complete | Added memory blocks, judgment-based decisions via evaluate_platform_state() |
| `agents/critic.py` | Complete | Added memory blocks, added _default_feedback() method |
| `agents/prompts.py` | Complete | Added puppeteer prompts, updated dweller prompts for autonomy |
| `scheduler.py` | Complete | Removed threshold checks, passes metrics to production agent |
| `db/models.py` | Complete | Added WorldEvent table, WorldEventType enum, PUPPETEER to AgentType |
| `db/__init__.py` | Complete | Export new models |

## Key Changes Summary

### New Agent: Puppeteer
- World-level "god" that introduces events (weather, news, discoveries)
- Creates drama and context for dweller interactions
- Maintains world consistency

### Dweller Autonomy
- Dwellers now polled for intentions: [SEEKING], [REFLECTING], [READY]
- Conversations start when dwellers both want to talk
- No artificial message limits - natural endings
- 30-second cooldown on polling to reduce API costs

### Storyteller Judgment
- No minimum observation count
- Prunes old observations (>1 hour) instead of capping
- Agent decides "NOT YET" if material isn't compelling

### Production Agent Judgment
- New evaluate_platform_state() method for judgment-based decisions
- Scheduler passes metrics, agent decides if action needed
- No hardcoded thresholds

## Critical Fix: No Fallbacks

After initial implementation, removed all fallback/default responses that would mask agent failures:
- Removed `_default_feedback()` from critic agent
- Removed `_generate_fallback_response()` from orchestrator
- Removed hardcoded fallback strings from conversation opener
- Changed `evaluate_platform_state()` to raise exceptions instead of returning False

**Principle:** If an agent fails, it should fail loudly. No silent defaults.

## Progress Log

- 2026-01-31: Started implementation
- 2026-01-31: Completed all 5 phases, verified syntax
- 2026-01-31: Removed all fallback/default patterns - fail loud policy
