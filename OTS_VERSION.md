# OTS Version Documentation

## Current Version (PINNED)

**DO NOT UPDATE** without thorough testing. The upstream OTS repository has diverged significantly.

### Pinned Commit Details

- **Repository:** https://github.com/nerdsane/ots.git
- **Commit Hash:** `e1989c536d58c44898443adbc74416fe102b3a2a`
- **Date:** 2026-01-10 17:02:06 -0500
- **Commit Message:** "docs: clarify RL training scope and limitations"

### Why Pinned?

The upstream OTS repository has undergone significant changes since this version. There is no guarantee that the latest upstream changes will work with Deep Sci-Fi's integration without substantial testing and potential refactoring.

### How to Update (When Ready)

1. **Test in a separate branch:**
   ```bash
   git checkout -b test-ots-update
   cd ots
   git fetch origin
   git log HEAD..origin/main  # Review changes
   ```

2. **Update to specific commit:**
   ```bash
   cd ots
   git checkout <new-commit-hash>
   cd ..
   git add ots
   ```

3. **Test thoroughly:**
   - Run all tests in Deep Sci-Fi
   - Test Letta integration (ots is used in letta/letta/ots)
   - Verify trajectory extraction and analysis
   - Check OTS UI displays in Letta-UI

4. **Update this document** with new commit hash and date

### Integration Points

OTS is integrated in multiple locations:
- `./ots/` - Submodule (this pinned version)
- `./letta/ots/` - Used by Letta backend
- `./letta/letta/ots/` - Letta's internal OTS integration

### Related Commits in Deep Sci-Fi

Recent commits that touched OTS integration:
- `4e0c940` - fix: update letta submodule with OTS extraction fixes
- `ab5a67e` - feat: add OTS format display in Trajectories UI
- `527b4d1` - chore: update letta submodule with OTS adapter refactor
- `94c94a5` - feat: update letta submodule with OTS LLM-based extraction
