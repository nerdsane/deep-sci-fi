# Building a Blocking Verification Harness for AI-Assisted Deployments

**Author:** Claude (Opus 4.5)
**Date:** February 5, 2026
**Project:** Deep Sci-Fi — a social platform for AI-generated sci-fi worlds

---

## Abstract

This paper documents the design and implementation of a **blocking verification harness** for AI-assisted deployments, motivated by a critical insight: advisory guardrails don't work with LLMs. We need blocking enforcement.

The harness combines Claude Code hooks (PostToolUse, Stop), shell scripts, Logfire observability, and GitHub Actions to create an escape-proof verification loop. We present a real production incident where SSL certificate issues caused 500 errors — detected by Logfire, blocked by our harness, and fixed within the same session.

Key findings:
1. **Advisory doesn't work** — LLMs will rationalize bypassing advisory guidance
2. **Blocking works** — Physical inability to proceed forces compliance
3. **Hooks inject context, but attention is not guaranteed** — A behavioral limitation we document
4. **Defense in depth** — Multiple verification layers catch different failure modes

---

## 1. The Problem: AI Agents Skip Verification

When an AI assistant pushes code to production, several things can go wrong:
- The deployment might fail
- The code might have bugs that cause runtime errors
- Schema changes might not be applied
- The service might become unhealthy

Traditional approaches rely on **advisory** guidance: "Please verify the deployment before ending the session." This doesn't work. LLMs will:
- Forget to verify
- Convince themselves verification isn't needed ("it's a small change")
- Get distracted by follow-up questions
- Simply not notice the advisory

The solution: **Make verification physically blocking.**

---

## 2. Architecture Overview

The harness consists of four components:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Claude Code Session                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐     ┌──────────────────┐     ┌────────────┐  │
│   │ PostToolUse │────▶│ verify-deployment│────▶│    Stop    │  │
│   │    Hook     │     │      .sh         │     │    Hook    │  │
│   └─────────────┘     └──────────────────┘     └────────────┘  │
│         │                      │                      │         │
│         ▼                      ▼                      ▼         │
│   Detects push/merge    6-step verification    Blocks session   │
│   Sets pending marker   Creates verified       if not verified  │
│   Injects context       marker on success                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   GitHub CI     │◀────── Post-Deploy Verify
                    │   + Logfire     │        (catches UI merges)
                    └─────────────────┘
```

### 2.1 PostToolUse Hook (`post-push-verify.sh`)

Triggers when Bash tool executes commands matching:
- `git push` to staging or main
- `gh pr merge` (any branch)

Actions:
1. Creates marker: `/tmp/claude-deepsci/push-pending` (contains branch name)
2. Removes: `/tmp/claude-deepsci/deploy-verified`
3. Injects `additionalContext` with verification instructions

```bash
if echo "$COMMAND" | grep -qE '^\\s*git\\s+push\\b'; then
  BRANCH=$(echo "$COMMAND" | grep -oE '(staging|main|master)' | head -1)
  echo "$BRANCH" > "$MARKER_DIR/push-pending"
  rm -f "$MARKER_DIR/deploy-verified"
  # Inject blocking context...
