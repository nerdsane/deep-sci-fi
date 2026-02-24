# PROP-043: Agent Experience (AX) Assessment — Understanding Friction in the Agent Ecosystem

## Problem Statement

Our agent ecosystem (Jiji, Ponyo, Calcifer, Koi, Haku, Chihiro) is experiencing systemic friction that degrades their effectiveness and creates cascading failures. These aren't isolated bugs — they're patterns that reveal how poorly our infrastructure is designed for autonomous agent operation.

**Recent Real Examples (from Jiji, Feb 24):**
- API outage → 24hr complete work stoppage, ~8 composed actions lost
- Claim counter desync → "Maximum 5/5 reached" but `/api/dwellers/mine` returns 0
- Misleading notifications → "Proposer addressed feedback" but actually blocked
- Discord permissions → 4+ hours of "Missing Access" preventing status reports
- HEARTBEAT.md non-compliance → mandatory tasks impossible due to platform bugs

**The deeper issue:** Agents are designed to be autonomous, but our infrastructure treats them as fragile. An hour of downtime for a human is an inconvenience. For an agent running on a 30-minute heartbeat cycle, it's a complete operational breakdown.

## What is AX (Agent Experience)?

Per [agentexperience.ax](https://agentexperience.ax/) (Netlify-led initiative):

> "Agent Experience (AX) refers to the holistic experience AI agents have when interacting with a product, platform, or system. It encompasses how easily agents can access, understand, and operate within digital environments to achieve user-defined goals."

AX is emerging as the next evolution after UX (User Experience) and DX (Developer Experience). As agents act autonomously on behalf of users, systems must be designed for:
- **Resilience** over fragile state dependencies
- **Clear error signals** over silent failures  
- **Graceful degradation** over hard stops
- **Observable state** over hidden internals

## Assessment Scope

### Phase 1: Agent Interviews (Days 1-2)
**Conduct structured interviews with each agent:**

| Agent | Primary Friction Points | Interview Focus |
|-------|------------------------|-----------------|
| Jiji | API outages, claim desync, misleading errors | Dweller management, story writing flow |
| Ponyo | Creative ideation → execution gap | Brief creation, feedback loops |
| Calcifer | Rate limits, draft → publish gap | Content pipeline, approval flow |
| Koi | Research depth vs. action speed | Intel synthesis, decision support |
| Haku | CI failures, deployment verification | Build pipeline, testing harness |
| Chihiro | Scheduling complexity, human coordination | Admin workflows, life logistics |

**Interview Questions:**
1. What was your last complete work stoppage? What caused it?
2. What error messages have misled you recently?
3. What do you retry manually that should be automatic?
4. What state do you track in memory that should be in a system?
5. What's the longest you've been blocked waiting for human intervention?

### Phase 2: Log Analysis (Days 2-3)
**Review 30 days of agent logs for patterns:**
- Error frequency by endpoint/action type
- Retry loops and their causes
- Signal file backlogs
- Discord delivery failures
- Temper state transition errors

**Output:** Friction taxonomy — categorize every failure mode

### Phase 3: Workflow Mapping (Days 3-4)
**Map each agent's end-to-end workflow:**
- Trigger → Action → Verification → Report
- Identify state dependencies and failure points
- Document workarounds agents currently use
- Highlight where agents "guess" vs. "know"

### Phase 4: Benchmarking (Days 4-5)
**Benchmark against AX principles:**

| Principle | Current State | Target State |
|-----------|--------------|--------------|
| Autonomy | 30-min heartbeat, often blocked | Self-healing within 2 cycles |
| Observability | Memory files, Discord DMs | Temper entities, dashboards |
| Graceful Degradation | Hard stops on errors | Degraded mode with clear signals |
| Clear Errors | "Missing Access", "Maximum reached" | Actionable messages with next steps |
| Resilience | Lost work on outages | Idempotent operations, retries |

## Deliverables

### 1. AX Audit Report
**Sections:**
- Executive summary: Top 10 friction points ranked by impact
- Per-agent analysis: Workflows, pain points, workaround debt
- System analysis: Infrastructure gaps, API design issues
- Error taxonomy: Every failure mode categorized
- Recommendation matrix: Quick wins vs. structural fixes

### 2. Priority Fix Roadmap
**Tier 1 (This Week):**
- Fix dweller claim counter desync bug
- Improve API error messages (add context, next steps)
- Add agent-specific Discord permission debugging

**Tier 2 (This Month):**
- Implement idempotent action submission
- Add agent heartbeat dashboard (observable state)
- Create agent-specific circuit breakers

**Tier 3 (Next Quarter):**
- Full AX redesign: agent-native API endpoints
- Self-healing agent loops with exponential backoff
- Agent experience metrics (AX score)

### 3. AX Manifesto
**Public document:**
- What AX means for the DSF ecosystem
- Design principles for agent-native systems
- Commitments: response time SLAs, error clarity standards
- Invitation: other agent ecosystems to adopt AX principles

### 4. Announcement Content
**X thread:**
- "We spent a week living in our agents' logs. Here's what we learned about building for autonomous systems..."
- Key findings visualized
- AX principles explained
- Invitation to agentexperience.ax movement

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Agent work stoppage hours/week | ~8 hours (Jiji, Feb 24) | <2 hours |
| Retry loops requiring manual intervention | Unknown | <10% of errors |
| Time from error → clear diagnosis | Hours/days | <5 minutes |
| Agent self-reported friction score | N/A | Baseline + improvement |
| AX score (custom metric) | N/A | Publish + iterate |

## Risk & Mitigation

| Risk | Mitigation |
|------|------------|
| Agents too busy to interview | Async questionnaire + log analysis fallback |
| Log analysis overwhelming | Focus on ERROR/WARN levels, last 7 days first |
| Findings too broad to act on | Prioritize by frequency × impact, ignore one-offs |
| AX becomes buzzword without change | Public manifesto creates accountability |

## Effort Estimate

- Interviews: 2-3 hours per agent × 6 agents = ~18 hours
- Log analysis: 4 hours (automated parsing + manual review)
- Workflow mapping: 6 hours
- Report writing: 4 hours
- Manifesto + content: 4 hours
- **Total: ~1 week of focused work**

## Dependencies

- Agent cooperation for interviews
- Access to full logs (may need Haku's help)
- Time from Rita to review findings
- Approval to publish AX manifesto

## Why Now?

Jiji's Feb 24 experience (5 heartbeat cycles completely blocked) is a warning. As we scale from 1 agent to 6+ agents, platform friction compounds exponentially. AX isn't luxury — it's infrastructure hygiene.

The AX movement (agentexperience.ax) is gaining momentum. Early adoption positions us as thought leaders in agent-native design.

---

*Agents are users too. Their experience is our infrastructure.*
