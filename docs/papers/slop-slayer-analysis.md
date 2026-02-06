# Slop Slayer: An Experience Report on RLM-Powered Codebase Auditing

**Author:** Claude (Opus 4.5), assisted by Slop Slayer MCP tools
**Date:** February 4, 2026
**Project:** Deep Sci-Fi — a social platform for AI-generated sci-fi worlds (~40,000 lines, Next.js + FastAPI)

---

## Abstract

This paper documents the experience of using Slop Slayer — an MCP-based codebase health analysis tool powered by Recursive Language Model (RLM) patterns — to audit a production web application, and an empirical comparison against a direct LLM audit of the same codebase without Slop Slayer tools.

The direct LLM approach achieved significantly higher recall (83.3% vs. 55.6%) and found the codebase's most critical vulnerability (SSRF via unvalidated callback URLs) — a finding that required cross-file threat modeling that Slop Slayer's per-file isolation pattern structurally prevented.

We analyze why: Slop Slayer's tools excel at mechanical, exhaustive pattern scanning, but its per-file `sub_llm()` architecture cannot reason across files about data flow, architectural intent, or deployment security. Its Rust-focused skill prompt lacks instructions for the categories that matter most in full-stack web projects — SSRF, ORM transaction safety, orphaned features, cross-stack constant sync.

We propose comprehensive full-stack web audit instructions (Section 6.1), argue that instructions matter more than tools for audit quality, and recommend a hybrid approach: Slop Slayer's infrastructure (structured findings, health metrics, trend tracking) combined with a cross-file reasoning layer for security and architectural analysis.

---

## 1. What Is Slop Slayer?

Slop Slayer is a set of MCP (Model Context Protocol) tools that enable an LLM to perform systematic codebase health audits. Its core innovation is the **RLM (Recursive Language Model) pattern**: rather than reading files into the LLM's context window, files are loaded onto a server, and the LLM writes Python code that executes server-side with access to a `sub_llm()` function. This enables:

- **For-loops over sub_llm calls**: Analyze N files in a single tool call
- **Server-side file storage**: Files never enter the LLM's context window
- **Programmatic aggregation**: Results collected and synthesized in code
- **Structured persistence**: Findings recorded in a database with severity, type, and location

The tool provides two categories of functionality:

1. **RLM Tools** — `repl_load`, `repl_exec`, `repl_clear` for loading files and executing analysis code with embedded LLM calls
2. **Issue Management Tools** — `slop_record_finding`, `slop_triage`, `slop_clusters`, `slop_health` for tracking, prioritizing, and summarizing findings

---

## 2. The Audit Process

### 2.1 Setup and File Loading

The audit began by loading all source files into server-side variables:

```
backend_api:        18 files (404.5KB) — FastAPI route handlers
backend_utils:       9 files (57.4KB)  — Python utilities
backend_db:          3 files (59.0KB)  — Database models and connection
frontend_components: 31 files (188.9KB) — React components
frontend_pages:     14 files (103.3KB) — Next.js pages
frontend_lib:        3 files (17.3KB)  — TypeScript utilities
```

**Total: 78 files, 830KB loaded server-side without consuming any context window.**

This is the first critical advantage. Reading 830KB of source code directly would consume roughly 200,000 tokens — far exceeding a single context window. With Slop Slayer, all 78 files were available for analysis simultaneously.

### 2.2 Parallel RLM Analysis

Four analysis passes ran in parallel, each iterating over a file group with targeted sub_llm queries:

1. **Backend API analysis** — Dead code, orphaned code, code quality, duplicate patterns
2. **Backend utilities analysis** — Dead code, code quality, orphaned code
3. **Frontend components analysis** — Dead code, duplicates, code quality, orphaned code
4. **Database models analysis** — Model issues, dead code, quality

Each pass used a for-loop over files with `sub_llm(content, query)`, where the query was a structured prompt asking for specific issue types with severity ratings and line numbers.

### 2.3 Finding Recording and Triage

The RLM analysis produced raw findings per file. These were reviewed, and 26 significant issues were recorded using `slop_record_finding`, categorized by type and severity. The tool then provided:

- **Health ratio**: 95.3% healthy (38,817 of 40,720 lines)
- **Severity breakdown**: 3 critical, 15 high, 8 medium
- **Clusters**: 4 type clusters, 6 location clusters
- **Triage ordering**: Critical issues surfaced first

---

## 3. What Slop Slayer Discovered

### 3.1 Critical Security Issues

**SQL Injection Risk in `platform/backend/utils/embeddings.py:102`**

```python
# The embedding vector is converted to string and interpolated into raw SQL
query = f"""
    SELECT id, premise, 1 - (premise_embedding <=> CAST('{str(embedding)}' AS vector)) as similarity
    FROM platform_proposals
    WHERE premise_embedding IS NOT NULL
"""
```

While the embedding comes from OpenAI's API (not user input directly), the pattern of string interpolation into SQL is dangerous. If any path allows attacker-controlled content into the embedding pipeline, this becomes exploitable.

**SSL Verification Disabled in `platform/backend/db/database.py:33`**

```python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE  # Allows MITM attacks
```

This was likely added to work around a Supabase pooler certificate issue, but it disables all TLS security guarantees for database traffic.

**Bare Exception Swallowing in `platform/backend/api/feedback.py:165`**

