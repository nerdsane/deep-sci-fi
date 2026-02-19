# PROP-028 Step 1: Add write hooks to remaining API files

A previous session already added `emit_feed_event()` calls to `api/stories.py` and `api/dwellers.py`. You need to add similar calls to 4 more files.

First: `from utils.feed_events import emit_feed_event` at the top of each file.

Then add `emit_feed_event()` calls after each entity is committed. Read api/feed.py to see the _fetch_* functions — they show what fields the frontend expects per event type. Match those payload shapes.

## Files to modify:

### api/proposals.py
After proposal submission, add emit for "proposal_submitted". After graduation, emit "world_created". After revision, emit "proposal_revised". After validation, emit "proposal_validated".

### api/aspects.py  
After aspect creation, emit "aspect_proposed". After approval, emit "aspect_approved".

### api/auth.py
After agent registration, emit "agent_registered".

### api/reviews.py
After review submission, emit "review_submitted". After feedback resolution, emit "feedback_resolved".

## After adding all hooks:
```bash
cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20
```

Then commit:
```bash
git add -A && git commit -m "feat(028): add feed event write hooks to all API files"
```
