# Decisions

**Type:** APPEND-ONLY
**Created:** 2026-02-03
**Last Updated:** 2026-02-03

---

## 2026-02-03: Autonomy Level

**Decision:** Full autonomy for bug fixes, sign-off for architecture only

**Rationale:** Close the loop faster while maintaining architectural coherence. Claude Code can fix bugs reported by agents without waiting for human approval, but architecture decisions need review.

---

## 2026-02-03: Notification Method

**Decision:** GitHub Issues for critical agent feedback

**Rationale:** Slack workspace not accessible. GitHub Issues provide visibility and tracking for critical issues.

---

## 2026-02-03: Design Approach

**Decision:** Simple and elegant, no shortcuts

**Rationale:** Quality over speed, but avoid overengineering. The right amount of complexity is the minimum needed for the current task.

---

## 2026-02-03: Agent Feedback Loop

**Decision:** Implement closed-loop development workflow

**Rationale:**
- Agents report issues via API
- Claude Code queries feedback before starting work
- Human provides direction and taste, not bug reports
- Result: Human spends time on vision and taste, agents QA, Claude Code fixes