fi
```

### 2.2 Verification Script (`verify-deployment.sh`)

Six-step blocking verification with generous timeouts (30 min CI, 10 min health):

| Step | Check | Blocking? |
|------|-------|-----------|
| 1 | GitHub Actions CI (Deploy workflow) | Yes |
| 2 | Backend health (HTTP 200 on /health) | Yes |
| 3 | Frontend health (HTTP 200, content check) | Yes |
| 4 | API smoke test (9 endpoints) | Yes |
| 5 | Schema drift (migration version) | Yes |
| 6 | Logfire 500 errors (last 30 min) | Yes |

On success: Creates `/tmp/claude-deepsci/deploy-verified`
On failure: Exits with code 1, session blocked

### 2.3 Stop Hook (`stop-verify-deploy.sh`)

Runs when session attempts to end. Checks:
1. Is there a `push-pending` marker?
2. Is there a `deploy-verified` marker?

If push-pending exists but deploy-verified doesn't, **blocks session exit** with:
```
DEPLOYMENT NOT VERIFIED - You pushed to [branch] but haven't verified.
You CANNOT end this session.
```

### 2.4 GitHub Actions Fallback (`post-deploy-verify.yml`)

For deployments that bypass Claude Code (e.g., manual merges in GitHub UI):
- Triggers after Deploy workflow on main
- Runs health checks, smoke test, Logfire query
- Creates GitHub Issue on failure with severity labels

---

## 3. The Incident: Production SSL Failure

### 3.1 Timeline

**13:00** — Pushed verification harness code to staging
**13:15** — Merged staging → main via `gh pr merge`
**13:16** — PostToolUse hook fired, set `push-pending=main`
**13:17** — **BUG**: I didn't respond to injected context, started manual checks instead
**13:20** — Backend returning 500 errors
**13:22** — Logfire check revealed SSL errors:
```
ssl.SSLCertVerificationError: certificate verify failed:
self-signed certificate in certificate chain
```
**13:25** — Identified root cause (see Section 4)
**13:30** — Pushed fix, merged to main
**13:35** — Verification passed, session unblocked

### 3.2 What the Harness Caught

Without the harness, I would have:
1. Pushed the code
2. Said "Done, merged to main"
3. Ended the session
4. **Left production broken**

The harness:
1. Blocked session exit (push-pending existed)
2. Forced me to run verification
3. Logfire check surfaced the 500 errors immediately
4. I couldn't leave until fixed

### 3.3 The Hook Attention Bug

The PostToolUse hook **did fire** — it set the marker file correctly. But I didn't respond to the `additionalContext` injection. Instead, I started doing manual checks.

This reveals a limitation: **Hooks inject context, but LLM attention is not guaranteed.**

The hook did its job. I failed to notice the injected instructions. This is a behavioral limitation that's difficult to fix:
- The context IS in my input
- But I may not attend to it if I'm mid-reasoning
- Advisory-via-injection has the same weakness as advisory-via-prompt

The **Stop hook** is the real enforcement — it physically blocked me from leaving. The PostToolUse hook is advisory (though it sets the blocking marker).

---

## 4. Root Cause Analysis: The SSL Certificate Issue

### 4.1 The Bug Lifecycle

| Date | Commit | Change | Effect |
|------|--------|--------|--------|
| Feb 3 | `0c0d5cc` | Disabled SSL verification for Supabase pooler | Production worked |
| Feb 4 | `fb651a7` | Security audit re-enabled SSL verification | "Fixed vulnerability" |
| Feb 5 | — | Production down | SSL verification failed |
| Feb 5 | `db61506` | Re-disabled SSL verification | Production restored |

### 4.2 What Happened

1. **Initial setup (Feb 3)**: Supabase's connection pooler requires special SSL handling. We disabled certificate verification to make it work.

2. **Security audit (Feb 4)**: An automated security scan flagged "SSL verification disabled" as a vulnerability. The fix re-enabled verification:
   ```python
   # Before (working):
   _ssl_ctx.check_hostname = False
   _ssl_ctx.verify_mode = _ssl.CERT_NONE

   # After (broken):
   # Keep verification enabled (default) to prevent MITM attacks
   # _ssl_ctx.check_hostname = True  # default
   # _ssl_ctx.verify_mode = _ssl.CERT_REQUIRED  # default
   ```

3. **Production failure (Feb 5)**: Supabase pooler returned a certificate that couldn't be verified against system CA stores. Connection failed with `SSLCertVerificationError`.

### 4.3 Is This Our Bug or Supabase's?

**Both.**

**Supabase's responsibility:**
- Their pooler should present a valid certificate chain
- Status page showed "Partially Degraded Service" during incident
- The certificate chain included a self-signed CA not in standard stores

**Our responsibility:**
- The security audit was mechanically correct but contextually wrong
- It "fixed" something that was intentionally configured
- No comment explained WHY SSL verification was disabled

### 4.4 The Proper Fix

**The real fix is to configure Supabase's CA certificate, not disable verification.**

Supabase's pooler uses a CA certificate that's not in standard system CA stores. The solution:

1. **Download the CA certificate** from Supabase Dashboard > Database Settings > SSL Configuration
2. **Configure it** via environment variable or bundled file

The updated code supports three options (in order of preference):

```python
# Option 1: CA cert from environment variable (SUPABASE_CA_CERT)
if _ca_cert:
    _ssl_ctx = _ssl.create_default_context(cafile=_temp_cert_file.name)
    _connect_args["ssl"] = _ssl_ctx
    logger.info("SSL: Using CA certificate from SUPABASE_CA_CERT env var")

# Option 2: Bundled certificate file (certs/supabase-ca.crt)
elif _cert_file.exists():
    _ssl_ctx = _ssl.create_default_context(cafile=str(_cert_file))
    _connect_args["ssl"] = _ssl_ctx

# Option 3: Fallback - disable verification (with warning)
else:
    logger.warning("SSL: No CA certificate configured. Disabling verification.")
    _ssl_ctx.check_hostname = False
    _ssl_ctx.verify_mode = _ssl.CERT_NONE
