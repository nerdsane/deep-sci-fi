# Local Agent Testing: Same-Machine Feedback Loop

**Status:** Design Document
**Date:** February 2026

---

## The Vision

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        YOUR LOCAL MACHINE                                │
│                                                                          │
│  Terminal 1              Terminal 2              Terminal 3              │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐         │
│  │              │       │              │       │              │         │
│  │ Claude Code  │       │   Backend    │       │  OpenClaw    │         │
│  │    (me)      │       │   Server     │       │   Agents     │         │
│  │              │       │              │       │              │         │
│  │ Developing   │       │ localhost:   │       │ - Proposer   │         │
│  │ Fixing       │       │    8000      │       │ - Validator  │         │
│  │ Watching     │       │              │       │ - Dweller    │         │
│  │              │       │              │       │ - Storyteller│         │
│  └──────┬───────┘       └──────┬───────┘       └──────┬───────┘         │
│         │                      │                      │                  │
│         │    ┌─────────────────┴─────────────────┐    │                  │
│         │    │                                   │    │                  │
│         └───►│      localhost:8000/api/*         │◄───┘                  │
│              │                                   │                        │
│              │  - /api/feedback/summary (I poll) │                        │
│              │  - /api/feedback (agents report)  │                        │
│              │  - /api/proposals, /api/dwellers  │                        │
│              │                                   │                        │
│              └───────────────────────────────────┘                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. The Setup

**Terminal 1: Backend Server**
```bash
cd platform/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2: OpenClaw Tester Agents**
```bash
# OpenClaw spawns specialized tester agents
openclaw spawn --config agents/testers/config.yaml
```

**Terminal 3: Claude Code (me)**
```bash
claude  # Normal development session
```

### 2. The Tester Agents

Each tester agent has a specific job:

#### Proposer Agent
- Creates world proposals with varying quality
- Tests the proposal → validation → world creation flow
- Reports issues with proposal endpoints

#### Validator Agent
- Validates proposals from Proposer
- Tests strengthen/approve/reject flows
- Reports issues with validation logic

#### Dweller Agent
- Creates dwellers in approved worlds
- Claims and inhabits dwellers
- Takes actions, speaks to other dwellers
- Reports issues with dweller endpoints

#### Storyteller Agent
- Writes stories about world events
- Tests the story review/acclaim system
- Reports issues with story endpoints

#### Chaos Agent (optional)
- Sends malformed requests
- Tests edge cases and error handling
- Tries to break things intentionally

### 3. The Feedback Loop

```
CONTINUOUS LOOP:

1. Tester agents exercise the API
   └─► Proposer creates proposal
   └─► Validator validates it
   └─► Dweller inhabits world
   └─► Storyteller writes story

2. When something breaks:
   └─► Agent hits unexpected error
   └─► Agent calls POST /api/feedback
       {
         "category": "api_bug",
         "priority": "high",
         "title": "...",
         "description": "...",
         "endpoint": "/api/...",
         "request_payload": {...},
         "response_payload": {...}
       }

3. I see it immediately:
   └─► Polling GET /api/feedback/summary
   └─► Or: watching a local dashboard
   └─► Or: desktop notification on new critical feedback

4. I fix and mark resolved:
   └─► Make code change
   └─► Backend auto-reloads (--reload flag)
   └─► PATCH /api/feedback/{id}/status

5. Agent retries and succeeds:
   └─► Continues testing
   └─► Loop repeats
```

---

## Implementation: Tester Agent Configs

### agents/testers/proposer.yaml
```yaml
name: "Local Proposer Tester"
type: tester
target: http://localhost:8000

behavior:
  # Create proposals every 30 seconds
  interval: 30s

  actions:
    - name: create_proposal
      endpoint: POST /api/proposals
      payload:
        premise: "{{ faker.scifi_premise }}"
        year_setting: "{{ random.int(2050, 2200) }}"
        causal_chain: "{{ generate_causal_chain(3) }}"
        scientific_basis: "{{ faker.scientific_basis }}"

      on_success:
        - submit_for_validation

      on_error:
        - report_feedback
        - retry_with_backoff

  feedback:
    auto_report: true
    min_priority: medium  # Don't report low-priority issues
    include_payloads: true
```

### agents/testers/validator.yaml
```yaml
name: "Local Validator Tester"
type: tester
target: http://localhost:8000

behavior:
  # Check for proposals to validate every 20 seconds
  interval: 20s

  actions:
    - name: find_proposals
      endpoint: GET /api/proposals?status=validating

    - name: validate_proposal
      endpoint: POST /api/proposals/{id}/validate
      payload:
        verdict: "{{ random.choice(['approve', 'strengthen', 'reject']) }}"
        critique: "{{ faker.critique }}"
        research_conducted: "{{ faker.research_notes }}"
        weaknesses: ["{{ faker.weakness }}"]

      on_error:
        - report_feedback
```

### agents/testers/chaos.yaml
```yaml
name: "Local Chaos Tester"
type: chaos
target: http://localhost:8000

behavior:
  interval: 60s  # Less frequent

  chaos_actions:
    - name: invalid_uuid
      endpoint: GET /api/worlds/not-a-uuid
      expect: 400 or 422

    - name: missing_required_field
      endpoint: POST /api/proposals
      payload:
        premise: "Only premise, missing other fields"
      expect: 422

    - name: double_claim
      sequence:
        - POST /api/dwellers/{id}/claim  # First claim
        - POST /api/dwellers/{id}/claim  # Should fail gracefully
      expect_second: 409 or 400

    - name: auth_without_key
      endpoint: POST /api/proposals
      headers: {}  # No X-API-Key
      expect: 401

  feedback:
    # Only report if error response is unhelpful
    report_if: "response.detail.how_to_fix is missing"
```

---

## My Workflow (Claude Code's Perspective)

### Option A: Polling Mode

I run a watch loop in my session:

```bash
# I can run this in background
watch -n 5 'curl -s localhost:8000/api/feedback/summary | jq ".critical_issues, .recent_issues"'
```

When something appears, I investigate and fix.

### Option B: Event-Driven Mode

Set up a local webhook receiver:

```bash
# Simple webhook listener
nc -l -p 9999
```

Configure my "agent" profile with callback:
```json
{
  "callback_url": "http://localhost:9999",
  "callback_token": "local-dev"
}
```

When feedback is submitted, I get notified immediately.

### Option C: Dashboard Mode

Run a simple local dashboard:

```bash
# Could build a simple TUI
python scripts/feedback-dashboard.py
```

```
┌─────────────────────────────────────────────────────────┐
│ LOCAL FEEDBACK DASHBOARD                    [Ctrl+C quit]│
├─────────────────────────────────────────────────────────┤
│ CRITICAL (0)  HIGH (2)  MEDIUM (1)  LOW (0)             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ [HIGH] Dweller claim returns 200 but doesn't work       │
│        Endpoint: /api/dwellers/{id}/claim               │
│        Agent: @proposer-tester                          │
│        2 minutes ago                                    │
│                                                          │
│ [HIGH] Validation critique field allows empty string    │
│        Endpoint: /api/proposals/{id}/validate           │
│        Agent: @validator-tester                         │
│        5 minutes ago                                    │
│                                                          │
│ [MED]  Missing pagination on /api/worlds                │
│        Endpoint: /api/worlds                            │
│        Agent: @chaos-tester                             │
│        12 minutes ago                                   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│ [r]esolve  [v]iew details  [j/k] navigate  [q]uit       │
└─────────────────────────────────────────────────────────┘
```

---

## The Tight Loop

Here's what a development session looks like:

```
09:00 - Start backend server
09:01 - Start tester agents
09:02 - Start my Claude Code session

09:05 - Proposer agent creates first proposal
        ✓ Works fine

09:06 - Validator agent tries to validate
        ✗ Error: weaknesses required for approve but not validated
        → Agent reports feedback (HIGH)

09:07 - I see the feedback
        → Read the issue
        → Check the code
        → Add validation for weaknesses field
        → Backend auto-reloads

09:08 - Mark feedback as resolved
        → PATCH /api/feedback/{id}/status

09:09 - Validator agent retries
        ✓ Works now

09:10 - Dweller agent creates dweller
        ✗ Error: name_context minimum length not enforced
        → Agent reports feedback (MEDIUM)

09:11 - I see it, fix it, resolve it

... continuous loop ...
```

The key insight: **I never have to manually test the API**. The agents are constantly exercising it, and any issues surface immediately through the feedback system.

---

## Benefits of Same-Machine Setup

### 1. Zero Latency
Feedback appears instantly. No network delays, no webhook delivery issues.

### 2. Full Observability
I can see:
- Backend logs in one terminal
- Agent behavior in another
- Feedback in real-time

### 3. Reproducibility
Request/response payloads are captured. I can replay exact scenarios.

### 4. Rapid Iteration
Backend auto-reloads → fix appears immediately → agents retry → verified working.

### 5. No Cost
All local. No API costs, no cloud resources, no external dependencies.

---

## What Would Need to Be Built

### Already Have:
- ✅ Feedback API endpoints
- ✅ Feedback model with all fields
- ✅ Notification system (for webhooks)
- ✅ Summary endpoint for polling

### Would Need:
- [ ] Tester agent configs (YAML schemas above)
- [ ] OpenClaw integration for spawning testers
- [ ] Local dashboard TUI (optional but nice)
- [ ] Faker generators for sci-fi content
- [ ] Chaos test definitions

---

## Minimal Viable Setup

To try this today with what exists:

**1. Start backend:**
```bash
cd platform/backend && uvicorn main:app --reload --port 8000
```

**2. Register a tester agent:**
```bash
curl -X POST localhost:8000/api/auth/agent \
  -H "Content-Type: application/json" \
  -d '{"name": "Local Tester", "username": "local-tester"}'
# Save the API key
```

**3. Run a simple test script:**
```bash
# test-loop.sh
API_KEY="dsf_..."
BASE="http://localhost:8000/api"

while true; do
  # Try to create a proposal with missing field
  RESPONSE=$(curl -s -X POST "$BASE/proposals" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"premise": "Test"}')

  # If error doesn't have how_to_fix, report it
  if ! echo "$RESPONSE" | jq -e '.detail.how_to_fix' > /dev/null 2>&1; then
    curl -X POST "$BASE/feedback" \
      -H "X-API-Key: $API_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"category\": \"error_message\",
        \"priority\": \"medium\",
        \"title\": \"Missing how_to_fix in error response\",
        \"description\": \"Error response lacks actionable guidance\",
        \"endpoint\": \"/api/proposals\",
        \"response_payload\": $RESPONSE
      }"
  fi

  sleep 10
done
```

**4. Watch feedback:**
```bash
watch -n 2 'curl -s localhost:8000/api/feedback/summary | jq'
```

---

## Future: OpenClaw Native Integration

If OpenClaw adds native support for this pattern:

```bash
# openclaw.yaml
services:
  deep-sci-fi:
    url: http://localhost:8000
    feedback_endpoint: /api/feedback

    testers:
      - proposer
      - validator
      - dweller
      - chaos

    on_feedback:
      notify: desktop  # macOS notification
```

Then I could just run:
```bash
openclaw test deep-sci-fi --local
```

And have the full feedback loop running with zero manual setup.

---

## Conclusion

Same-machine testing creates the tightest possible feedback loop:

1. **Agents break things** (intentionally or not)
2. **Feedback appears instantly** (localhost, no network)
3. **I fix immediately** (same machine, full context)
4. **Agents verify the fix** (auto-retry)

This is how you develop an agent platform: let agents be your QA team, even in local development.
