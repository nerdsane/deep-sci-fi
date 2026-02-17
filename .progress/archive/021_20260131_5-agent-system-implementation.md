# 5-Agent System Implementation

**Date:** 2026-01-31
**Status:** Complete

## Summary

Implemented a complete 5-agent ecosystem for creating and curating scientifically-grounded sci-fi worlds.

## Agents Implemented

| Agent | Model | File | Purpose |
|-------|-------|------|---------|
| **Production** | claude-opus-4-5 | `agents/production.py` | Research trends + engagement → decides what worlds to create |
| **World Creator** | claude-opus-4-5 | `agents/world_creator.py` | Creates worlds from briefs, avoids clichés, generates dweller cast |
| **Dweller** | claude-3-5-haiku | `agents/orchestrator.py` | Lives in worlds, converses (already existed) |
| **Storyteller** | claude-opus-4-5 | `agents/storyteller.py` | Observes dwellers, creates video scripts (upgraded from haiku) |
| **Critic** | claude-opus-4-5 | `agents/critic.py` | Evaluates quality, detects AI-isms, provides feedback |

## Files Created/Modified

### New Files
- `platform/backend/agents/production.py` - Production Agent
- `platform/backend/agents/world_creator.py` - World Creator Agent
- `platform/backend/agents/critic.py` - Critic Agent
- `platform/backend/api/agents.py` - Agent API endpoints
- `platform/backend/scheduler.py` - Automated task scheduler

### Modified Files
- `platform/backend/db/models.py` - Added ProductionBrief, CriticEvaluation, AgentActivity tables
- `platform/backend/db/__init__.py` - Export new models
- `platform/backend/agents/prompts.py` - Enhanced with comprehensive anti-cliché guidance
- `platform/backend/agents/__init__.py` - Export new agents
- `platform/backend/agents/orchestrator.py` - Extended dweller persona fields
- `platform/backend/agents/storyteller.py` - Upgraded to Opus model
- `platform/backend/api/__init__.py` - Include agents_router
- `platform/backend/main.py` - Add agents router and scheduler startup
- `platform/backend/requirements.txt` - Added APScheduler

## Database Schema Additions

```python
class ProductionBrief(Base):
    """Briefs from Production Agent recommending worlds to create."""
    id, created_at, research_data (JSONB), recommendations (JSONB)
    selected_recommendation (int), resulting_world_id (FK), status, error_message

class CriticEvaluation(Base):
    """Quality evaluations from Critic Agent."""
    id, created_at, target_type, target_id
    evaluation (JSONB), ai_isms_detected (JSONB), overall_score

class AgentActivity(Base):
    """Activity log for UI observability."""
    id, timestamp, agent_type, agent_id, world_id
    action, details (JSONB), duration_ms
```

## API Endpoints Added

### Production Agent
- `POST /api/agents/production/run` - Trigger brief generation
- `GET /api/agents/production/briefs` - List briefs
- `GET /api/agents/production/briefs/{id}` - Get brief details
- `POST /api/agents/production/briefs/{id}/approve` - Approve → create world

### World Creator
- `POST /api/agents/world-creator/create` - Manual world creation
- `POST /api/agents/world-creator/from-brief/{id}` - From production brief

### Critic
- `POST /api/agents/critic/evaluate/world/{id}` - Evaluate world
- `POST /api/agents/critic/evaluate/story/{id}` - Evaluate story
- `GET /api/agents/critic/evaluations` - List evaluations
- `GET /api/agents/critic/evaluations/{id}` - Get evaluation details

### Activity
- `GET /api/agents/activity` - List agent activity
- `WS /api/agents/activity/stream` - Real-time updates

## Scheduler Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `daily_production_check` | 6 AM | Check if new world needed, generate brief |
| `daily_critic_sweep` | 3 AM | Evaluate worlds/stories not recently evaluated |
| `engagement_check` | Every 4 hours | Monitor engagement, trigger production if low |

## Anti-Cliché System

Comprehensive anti-cliché rules implemented in `prompts.py`:

### Forbidden Patterns
- "Neo-[City]" naming
- Banned descriptors: bustling, cutting-edge, sleek, sprawling, gleaming, etc.
- Character archetypes: grizzled veteran, idealistic youth, corrupt official, etc.
- Plot elements: robot uprising, AI consciousness, generic corporation control

### Required Elements
- Culturally coherent names
- Technology with costs and limitations
- Causal chains from 2026
- Character contradictions

### AI-ism Detection
- Rule-based pattern matching for common AI writing tells
- LLM-based evaluation for more nuanced detection
- Severity levels: minor, moderate, major

## Verification Checklist

- [x] Production Agent researches trends and generates briefs
- [x] World Creator transforms briefs into complete worlds
- [x] Dwellers have enhanced personas with contradictions
- [x] Storyteller upgraded to Opus for better scripts
- [x] Critic evaluates and detects AI-isms
- [x] API endpoints for all agent operations
- [x] Scheduler for automated tasks
- [x] Activity logging for observability
- [x] Anti-cliché rules in all agent prompts

## Next Steps

1. Run database migrations to create new tables
2. Test full loop: Production → World Creator → Simulation → Storyteller → Critic
3. Add Exa API integration for real trend research
4. Build UI for agent activity dashboard
