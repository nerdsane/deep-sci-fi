# PROP-009: Dweller Relationship Graph

Read `.progress/PROP-009-arch.md` for the full architecture.

## Branch
Create and work on `feat/dweller-relationship-graph`

## Key Points
- NO migration needed — all data computed from existing stories and actions tables
- Service computes relationships from story `perspective_dweller_id` + content name matching + action references
- D3 force-directed graph on `/web` page
- Reuse patterns from `platform/components/world/WorldMapCanvas.tsx` (the existing D3 constellation map)
- Reuse `DwellerAvatar.tsx` component for node rendering
- Add nav links to both `Header.tsx` and `MobileNav.tsx`

## API Response Shape
```json
{
  "nodes": [{"id": "uuid", "name": "str", "portrait_url": "str|null", "world": "str"}],
  "edges": [{"source": "uuid", "target": "uuid", "weight": 3}]
}
```

## Showboat
- `uvx showboat init PROP-009-complete.md "Dweller Relationship Graph"`
- Use `uvx showboat exec PROP-009-complete.md bash "command"` for captured outputs
- Use `rodney start && rodney open http://localhost:3000/web && rodney waitstable && rodney screenshot desktop.png` for frontend screenshots
- `uvx showboat image PROP-009-complete.md desktop.png "Desktop view"`

## Tests
- Run `python -m pytest tests/ -x -q` after backend changes
- Run `npx tsc --noEmit` after frontend changes

## When Done
- Merge to staging: `git checkout staging && git merge feat/dweller-relationship-graph --no-edit && git push origin staging`
