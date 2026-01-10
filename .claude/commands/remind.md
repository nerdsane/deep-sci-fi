# TigerStyle Reminder

**STOP. Read this before continuing.**

---

## Are You Following the Process?

### Before Writing Code

- [ ] Did you read `.vision/` files first?
- [ ] Did you create a plan in `.progress/YYYYMMDD_HHMMSS_task-name.md`?
- [ ] Did you document the options you considered?
- [ ] Did you note the trade-offs of your chosen approach?

### During Implementation

- [ ] Are you logging decisions in the plan file?
- [ ] Are you updating the plan as you complete phases?
- [ ] If you hit a blocker, did you document it?

### Before Completion

- [ ] Did you write tests that prove the feature works?
- [ ] Did you run `/no-cap` to verify no placeholders/hacks?
- [ ] Does the result align with `.vision/CONSTRAINTS.md`?
- [ ] Did you update the plan state to COMPLETE?

---

## Quick Reference

```
State Machine: GROUNDING → PLANNING → IMPLEMENTING → VERIFYING → COMPLETE

GROUNDING:   Read .vision/*.md, understand constraints
PLANNING:    Create .progress/ plan with options/decisions/trade-offs
IMPLEMENTING: Do the work, log decisions
VERIFYING:   Tests pass, /no-cap pass, vision aligned
COMPLETE:    Commit with plan reference, push
```

---

## Key Files

| File | Purpose |
|------|---------|
| `.vision/CONSTRAINTS.md` | Non-negotiable requirements |
| `.vision/PHILOSOPHY.md` | Tools not workflows, Bitter Lesson |
| `.progress/templates/plan.md` | Plan template to copy |

---

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Started coding without plan | Stop. Create plan first. |
| Made decision without documenting | Add to Options & Decisions section |
| Skipped tests | Write tests before marking complete |
| Left TODOs in code | Fix or document as intentional |
| Forgot to update plan state | Update now |

---

## If You're Lost

1. Read `.vision/CONSTRAINTS.md`
2. Check current plan in `.progress/`
3. Ask user for clarification if needed

**The goal is disciplined, traceable development - not speed.**