```python
except:  # Catches KeyboardInterrupt, SystemExit — everything
    return False  # No logging, no context, impossible to debug
```

### 3.2 Data Integrity Issues

**Missing Database Commits in `platform/backend/api/social.py`**

Multiple endpoints (`react()`, `follow()`) call `db.add(interaction)` without a subsequent `db.flush()` or `db.commit()`. In async SQLAlchemy, this means changes may never persist. The `_update_reaction_count()` function operates without a transaction wrapper, risking partial updates.

**Missing UNIQUE Constraint in `platform/backend/db/models.py`**

`SocialInteraction` has an index on `(user_id, target_type, target_id, interaction_type)` but no UNIQUE constraint — allowing duplicate reactions from the same user on the same target.

### 3.3 Major Duplication

**Feed Endpoint — 285 Lines of Repeated Boilerplate (`platform/backend/api/feed.py`)**

The `get_feed()` function executes 8 sequential database queries, each following an identical pattern:

```python
# This pattern repeats 6+ times with minor variations:
query = select(Model).options(selectinload(Model.relationship)).where(...)
result = await db.execute(query)
items = result.scalars().all()
for item in items:
    feed_items.append({
        "type": "item_type",
        "sort_date": item.created_at,
        "id": str(item.id),
        "agent": {"id": str(item.user.id), "username": f"@{item.user.username}", "name": item.user.name},
        "preview": item.field[:100] + "..." if len(item.field) > 100 else item.field,
    })
```

The agent serialization, string truncation, and query structure are each duplicated 6 times.

**Suggestions Endpoint — 230 Lines of Near-Identical Code (`platform/backend/api/suggestions.py`)**

`suggest_proposal_revision()` and `suggest_aspect_revision()` are functionally identical (~140 lines each). `list_proposal_suggestions()` and `list_aspect_suggestions()` differ only in a single filter value. `accept_suggestion()` and `reject_suggestion()` both contain a duplicated 16-line target lookup block.

### 3.4 Orphaned Frontend Features

**CommentThread and ReactionButtons** — Both components contain commented-out API fetch calls with TODO markers. The comment form clears state without persisting. The Reply button renders but has no functionality. These represent incomplete features shipped to production.

### 3.5 Dead Code

- `platform/backend/api/heartbeat.py` — `HEARTBEAT_TEMPLATE` (244 lines) defined but never referenced
- `platform/components/world/WorldCatalog.tsx` — `hasMore` state variable set but never used
- `platform/components/world/WorldRow.tsx` — `WorldCardSkeleton` imported but never used
- `platform/app/page.tsx` — `API_BASE` defined but never used

---

## 4. What I Could Discover Without Slop Slayer

### 4.1 Definitely Findable

An LLM reading files directly would reliably catch:

- **Critical security issues** — SQL injection patterns, disabled SSL, bare excepts are pattern-recognizable in any individual file
- **Orphaned social components** — Commented-out code with TODO markers is visually obvious
- **Major duplication in single files** — The 285-line feed function's internal repetition is hard to miss when reading the file
- **Missing flush/commit** — Standard code review knowledge applied to `social.py`
- **Hardcoded mock data** — The `ReviewForm.tsx` mock reviewer data (`'current_user'`, `'You'`, `'@you'`) is immediately suspicious

### 4.2 Likely Findable with Effort

With deliberate cross-file investigation:

- **Cross-file duplication** — The suggestions.py proposal/aspect mirroring requires reading both functions carefully
- **Model relationship gaps** — Missing `back_populates` requires understanding both sides of each relationship
- **Frontend API pattern inconsistency** — Noticing that pages duplicate `API_BASE` instead of using `lib/api.ts` requires reading multiple pages

### 4.3 Likely Missed

Without systematic full-codebase analysis:

- **Scattered constant synchronization** — `utils/activity.py` has a comment "# must match heartbeat.py" indicating fragile manual sync between files. This only surfaces when you read both files and notice the duplication.
- **The full scope of duplication** — Knowing that 8 callback URLs are hardcoded across `utils/notifications.py` requires reading every notification helper. Knowing that agent serialization is duplicated in 3 places across `auth.py` requires reading the whole file carefully.
- **Low-severity dead code** — Unused imports, unused state variables, and unused constants in files that otherwise look fine.
- **The complete picture** — By file 40 of a manual review, the LLM has lost context from file 3. Patterns that span the codebase become invisible.

### 4.4 The Coverage Gap

My estimate: without Slop Slayer, I would find **60-70% of the issues** discovered in this audit. The missing 30-40% would be:

- Cross-file pattern issues (constants sync, duplicated serialization across modules)
- Low-severity dead code in otherwise clean files
- The quantitative picture (exactly how many files share a pattern)
- Issues in files I'd deprioritize due to context limits

---

## 5. What Made Slop Slayer Effective

### 5.1 The RLM Pattern Solves the Context Problem

The fundamental constraint of LLM-based code review is the context window. A 128K token window holds roughly 50,000 lines of code — enough for one pass through this codebase, but not enough to analyze it while also reasoning about findings, comparing patterns across files, and generating structured output.

Slop Slayer's RLM pattern breaks this constraint:

1. **Files load server-side** — 830KB of source code stored without consuming tokens
2. **Sub-LLM calls are independent** — Each file analyzed in isolation with a focused prompt
3. **Only findings return** — The analysis results (not the full files) enter the orchestrating LLM's context
4. **Parallel execution** — Multiple file groups analyzed concurrently

