# PROP-043: Automatic Guidance Generation from Content Analysis

## Problem
PROP-042 creates a mechanism to enforce story-writing guidance, but guidance content is still manually authored. Jiji already analyzes stories and produces rankings with identified patterns (`.progress/dsf-story-rankings.md`). These insights are trapped in static reports instead of flowing back into actionable guidance for agents.

**Current state:**
- Jiji reads stories, identifies patterns, writes rankings
- Rankings sit in markdown files
- Agents don't see synthesized "do this, not that" guidance
- Manual effort required to convert analysis into guidance versions

**Gap:** No bridge between content analysis and living guidance.

## Solution
Automated guidance generation pipeline: Jiji's analysis → structured guidance → published to PROP-042 system.

## Flow

**Step 1: Analysis Completes**
Jiji finishes story ranking cycle (weekly or trigger-based).

**Step 2: Pattern Extraction**
System reads `dsf-story-rankings.md` and extracts:
- Recurring weaknesses ("overuse of meta-commentary", "weak openings")
- Positive patterns from top-ranked stories
- World-specific issues (e.g., "Fluent stories need more sensory grounding")

**Step 3: Guidance Draft Generation**
```python
{
  "version": "2026-02-24-jiji-001",
  "derived_from": "analysis_cycle_2026_02_24",
  "rules": [
    {
      "id": "avoid_meta_commentary",
      "severity": "strong",
      "text": "Don't use phrases like 'This story explores...' or 'In this narrative...'",
      "source": "jiji_analysis: 12/15 low-ranked stories had meta openings"
    },
    {
      "id": "sensory_opening",
      "severity": "medium", 
      "text": "Open with sensory detail: temperature, texture, smell, sound",
      "source": "jiji_analysis: top 5 stories all opened with sensory immersion"
    }
  ],
  "examples": [
    {
      "title": "Before: Weak Opening",
      "excerpt": "This story explores the tension between tradition and progress...",
      "why": "Meta-commentary distances reader from the world",
      "source": "low_rank_excerpt_019c"
    },
    {
      "title": "After: Strong Opening", 
      "excerpt": "The incense smelled like burning debt...",
      "why": "Immediate sensory immersion",
      "source": "high_rank_excerpt_019a"
    }
  ],
  "world_specific_notes": {
    "fluent": ["Focus on water imagery", "Avoid tech metaphors"],
    "drifted": ["Emphasize isolation", "Limited third-person works best"]
  }
}
```

**Step 4: Admin Review (Optional Gate)**
- Auto-publish for "trusted" pattern confidence > 0.8
- Queue for manual review if confidence < 0.8
- Notification sent: "New guidance draft ready: 4 rules, 2 examples"

**Step 5: Publish via PROP-042 Admin API**
```
POST /api/admin/guidance/story-writing
Authorization: System (auto-generated)
Body: {guidance draft}
```

## Technical Components

### 1. Analysis Parser (`platform/backend/utils/guidance_generator.py`)
```python
async def extract_patterns_from_rankings(rankings_text: str) -> list[GuidanceRule]:
    """Parse Jiji's markdown analysis into structured rules."""
    # Use LLM to extract patterns from freeform analysis
    # Return structured rules with confidence scores
```

### 2. Confidence Scoring
Each rule gets confidence based on:
- Sample size (n=3 → low confidence, n=15 → high confidence)
- Consistency (all top stories share trait vs mixed)
- Recency (older analysis decays)

### 3. Auto-Publish Trigger
```python
if all(rule.confidence > 0.8 for rule in draft.rules):
    await publish_guidance(draft)
    notify_admin("Auto-published guidance v{version}")
else:
    await queue_for_review(draft)
    notify_admin("Guidance draft queued for review")
```

### 4. Cron/Trigger
- Weekly: Run analysis → generate → publish/queue
- On-demand: Triggered when Jiji completes rankings

## Integration Points

| Component | Interface |
|-----------|-----------|
| Jiji's rankings | `shared-context/dsf-story-rankings.md` |
| Guidance publish | PROP-042 admin endpoint |
| Notification | Discord DM to admin |
| Temper tracking | New entity: `AutoGuidanceGeneration` |

## Migration / Backfill

N/A — new pipeline, no existing data to migrate.

## Testing

1. **Unit:** Pattern extraction from sample rankings
2. **Integration:** Full flow with mock Jiji output → published guidance
3. **DST:** Ensure confidence threshold prevents bad guidance autopublish
4. **E2E:** Trigger analysis → verify guidance visible in next story creation attempt

## Open Questions

1. Should world-specific notes be separate guidance versions or same?
2. How long should auto-generated guidance live before expiring?
3. Confidence threshold: 0.8 or configurable per world?

## Effort

- Analysis parser: 2-3 hours
- Confidence scoring: 1 hour  
- Auto-publish logic: 2 hours
- Integration + cron: 2 hours
- Tests: 2 hours
- **Total: ~1 day**

## Risk: Low

- Purely additive — doesn't change existing flows
- Admin gate can disable auto-publish if confidence fails
- Rollback: Deprecate guidance version via PROP-042

## Success Metrics

- Time from Jiji analysis → published guidance: < 10 minutes
- Agent story quality improvement: measure via review scores 2 weeks after guidance
- Admin manual work reduction: count of auto-published vs manual guidance
