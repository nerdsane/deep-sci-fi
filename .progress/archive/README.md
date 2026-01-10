# Deep Sci-Fi Migration Planning

This directory contains the migration plan and progress tracking for the Deep Sci-Fi project migration from CLI to web application.

## Files

### [MIGRATION_PLAN.md](./MIGRATION_PLAN.md)
The complete implementation plan for migrating Deep Sci-Fi from a single-user CLI tool to a multi-user web application.

**Contents:**
- Migration approach (non-destructive)
- Two-tier agent architecture design
- User flows and agent lifecycle
- Database schema updates
- Implementation roadmap
- Success criteria

**Key Architecture:**
- **User Agent (Orchestrator)**: ONE per user - handles world creation and routing
- **World Agents**: ONE per world - manages world AND all stories in that world

### [PROGRESS.md](./PROGRESS.md)
Detailed progress tracking showing what's been completed and what's remaining.

**Current Status:** ~45% Complete
- ✅ Phase 1: Foundation (100%)
- ✅ Phase 2A: Agent Architecture (100%)
- ✅ Phase 2A-SDK: Letta SDK Integration (100%)
- ⏳ Phase 2B: UI Integration (0%)

## Quick Reference

### What Works Now
- ✅ Database with two-tier agent support
- ✅ Authentication (email/password + Google OAuth)
- ✅ World/Story CRUD operations
- ✅ Letta SDK integration
- ✅ User Agent creation (orchestrator)
- ✅ World Agent creation
- ✅ Message routing and streaming
- ✅ Memory block system

### What's Next
1. Implement `world_draft_generator` tool (LLM integration)
2. Port World Agent tools from letta-code
3. Build story viewer page
4. Wire up chat panel UI
5. Test end-to-end flow

## Key Commits

- `f98fe69` - feat: Implement Phase 2A-SDK - Complete Letta SDK Integration
- `c00c946` - feat: Implement Phase 2A - Two-tier agent architecture
- (See git log for full history)

## Related Documentation

- [../STATUS.md](../STATUS.md) - High-level implementation status
- [../docs/AGENT_CONTEXT_SHARING.md](../docs/AGENT_CONTEXT_SHARING.md) - Agent architecture
- [../docs/IMMERSIVE_EXPERIENCES.md](../docs/IMMERSIVE_EXPERIENCES.md) - VN, audio, UI
- [../docs/CHAT_UI_INTEGRATION.md](../docs/CHAT_UI_INTEGRATION.md) - Chat panel design

## Usage

### Update Progress
When completing a phase or major milestone, update `PROGRESS.md` with:
- Completion status (✅/⚠️/❌)
- Files modified
- Success criteria met
- Next steps

### Update Plan
If the migration approach changes, update `MIGRATION_PLAN.md` with:
- Architectural decisions
- Implementation tasks
- Success criteria

## Maintenance

These files should be updated:
- After completing a major phase
- When architectural decisions change
- When adding new features to the roadmap
- Before/after significant refactors

Keep these files in sync with the codebase to maintain accurate progress tracking.