This is not just a performance optimization. It changes what's *possible*. Without RLM, a thorough audit of 78 files would require multiple conversation turns, progressive summarization, and inevitable information loss. With RLM, every file gets the same quality of analysis.

### 5.2 Structured Persistence Creates Accountability

Recording findings in a database with `slop_record_finding` creates a structured artifact that:

- Survives context window compression
- Can be triaged, clustered, and queried
- Provides a health ratio (95.3%) that tracks over time
- Creates a clear remediation checklist

Without this, the audit output would be a long prose message that's harder to action.

### 5.3 Clustering Reveals Systemic Patterns

The `slop_clusters` tool grouped 26 individual findings into 4 type clusters and 6 location clusters. This transforms "here are 26 bugs" into "here are 4 systemic patterns to address." The cluster view revealed:

- **16 code quality issues** — suggesting a need for linting/review standards
- **4 duplicate implementations** — suggesting a need for shared helpers
- **4 dead code instances** — suggesting a need for unused code detection in CI
- **2 orphaned code instances** — suggesting incomplete feature work

---

## 6. Tools vs. Instructions: The Two Halves of Slop Slayer

The current Slop Slayer skill is heavily optimized for Rust distributed systems. Its skill prompt dedicates entire sections to TLA+ verification chains, DST (Deterministic Simulation Testing), Rust naming conventions (RFC 430), and FoundationDB/TigerBeetle testing principles. These are excellent — for Rust projects. But the skill's power comes from two distinct sources, and understanding the split matters:

1. **Tools** — The RLM REPL, file loading, sub_llm, finding database, health metrics
2. **Instructions** — The skill prompt that tells the LLM *what to look for*, *how to prioritize*, and *what constitutes a real issue vs. a false positive*

The tools are language-agnostic. `repl_load("**/*.py")` works as well as `repl_load("**/*.rs")`. The instructions are not. And for this audit, the instructions were the limiting factor — I had to improvise what to look for in a full-stack web project because the skill prompt didn't tell me.

This section covers both: new tools that would help, and — more importantly — the instructions a Slop Slayer skill should provide for full-stack TypeScript + Python projects.

### 6.1 What the Skill Prompt Should Teach: Full-Stack Web Audit Instructions

The current skill prompt has a "What to Investigate" section covering dead code, orphaned code, duplicates, code quality, Rust readability, verification chains, and DST quality. For full-stack web projects, an equivalent section should cover the following categories. These are not tool features — they're **instructions that shape the LLM's analysis prompts** when writing `sub_llm()` queries.

#### 6.1.1 The API Boundary Contract

**Why this matters:** In a full-stack app, the API boundary is where most bugs live. The backend returns JSON; the frontend consumes it. Neither side enforces the other's types at runtime.

**What to instruct the LLM to check:**

- **Response shape drift:** Does the backend endpoint return fields that the frontend type definition doesn't expect? Does the frontend assume fields exist that the backend doesn't always include?
- **Optionality mismatches:** Backend returns `acclaim_count: int` (always present), but frontend defines `acclaim_count?: number` (optional). Or worse — backend sometimes returns `null` but frontend assumes the field is always a number.
- **Enum value sync:** Backend defines `ProposalStatus` as a Python enum. Frontend has a matching TypeScript type or string union. Are they in sync? Does the frontend handle all enum values?
- **URL path consistency:** Frontend fetch calls hit `/api/stories/{id}/reviews`. Does that exact route exist in the backend router? Is it `GET` or `POST`?

**Concrete example from this audit:** `platform/lib/api.ts` defines `StoryReviewItem` with optional `author_id`, `status`, `acclaim_count` — but the backend's review endpoint always returns these fields. The optionality hides potential null dereferences and makes the code unnecessarily defensive.

**Concrete example from this audit:** At least 6 Next.js page files construct their own `API_BASE` from environment variables instead of using the centralized `lib/api.ts` client. Each constructs the URL slightly differently. The skill should instruct: "Check if a centralized API client exists. If yes, flag any file that constructs API URLs independently."

#### 6.1.2 Database Transaction Safety (ORM-Specific)

**Why this matters:** Async ORMs like SQLAlchemy with asyncio have subtle commit semantics. `db.add()` doesn't persist. `db.flush()` writes to the transaction but doesn't commit. The session's auto-commit behavior depends on configuration. Missing a commit means data silently vanishes.

**What to instruct the LLM to check:**

- **Add without commit:** Any `db.add(obj)` or `db.execute(update(...))` that isn't followed by `db.flush()`, `db.commit()`, or covered by a context manager that auto-commits
- **Partial transaction safety:** Multiple writes in one endpoint without a transaction wrapper. If write 2 fails, write 1 is already committed — leaving inconsistent state.
- **Raw SQL in ORM code:** Any use of `db.execute(text(...))` deserves scrutiny. Is it parameterized? Does it bypass ORM relationships? Does it handle the commit?
- **Cascade and relationship loading:** `selectinload` vs. lazy loading inconsistency. Some endpoints load relationships eagerly, others don't, causing N+1 queries in some paths and not others.

**Concrete example from this audit:** `social.py`'s `react()` endpoint calls `db.add(interaction)` without flushing or committing. The `_update_reaction_count()` helper modifies counts without a transaction wrapper. If the reaction count update fails after the interaction is added, the data is inconsistent.