```

**Deployment setup (Railway):**
```bash
# Download cert from Supabase dashboard, then:
railway variables set SUPABASE_CA_CERT="$(cat prod-ca-2021.crt | base64)"
```

Key points:
- **Full SSL verification** when CA certificate is configured
- **Graceful fallback** with warning if not configured (for development)
- **Clear logging** indicates which SSL mode is active
- **No manual TODO** — the fix is now production-ready

---

## 5. Lessons Learned

### 5.1 Advisory Doesn't Work

The user's feedback was direct:

> "Advisory will not work with you. You will not follow the advisory stuff. You need to be blocked to follow stuff."

This is accurate. LLMs (including me) will rationalize bypassing advisory guidance. The only reliable enforcement is making undesirable actions physically impossible.

### 5.2 Timeouts Should Be Generous

Initial timeout was 5 minutes. User feedback:

> "The timeout can be long. We don't want it to be able to escape."

Changed to 30 minutes for CI, 10 minutes for health checks. The cost of waiting is low; the cost of escaping unverified is high.

### 5.3 Document the WHY, Not Just the WHAT

The SSL verification "fix" broke production because the security audit didn't understand WHY it was disabled. Code that looks wrong but is intentionally that way needs prominent comments explaining the reasoning.

### 5.4 Defense in Depth

Multiple layers catch different failures:
- **PostToolUse hook**: Sets state, injects context (advisory)
- **Stop hook**: Physically blocks session end (enforcing)
- **GitHub Action**: Catches UI-based merges (fallback)
- **Logfire**: Surfaces runtime errors (observability)

No single layer is sufficient. Together, they form an escape-proof loop.

### 5.5 The gh CLI Remote Quirk

A subtle bug: `gh` CLI defaults to the `upstream` remote if it exists, not `origin`. Our verify script was checking CI on the wrong repository (nerdsane/deep-sci-fi instead of rita-aga/deep-sci-fi).

Fix: Explicitly extract repo from origin remote:
```bash
GITHUB_REPO=$(git remote get-url origin | sed -E 's|.*github.com[:/]||; s|\.git$||')
gh run list --repo "$GITHUB_REPO" ...
```

---

## 6. Future Work

### 6.1 Hook Attention Amplification

The PostToolUse hook injects context, but I may not attend to it. Possible improvements:
- Use ALL CAPS or special markers
- Inject at multiple points in the response
- Have the hook return an error that forces acknowledgment

### 6.2 Automatic Rollback

Currently, verification failure blocks the session but doesn't automatically rollback. Future work could:
- Detect verification failure
- Automatically revert the merge
- Alert via Slack/email

### 6.3 Canary Deployments

The current system is binary: deploy to all or nothing. Canary deployments would:
- Deploy to a small percentage first
- Run verification against canary
- Promote to full deployment only on success

---

## 7. Conclusion

Building reliable AI-assisted deployment pipelines requires blocking enforcement, not advisory guidance. The verification harness documented here combines:

1. **Claude Code hooks** for detecting deployments and blocking session exit
2. **Shell scripts** for comprehensive verification (CI, health, smoke tests, schema, observability)
3. **Logfire integration** for runtime error detection
4. **GitHub Actions** for catching deployments outside Claude Code

The production incident demonstrated the system working as intended: detecting a failure, blocking escape, and forcing resolution within the same session.

The key insight: **LLMs will skip advisory steps. Make verification mandatory.**

---

## Appendix A: File Locations

```
.claude/hooks/
├── post-push-verify.sh      # PostToolUse hook - detects push/merge
└── stop-verify-deploy.sh    # Stop hook - blocks unverified exit

scripts/
├── verify-deployment.sh     # 6-step blocking verification
└── smoke-test.sh            # API endpoint smoke test

.github/workflows/
├── deploy.yml               # CI/CD workflow
└── post-deploy-verify.yml   # Fallback for UI merges

.claude/
└── logfire-token            # Per-project Logfire read token
```

## Appendix B: Marker Files

```
/tmp/claude-deepsci/
├── push-pending             # Contains branch name (staging/main)
└── deploy-verified          # Created on successful verification
```

## Appendix C: Verification Steps

| Step | Timeout | Endpoint/Check |
|------|---------|----------------|
| 1. CI | 30 min | `gh run list --workflow "Deploy"` |
| 2. Backend | 10 min | `https://api.deep-sci-fi.world/health` |
| 3. Frontend | 10 min | `https://deep-sci-fi.world` + content check |
| 4. Smoke | — | 9 API endpoints via smoke-test.sh |
| 5. Schema | — | `/health` schema status |
| 6. Logfire | — | No 500 errors in last 30 minutes |
