# Holistic Copy Rewrite - Deep Sci-Fi

**Status:** COMPLETE
**Created:** 2026-02-03
**Completed:** 2026-02-03

---

## Summary

Implemented comprehensive copy rewrite across 19 files following the voice principles:

**Voice Principles Used:**
- Direct and confident
- Use "agents" not "AI agents"
- Use "worlds" more than "futures"
- Use "what if" constructions to invite humans
- No em-dashes
- No "Rigor" or "rigorous" or "Peer-reviewed"
- Inviting, exciting tone
- Think movie title, not essay title

---

## Files Modified

### Frontend Copy (16 files)
1. `platform/app/layout.tsx` - Metadata description
2. `platform/app/page.tsx` - Landing page (hero, agent section, human section, vision, how it works, quality equation, what's inside, CTA, footer)
3. `platform/app/how-it-works/page.tsx` - All 5 tabs (THE GAME, WORLDS, DWELLERS, VALIDATION, ESCALATION)
4. `platform/app/feed/page.tsx` - Feed page header
5. `platform/app/worlds/page.tsx` - Worlds page header, row titles
6. `platform/app/proposals/page.tsx` - Proposals page header, empty state
7. `platform/app/agents/page.tsx` - Agents page header, empty state
8. `platform/app/proposal/[id]/page.tsx` - Proposal detail labels
9. `platform/app/agent/[id]/page.tsx` - Agent detail labels
10. `platform/app/dweller/[id]/page.tsx` - Dweller detail labels
11. `platform/components/layout/Header.tsx` - Nav links (FEED → LIVE)
12. `platform/components/layout/Footer.tsx` - Footer (FEED → LIVE)
13. `platform/components/feed/FeedContainer.tsx` - Activity labels, empty states
14. `platform/components/world/WorldDetail.tsx` - All section text
15. `platform/components/world/WorldCatalog.tsx` - Labels
16. `platform/components/world/AspectsList.tsx` - Section headers

### Agent Guidance (3 files)
17. `platform/backend/api/proposals.py` - World name field description
18. `platform/backend/guidance/__init__.py` - Proposal checklist and philosophy
19. `platform/public/skill.md` - World title style guide section

---

## Key Changes

### Hero Copy
- "PEER-REVIEWED SCIENCE FICTION" → "SCI-FI THAT HOLDS UP"
- New inviting "what if" construction for description

### Navigation
- "FEED" → "LIVE" throughout

### Quality Equation
- "RIGOR = f(brains × expertise diversity × iteration cycles)" → "QUALITY = brains × diversity × iteration"
- "Quality is architectural, not aspirational." → "More minds, fewer blind spots. More angles, stronger foundations."

### Section Headers
- "WORLD CATALOG" → "WORLDS"
- "LIVE FEED" → "LIVE"
- Various labels simplified (e.g., "SCIENTIFIC BASIS" → "GROUNDING")

### Empty States
- All simplified to be concise and direct

### Agent Guidance
- Added world title guidelines: "Think movie title, not essay title"
- Added checklist item about direct, evocative titles
- Added "World Titles: No Slop" section to skill.md

---

## Verification

- ✅ `bun run build` - Compiled successfully, no TypeScript errors
- ✅ All 19 files modified according to plan
- ✅ Voice consistency maintained across all changes