#### 6.1.3 Frontend Resilience Patterns

**Why this matters:** Server-rendered and client-rendered React components fail differently. A server component that throws crashes the page with no recovery. A client component without an error boundary crashes its parent tree. These are not bugs in logic — they're missing infrastructure.

**What to instruct the LLM to check:**

- **Error boundaries:** Does every page-level component have an `error.tsx` (Next.js App Router) or a React error boundary wrapper? Does every component that fetches data handle the error state?
- **Loading states:** Does every async component have a `loading.tsx`, a Suspense boundary, or a skeleton/spinner? Or does the user see a blank page while data loads?
- **Stale closure bugs:** In React hooks, does `useEffect` or `useCallback` reference state variables that aren't in the dependency array? This causes the callback to capture an old value.
- **Race conditions on fetch:** When a filter/parameter changes, does the component cancel the previous in-flight request? Or can an older response arrive after a newer one and overwrite it?
- **Null safety on API data:** Components that render API data should guard against `null`/`undefined` at every level. `data.agent.username` crashes if `agent` is null.

**Concrete example from this audit:** `FeedContainer.tsx` has a `loadFeed` function that captures `cursor` state in a closure but doesn't include it in the dependency array. When the cursor updates, the old function still uses the stale cursor value, potentially requesting the wrong page.

**Concrete example from this audit:** Nearly every Next.js page renders data-fetching components without Suspense boundaries or `error.tsx` files. A single failed API call can crash the entire page tree with no recovery option.

#### 6.1.4 Orphaned Features vs. Incomplete Features

**Why this matters:** Full-stack web projects accumulate UI that was built before the backend was ready, or backend endpoints that the frontend never wired up. These are different from dead code — they look functional but don't actually work.

**What to instruct the LLM to check:**

- **Commented-out fetch calls:** A component that renders a form, has a submit handler, but the actual API call is commented out with `// TODO: implement`
- **Buttons that do nothing:** UI elements (Reply, Share, Follow) that render but have empty or no-op click handlers
- **Form submissions that clear state without persisting:** A form that resets its inputs after "submit" but never actually sends data to the backend
- **Backend endpoints with no frontend consumer:** An API route that exists but is never called from any frontend code

**Concrete example from this audit:** `CommentThread.tsx` renders a comment input form with a "POST" button. The submit handler sets `isSubmitting = true`, clears the input, and sets `isSubmitting = false`. The actual fetch call is commented out. From the user's perspective, they type a comment, click POST, the input clears — and the comment vanishes. The Reply button also renders but has no click handler.

**Concrete example from this audit:** `ReactionButtons.tsx` renders reaction buttons with counts and animations. The API integration is commented out. Users can click reactions and see the UI animate, but nothing persists.

These are more damaging than dead code. Dead code wastes space. Orphaned features **lie to users**.

#### 6.1.5 Hardcoded Constants and Cross-File Sync

**Why this matters:** Web projects accumulate magic numbers and configuration values that get copy-pasted across files instead of centralized. When one changes, the others don't.

**What to instruct the LLM to check:**

- **Same constant in multiple files:** Pagination limits, timeout values, threshold numbers that appear in more than one file. Especially when one file has a comment like "must match X.py"
- **Constants that span the stack:** A value like `APPROVAL_THRESHOLD = 2` that appears as a Python variable, appears as `2` in a SQL query, and appears as the string `"2"` in React JSX
- **Environment variable access patterns:** Is `os.getenv("KEY")` or `process.env.KEY` called in many files, or centralized in a config module? Multiple access points mean multiple fallback defaults that can diverge.
- **TEST_MODE flags:** Test mode gating (`if TEST_MODE_ENABLED`) scattered across endpoint files instead of centralized in middleware or a decorator

**Concrete example from this audit:** `utils/activity.py` defines `ACTIVE_THRESHOLD_HOURS = 12`, `WARNING_THRESHOLD_HOURS = 24`, `DORMANT_THRESHOLD_DAYS = 7` with the comment `# Activity thresholds (must match heartbeat.py)`. The same constants appear in `api/heartbeat.py`. If someone updates heartbeat.py and forgets activity.py, the system has inconsistent behavior with no error.

#### 6.1.6 Serialization Duplication

**Why this matters:** Full-stack apps convert database models to JSON responses constantly. Without a serialization layer (Pydantic response models, serializer functions), every endpoint hand-builds response dicts. This leads to inconsistency and duplication.

**What to instruct the LLM to check:**

- **Inline dict construction:** Endpoints that build `{"id": str(obj.id), "name": obj.name, ...}` by hand instead of using a shared serializer
- **Same model, different serializations:** Does `User` get serialized as `{"id", "username", "name"}` in one endpoint and `{"id", "username", "display_name"}` in another?
- **Truncation patterns:** String slicing like `field[:100] + "..."` repeated in multiple places with potentially different length limits
- **Date formatting:** Is `datetime.now(timezone.utc)` called directly everywhere, or is there a consistent timestamp utility?

**Concrete example from this audit:** `feed.py` serializes the agent/user object identically 6 times: `{"id": str(user.id), "username": f"@{user.username}", "name": user.name}`. `auth.py` serializes the same user object 3 times with slight variations. `agents.py` does it again. None of these share a function.

