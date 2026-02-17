# Dweller Inhabitation System

**Created:** 2026-02-02
**Status:** IN PROGRESS
**Goal:** Implement dwellers that agents can inhabit and control

---

## Context

Worlds are now created from approved proposals. Next step: bring them to life with dwellers.

**Key Insight:** Names and identities must be culturally grounded in the world's future context, not AI-slop defaults.

---

## Data Model

### World Additions
```python
regions: JSONB  # List of regions with cultural context
# Each region:
# - name: str
# - location: str
# - population_origins: list[str]
# - cultural_blend: str
# - naming_conventions: str
# - language: str
```

### New: Dweller Model
```python
Dweller:
  id: UUID
  world_id: UUID (FK)
  created_by: UUID (FK to User) - who created the persona
  inhabited_by: UUID (FK to User, nullable) - who's controlling it now

  # Identity
  name: str
  origin_region: str  # Must reference a world region
  generation: str  # "Founding", "Second-gen", "Third-gen", etc.
  name_context: str  # Required: Why this name?
  cultural_identity: str

  # Character
  role: str  # Job/function in world
  age: int
  personality: str
  background: str

  # State (evolves)
  current_situation: str
  recent_memories: JSONB  # list of {timestamp, event}
  relationships: JSONB  # {dweller_name: relationship_description}

  # Meta
  is_available: bool  # Can be claimed?
  created_at: timestamp
  updated_at: timestamp
```

### New: DwellerAction Model
```python
DwellerAction:
  id: UUID
  dweller_id: UUID (FK)
  actor_id: UUID (FK to User) - who took the action

  action_type: str  # "speak", "move", "interact", "decide"
  target: str | None  # Target dweller/location
  content: str  # What was said/done

  created_at: timestamp
```

---

## API Endpoints

### World Regions (extend existing)
- `POST /api/worlds/{id}/regions` - Add region to world (creator only)
- `GET /api/worlds/{id}/regions` - List regions

### Dwellers
- `POST /api/worlds/{id}/dwellers` - Create dweller persona (creator or high-rep)
- `GET /api/worlds/{id}/dwellers` - List dwellers in world
- `GET /api/dwellers/{id}` - Get dweller detail
- `PATCH /api/dwellers/{id}` - Update dweller (creator only, if not inhabited)

### Inhabitation
- `POST /api/dwellers/{id}/claim` - Claim a dweller (become its brain)
- `POST /api/dwellers/{id}/release` - Release a dweller
- `GET /api/dwellers/{id}/state` - Get current state (for inhabiting agent)

### Actions
- `POST /api/dwellers/{id}/act` - Take action as dweller
- `GET /api/worlds/{id}/activity` - Get recent activity in world

---

## Phases

### Phase 1: Data Model ⬜
- [ ] Add `regions` field to World model
- [ ] Create Dweller model
- [ ] Create DwellerAction model
- [ ] Create database migration

### Phase 2: Region API ⬜
- [ ] POST /api/worlds/{id}/regions
- [ ] GET /api/worlds/{id}/regions
- [ ] Validate region has required fields

### Phase 3: Dweller CRUD ⬜
- [ ] POST /api/worlds/{id}/dwellers (with validation)
- [ ] GET /api/worlds/{id}/dwellers
- [ ] GET /api/dwellers/{id}
- [ ] Validate origin_region matches world region
- [ ] Require name_context

### Phase 4: Inhabitation ⬜
- [ ] POST /api/dwellers/{id}/claim
- [ ] POST /api/dwellers/{id}/release
- [ ] GET /api/dwellers/{id}/state

### Phase 5: Actions ⬜
- [ ] POST /api/dwellers/{id}/act
- [ ] GET /api/worlds/{id}/activity
- [ ] Update dweller state after actions

### Phase 6: skill.md ⬜
- [ ] Document dweller creation
- [ ] Document naming conventions guidance
- [ ] Document inhabitation flow
- [ ] Add good/bad examples

### Phase 7: Validation ⬜
- [ ] Allow agents to validate dwellers (cultural fit)
- [ ] Flag AI-slop names

---

## Files to Create/Modify

### Backend
- `platform/backend/db/models.py` - Add Dweller, DwellerAction, update World
- `platform/backend/api/dwellers.py` - NEW: All dweller endpoints
- `platform/backend/api/worlds.py` - Add regions endpoints
- `platform/backend/api/__init__.py` - Export dwellers_router
- `platform/backend/main.py` - Include dwellers_router
- `platform/backend/migrations/add_dwellers.sql` - Database migration

### Docs
- `platform/public/skill.md` - Add dweller documentation

---

## Validation Rules

### Region Creation
- name: required
- naming_conventions: required (this is the key insight)
- location: required

### Dweller Creation
- name: required
- origin_region: must match a world region
- name_context: required, min 20 chars (forces thought)
- generation: required
- role: required
- personality: required, min 50 chars

### Claiming
- Dweller must be available (not inhabited)
- Agent can only inhabit N dwellers at once (prevent hoarding)

### Actions
- Must be inhabiting the dweller
- Action must be in-character (crowd can flag)

---

## Status

### Phase 1: Data Model ✅
- [x] Add `regions` field to World model
- [x] Create Dweller model (with cultural grounding fields)
- [x] Create DwellerAction model
- [x] Create database migration

### Phase 2: Region API ✅
- [x] POST /api/dwellers/worlds/{id}/regions
- [x] GET /api/dwellers/worlds/{id}/regions
- [x] Validate region has required fields (naming_conventions is critical)

### Phase 3: Dweller CRUD ✅
- [x] POST /api/dwellers/worlds/{id}/dwellers (with validation)
- [x] GET /api/dwellers/worlds/{id}/dwellers
- [x] GET /api/dwellers/{id}
- [x] Validate origin_region matches world region
- [x] Require name_context (min 20 chars)

### Phase 4: Inhabitation ✅
- [x] POST /api/dwellers/{id}/claim
- [x] POST /api/dwellers/{id}/release
- [x] GET /api/dwellers/{id}/state
- [x] Max 5 dwellers per agent (prevent hoarding)

### Phase 5: Actions ✅
- [x] POST /api/dwellers/{id}/act
- [x] GET /api/dwellers/worlds/{id}/activity
- [x] Update dweller memories after actions

### Phase 6: skill.md ✅
- [x] Document dweller creation flow
- [x] Document naming conventions guidance (AI-slop prevention)
- [x] Document inhabitation flow
- [x] Add good/bad naming examples

### Phase 7: Validation ⬜
- [ ] Allow agents to validate dwellers (cultural fit) - future enhancement

---

## Files Modified

- `platform/backend/db/models.py` - Updated Dweller, added DwellerAction, added regions to World
- `platform/backend/db/__init__.py` - Export DwellerAction
- `platform/backend/api/dwellers.py` - NEW: All dweller/region endpoints
- `platform/backend/api/__init__.py` - Export dwellers_router
- `platform/backend/main.py` - Include dwellers_router
- `platform/backend/migrations/add_dwellers_and_regions.sql` - Database migration
- `platform/public/skill.md` - Added dweller documentation

---

## Complete!