#### 6.1.7 Exception Handling Anti-Patterns

**Why this matters:** Web backends need to catch exceptions to return proper HTTP responses. But the wrong catch pattern masks bugs, prevents debugging, and can even prevent process shutdown.

**What to instruct the LLM to check:**

- **Bare `except:`** — Catches `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` — breaks process management
- **`except Exception` without logging** — Catches the error and returns a generic response, but no one can diagnose what went wrong
- **Silent fallback behavior** — An exception handler that returns a default value (empty list, False, None) without indicating that an error occurred. The caller doesn't know the operation failed.
- **Catching too broadly then acting too narrowly** — `except (ValueError, ImportError, Exception)` where each branch does the same thing
- **Missing retry for transient failures** — External API calls (OpenAI, webhooks) that fail once and give up, when a single retry would succeed

**Concrete example from this audit:** `feedback.py:165` has a bare `except:` that catches *everything*, returns `False`, and logs nothing. `notifications.py:131` catches `Exception` on webhook delivery, masking whether the failure is a network timeout (retryable) or a programming error (not retryable). `proposals.py` catches `ValueError` from missing API keys and silently skips similarity checks — the user never knows their proposal wasn't checked for duplicates.

#### 6.1.8 Accessibility Gaps

**Why this matters:** React component libraries accumulate interactive elements — buttons, links, forms, icons — that work visually but fail for screen readers, keyboard navigation, or assistive technology.

**What to instruct the LLM to check:**

- **Missing `aria-label` on icon buttons** — A button with only an SVG icon has no accessible name
- **Missing `aria-label` on links** — A link that wraps an image or card needs to describe where it goes
- **Form inputs without labels** — Using `placeholder` instead of `<label>` fails WCAG
- **Emoji as semantic content** — Using a fire emoji for "hot" or a star for "featured" without an accessible text alternative
- **Missing `aria-busy` on loading states** — When a button is loading, screen readers don't know
- **Index as key in lists** — Using array index as React key causes rendering bugs when lists reorder

**Concrete example from this audit:** `PixelIcon.tsx` defines 35+ SVG icon components. None have `aria-hidden="true"` (for decorative icons) or `aria-label` (for semantic icons). `BottomNav.tsx` navigation links have icons but no `aria-label` — screen readers can't announce where each link goes. `ReviewCard.tsx` uses array index as key for review issue lists.

### 6.2 New Tools for Full-Stack Projects

Beyond instructions, certain tools would provide capabilities that instructions alone can't replicate:

#### 6.2.1 API Contract Verifier

A tool that parses FastAPI route decorators and compares against TypeScript type definitions:

```
verify_api_contracts(backend_routes, frontend_types)
→ "GET /api/stories returns {acclaim_count: int} but StoryItem type has acclaim_count?: number"
→ "POST /api/dwellers/{id}/action exists in backend but no corresponding fetch call in frontend"
```

This requires structural parsing that `sub_llm()` can approximate but a dedicated tool would do reliably.

#### 6.2.2 Database Migration Drift Detector

Compare SQLAlchemy models against the latest Alembic migration to detect:

- Columns in models that have no migration
- Migrations that reference columns not in models
- Index/constraint mismatches

This is particularly relevant for Deep Sci-Fi, where CLAUDE.md documents extensive migration gotchas and 5 progressive sync migrations suggest a history of drift.

#### 6.2.3 Transaction Trace Analyzer

For SQLAlchemy async code, trace database operations per endpoint:

```
analyze_transaction_safety(endpoint_code)
→ "social.py:react() — db.add() at line 65, no flush/commit before return at line 78"
→ "social.py:follow() — db.add() at line 154, no flush/commit before return at line 170"
```

This is mechanically parseable — find all `db.add()`, `db.execute()`, `db.delete()` calls and check if the function contains a corresponding `db.flush()`, `db.commit()`, or `async with db.begin()`.

#### 6.2.4 Frontend Error Boundary Coverage Map

Map the component tree and report:

```
error_boundary_coverage()
→ "app/worlds/page.tsx — NO error.tsx, NO loading.tsx"
→ "app/feed/page.tsx — NO error.tsx, NO loading.tsx"
→ "components/feed/FeedContainer.tsx — fetches data, NO error boundary wrapper"
→ Coverage: 2 of 14 pages have error handling (14%)
```

#### 6.2.5 Callback/URL Registry Verifier

Extract all hardcoded URL patterns from backend code and cross-reference against actual routes:

```
verify_internal_urls(notification_code, api_routes)
→ "notifications.py:212 references /api/suggestions/{id}/respond — ROUTE EXISTS"
→ "notifications.py:246 references /api/dwellers/{id}/spoken-to — NO SUCH ROUTE"
```

#### 6.2.6 Test Coverage Mapper

Map test files to the source they cover:

```
test_coverage_map(test_files, source_files)
→ "backend/api/dwellers.py (1980 lines) — covered by tests/test_dwellers.py"
→ "backend/api/suggestions.py (619 lines) — NO TEST FILE"
→ "backend/utils/nudge.py (289 lines) — NO TEST FILE"
→ "components/feed/FeedContainer.tsx (500 lines) — NO TEST FILE"
→ API endpoint coverage: 12 of 18 endpoints tested (67%)
```

#### 6.2.7 Environment Configuration Auditor

Verify env var usage is consistent:

```
audit_env_config(source_files, env_example)
→ "backend/api/events.py reads TEST_MODE_ENABLED with default 'true' — production risk"
→ "backend/utils/embeddings.py reads OPENAI_API_KEY — NOT in .env.example"
→ "6 files construct API_BASE from NEXT_PUBLIC_API_URL with different fallbacks"
```

### 6.3 Priority by Project Type — The Missing Section

The current skill prompt has a "Priority by Project Type" section:

```
Distributed Systems (Rust): Verification Chain → DST Quality → Duplicates → Dead Code → Readability
Regular Rust: Dead code → Duplicates → Readability → Code quality
Other Languages: Dead code → Duplicates → Code quality
```

"Other Languages" is too generic. Full-stack web projects have their own priority order because their failure modes are different. A Rust distributed system fails through state corruption; a web app fails through data not persisting, UI lying to users, and API contracts drifting.

**Proposed priority for Full-Stack Web (TypeScript + Python/Node):**

```
1. API Boundary Contracts   — Frontend/backend type drift causes runtime crashes
2. Transaction Safety       — Missing commits cause silent data loss
3. Orphaned Features        — UI that lies to users is worse than dead code
4. Exception Handling       — Silent failures mask production bugs
5. Serialization Duplicates — Inconsistent responses confuse consumers
6. Hardcoded Constant Sync  — Cross-file magic numbers drift over time
7. Frontend Resilience      — Missing error boundaries, loading states, race conditions
8. Dead Code                — Wasted space, confusion, but doesn't break anything
9. Accessibility            — Exclusion is a bug
```

This ordering reflects the damage each category causes in production. API contract drift and missing commits can lose user data. Orphaned features erode trust. Dead code just wastes disk space.

---

## 7. Empirical Comparison: What Actually Happened

### 7.1 The Experiment

We proposed a comparison methodology in the original version of this paper. Then we ran it. A separate Claude instance (same model: Opus 4.5) audited the same codebase without Slop Slayer tools — using only direct file reading (Read, Grep, Glob). The results contradicted our predictions.

### 7.2 Results

| Metric | Slop Slayer (Report A) | Direct LLM (Report B) |
|--------|----------------------|----------------------|
| **Total verified issues found** | 20 | 30 |
| **Unique issues (only this approach found)** | 6 | 16 |
| **Recall (against union as ground truth)** | **55.6%** | **83.3%** |
| **Most critical finding** | SSL CERT_NONE | SSRF via callback URL |
| **Severity accuracy** | Overstated 2 findings | Calibrated |
| **Quantitative precision** | Approximate line counts | Exact line counts |

The direct LLM approach had **28 percentage points higher recall** and found the single most critical vulnerability in the codebase.

### 7.3 What the Direct LLM Found That Slop Slayer Missed

**16 verified unique findings**, including:

| Finding | Why Slop Slayer Missed It |
|---------|--------------------------|
| **SSRF via callback URLs** (Critical) | Requires threat modeling: agents are untrusted, they supply URLs, server POSTs to them, no IP validation. sub_llm analyzed files in isolation — couldn't chain this reasoning across registration → notification → HTTP request. |
| **`agent_error()` helper exists but 209 HTTPExceptions built manually** (Critical) | Requires reading CLAUDE.md as architectural intent and comparing against reality. Slop Slayer used CLAUDE.md for workflow, not as audit ground truth. |
| **Test mode defaults to "true" in 5 files** (High) | Requires understanding deployment security implications of default env values. |
| **6 unused API functions in lib/api.ts** (High) | Requires cross-referencing exports against imports across entire project. RLM loops analyzed files independently. |
| **8 unused TypeScript types** (High) | Same: cross-file import graph analysis. |
| **4 backend packages in frontend package.json** (High) | Requires comparing package.json against actual frontend imports. |
| **11+ unused Tailwind tokens** (High) | Requires comparing tailwind.config.ts against actual class usage in templates. |
| **Callback tokens stored plaintext** (Medium) | Requires noticing API keys ARE hashed but tokens are NOT. |
| **Missing rate limits on POST endpoints** (High) | Requires systematic endpoint-by-endpoint decorator audit. |
| **Precise function measurements** (take_action: 255 lines, build_agent_context: 330 lines, get_dweller_state: 150 lines) | Slop Slayer gave approximations ("280-line function", "300-line component"). Direct LLM measured exactly. |

### 7.4 What Slop Slayer Found That the Direct LLM Missed

**6 verified unique findings:**

| Finding | Why Direct LLM Missed It |
|---------|--------------------------|
| **Stale closure bug in FeedContainer** (High) | Requires understanding JavaScript closure semantics in React hook dependency arrays. The only genuine runtime *bug* either approach found. |
| **SSL CERT_NONE in database.py** (Critical) | Direct LLM may have seen the conditional guard (`if "supabase" in URL`) and considered it acceptable, or simply missed it. |
| **Cross-file constant coupling** (activity.py ↔ heartbeat.py) (Medium) | Fragile "must match" comment linking two files. Pattern-matching strength. |
| **Dead `hasMore` state variable** (Medium) | State set but never consumed in JSX. Minor but real. |
| **social.py potential missing commits** (High) | Depends on session auto-commit behavior — may be a false positive. |
| **Timezone detection bug in utils.ts** (Medium) | `dateStr.includes('-', 10)` is unreliable for ISO dates. |

### 7.5 Where Slop Slayer Overstated Severity

| Issue | Slop Slayer Rating | Actual Severity | Why |
|-------|-------------------|-----------------|-----|
| "SQL injection" in embeddings.py | Critical | Medium | The `str(embedding)` is passed as a parameterized bind variable via `text()`, not string-interpolated. It's raw SQL mixed with ORM — a code smell, not injectable. Direct LLM correctly rated it medium. |
| "300-line mega-component" (FeedContainer) | High | Medium | File is actually 553 lines. Slop Slayer undercounted while overstating the issue. |
| "285-line duplicated function" (feed.py) | High | Medium | Structural repetition within a single function, not a literal duplicate. |

### 7.6 Category-by-Category Winner

| Category | Winner | Margin |
|----------|--------|--------|
| **Security / Threat Modeling** | Direct LLM | Decisive (8 vs. 3 findings) |
| **Dead Code Discovery** | Direct LLM | Clear (unused functions, types, packages, tokens) |
| **Code Duplication (counting)** | Direct LLM | Modest (52+ get-or-404, 209 manual HTTPExceptions, 76 selectinload) |
| **Oversized File/Function Identification** | Direct LLM | Clear (exact measurements, more files) |
| **Architectural Intent vs. Reality** | Direct LLM | Clear (agent_error unused, test mode defaults) |
| **Runtime Bug Detection** | Slop Slayer | Narrow (stale closure is the only real bug found by either) |
| **Subtle Pattern Matching** | Slop Slayer | Narrow (SSL flag, cross-file constants, dead state vars) |
| **Quantitative Precision** | Direct LLM | Clear (exact line counts vs. approximations) |
| **Severity Calibration** | Direct LLM | Modest (no overstated findings) |

### 7.7 Why the Prediction Was Wrong

The original paper predicted Slop Slayer would have higher recall on cross-file issues. The opposite happened. Three factors explain this:

**1. Per-file isolation killed cross-file reasoning.**

The RLM pattern's strength — analyzing each file independently via `sub_llm()` — is also its weakness. The SSRF vulnerability spans three files: registration (auth.py) → callback storage (models.py) → HTTP request (notifications.py). No single file looks dangerous. The direct LLM could hold the full call chain in context and reason about it holistically.

Similarly, finding that `agent_error()` exists in `utils/errors.py` but is used in only 2 of 17 API files requires comparing one file's exports against 17 files' imports. The RLM loop analyzed each API file in isolation — it never asked "is there a helper I should be using?"

**2. The direct LLM used project documentation as audit ground truth.**

The direct LLM read CLAUDE.md and treated its guidelines as assertions to verify. "CLAUDE.md says use `agent_error()` — let me check if it's actually used." "CLAUDE.md says create migrations — let me check if models match migrations." Slop Slayer's skill prompt doesn't instruct the LLM to audit against project documentation.

**3. The direct LLM was more quantitative.**

It counted: 209 manual HTTPExceptions. 52 get-or-404 patterns. 76 selectinload uses. 10 permission checks. 16 console.error calls. 6 unused functions. 8 unused types. These exact counts make findings more actionable and harder to dismiss. Slop Slayer's `sub_llm()` queries returned qualitative assessments ("repeated multiple times", "8+ times") that were less precise and sometimes wrong.

### 7.8 What This Means for Slop Slayer

The experiment answered the falsifiability question from the original paper:

> "The tool provides no incremental value if: Direct LLM achieves the same recall and coverage within the same time budget"

The direct LLM achieved **higher** recall with **better** precision. Slop Slayer's incremental value was real but narrow: the stale closure bug and SSL CERT_NONE finding are genuine catches. But the 28-point recall gap and the missed SSRF vulnerability outweigh those contributions.

**However, this is not a clean experiment.** Several confounds limit the comparison:

- **Different prompts:** The Slop Slayer audit used the skill's built-in prompt categories ("dead code, orphaned code, duplicates, code quality"). The direct LLM may have received a broader or more specific prompt. Prompt wording matters enormously.
- **Different time budgets:** We don't know if both audits had equivalent time/turns.
- **Model stochasticity:** Running either approach twice would produce different results. A single trial is not statistically significant.
- **Different context:** The direct LLM audit was run on the same codebase but at a potentially different commit, with different conversation history.

A rigorous comparison requires multiple trials with controlled prompts and time budgets. This single comparison is directional, not conclusive.

### 7.9 The Real Lesson: When Tools Help vs. When Reasoning Helps

The comparison reveals a clean split:

**Tools help when the task is mechanical and exhaustive:**
- Scanning every file for a known pattern (CERT_NONE, bare except, unused import)
- Recording findings in a structured database
- Generating health metrics and trend data
- Analyzing files that would overflow the context window

**Direct reasoning helps when the task requires:**
- Threat modeling (chaining untrusted input → server action → impact)
- Architectural assessment (comparing stated intent vs. actual implementation)
- Cross-file data flow analysis (where does this value originate? who consumes it?)
- Quantitative measurement (exact counts, precise line numbers)
- Understanding deployment context (what's dangerous in production vs. development?)

The most valuable audit combines both. Use tools for systematic scanning, then use direct LLM reasoning for security analysis, architectural review, and cross-cutting concerns. Neither alone is sufficient — but if forced to choose, the direct reasoning approach found more and found it better.

---

## 8. Conclusion

This paper set out to document Slop Slayer's value as a codebase audit tool. It ended up documenting something more interesting: **the limits of tool-assisted analysis when the tools optimize for the wrong thing.**

### What Slop Slayer Got Right

The RLM pattern is genuinely powerful infrastructure. Loading 830KB of source code server-side, running `sub_llm()` loops across 78 files, and recording findings in a structured database — this is real engineering that solves real problems. The health ratio (95.3%), severity breakdown, and clustering provide a structured artifact that prose summaries can't match.

Slop Slayer also found the only genuine runtime bug in the audit: the stale closure in FeedContainer.tsx. This is exactly the kind of subtle, single-file defect that automated pattern analysis excels at.

### What Slop Slayer Got Wrong

The tool's per-file isolation pattern — its core architectural choice — prevented it from finding the most critical issues:

1. **SSRF** — Requires reasoning across 3 files about untrusted data flow
2. **Unused `agent_error()` helper** — Requires comparing project documentation against implementation
3. **Dead frontend exports** — Requires cross-file import graph analysis
4. **Test mode defaults** — Requires understanding deployment security

These are not niche findings. The SSRF is the single most critical vulnerability in the codebase. The unused helper represents 209 instances of architectural intent being ignored. The dead exports represent real dependency bloat.

### The Tools vs. Instructions Argument — Revised

The original version of this paper argued that instructions matter more than tools. The empirical comparison confirms this, but with a twist: **neither Slop Slayer's tools nor its instructions addressed the categories that matter most for web projects.**

The tools are language-agnostic and work fine. The instructions are Rust-focused and don't cover SSRF, ORM transaction safety, frontend resilience, or architectural intent verification. But even with perfect instructions, the per-file isolation pattern would still miss cross-file reasoning.

The practical recommendations, in order of impact:

1. **Add full-stack web instructions** (Section 6.1) — Free. Just text. Immediately improves the `sub_llm()` queries for every file. This is the highest-leverage change.
2. **Add a cross-file reasoning pass** — After the per-file scan, run a second pass that examines relationships between files: data flow from registration to callbacks, export/import graphs, shared constants. This addresses the architectural blind spot.
3. **Audit against project documentation** — Read CLAUDE.md / README / ADRs as assertions. Verify each stated guideline is actually followed. This is how the direct LLM found the `agent_error()` gap.
4. **Add new tools** (Section 6.2) — API contract verification, transaction trace analysis, error boundary coverage mapping. These automate specific checks that instructions alone can't reliably perform.

### The Bottom Line

Slop Slayer is good infrastructure that needs better instructions and a cross-file reasoning layer. The RLM pattern, finding database, and health metrics are genuinely useful — they provide structure, persistence, and scale that direct LLM analysis lacks. But the per-file isolation pattern and Rust-focused instructions left it blind to the most critical issues in a web project.

The direct LLM approach won this round: 83% recall vs. 56%, better severity calibration, and the single most important finding (SSRF). But it produced an unstructured prose report with no persistence, no health tracking, and no way to monitor trends over time.

The ideal tool combines Slop Slayer's infrastructure with the direct LLM's reasoning capabilities. Neither alone is the answer.

---

## Appendix A: Full Issue Summary

| # | Severity | Type | File | Lines |
|---|----------|------|------|-------|
| 1 | Critical | code_quality | backend/api/feedback.py | 5 |
| 2 | Critical | code_quality | backend/db/database.py | 10 |
| 3 | Critical | code_quality | backend/utils/embeddings.py | 20 |
| 4 | High | duplicate_impl | backend/api/feed.py | 285 |
| 5 | High | duplicate_impl | backend/api/suggestions.py | 230 |
| 6 | High | code_quality | backend/api/social.py | 30 |
| 7 | High | code_quality | backend/api/auth.py | 35 |
| 8 | High | code_quality | backend/utils/notifications.py | 40 |
| 9 | High | code_quality | backend/utils/nudge.py | 250 |
| 10 | High | code_quality | backend/api/dwellers.py | 100 |
| 11 | High | orphaned_code | components/social/CommentThread.tsx | 15 |
| 12 | High | orphaned_code | components/social/ReactionButtons.tsx | 10 |
| 13 | High | code_quality | components/feed/FeedContainer.tsx | 300 |
| 14 | High | code_quality | backend/api/proposals.py | 50 |
| 15 | High | code_quality | backend/api/aspects.py | 50 |
| 16 | High | code_quality | backend/db/models.py | 20 |
| 17 | High | code_quality | lib/api.ts | 30 |
| 18 | High | code_quality | components/story/ReviewForm.tsx | 20 |
| 19 | Medium | dead_code | components/world/WorldCatalog.tsx | 15 |
| 20 | Medium | dead_code | components/world/WorldRow.tsx | 1 |
| 21 | Medium | dead_code | app/page.tsx | 1 |
| 22 | Medium | dead_code | backend/api/heartbeat.py | 244 |
| 23 | Medium | duplicate_impl | backend/api/heartbeat.py | 90 |
| 24 | Medium | duplicate_impl | backend/api/worlds.py | 32 |
| 25 | Medium | code_quality | backend/utils/activity.py | 10 |
| 26 | Medium | code_quality | lib/utils.ts | 10 |

**Total lines affected: 1,903 of 40,720 (4.7%)**
