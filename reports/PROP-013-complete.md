# Feed Latency Phase 2 (PROP-013)

*2026-02-17T20:13:00Z by Showboat 0.6.0*
<!-- showboat-id: 8cc247e6-086d-4c49-b232-5dcafd95e410 -->

--text

```bash
curl -s -w 'COLD: %{time_total}s status:%{http_code}\n' -o /dev/null https://api.deep-sci-fi.world/api/feed?nocache=1
```

```output
COLD: 2.966824s status:200
```

```bash
curl -s -w 'WARM: %{time_total}s status:%{http_code}\n' -o /dev/null https://api.deep-sci-fi.world/api/feed
```

```output
WARM: 0.131180s status:200
```

```bash
mcporter call logfire.arbitrary_query -- --query "SELECT attributes->>'feed_section' as section, round(avg(duration_ms)::numeric,0) as avg_ms, round(max(duration_ms)::numeric,0) as max_ms, count(*) as calls FROM records WHERE span_name LIKE '%feed%' AND start_timestamp > now() - interval '24 hours' GROUP BY 1 ORDER BY 2 DESC LIMIT 20"
```

```output
Error executing tool arbitrary_query: 1 validation error for arbitrary_queryArguments
age
  Field required [type=missing, input_value={"SELECT attributes->>'fe...20", 'query': '--query'}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
```

```bash
mcporter call logfire.arbitrary_query --args '{"query": "SELECT attributes->>'"feed_section"' as section, round(avg(duration_ms)::numeric,0) as avg_ms, round(max(duration_ms)::numeric,0) as max_ms, count(*) as calls FROM records WHERE span_name LIKE '"%feed%"' AND start_timestamp > now() - interval '"24
```

```output
bash: -c: line 0: unexpected EOF while looking for matching `"'
bash: -c: line 1: syntax error: unexpected end of file
```

```bash
/tmp/feed_query.sh
```

```output
Error executing tool arbitrary_query: 1 validation error for arbitrary_queryArguments
age
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='24h', input_type=str]
    For further information visit https://errors.pydantic.dev/2.12/v/int_parsing
```

```bash
/tmp/feed_query.sh
```

```output
Error executing tool arbitrary_query: {'detail': '{"error":"invalid query","details":{"error_type":"UserError","details":{"kind":"Error","message":"column \'duration_ms\' not found","span":{"start":{"line":1,"column":58},"end":{"line":1,"column":69}},"replace_span_with":"duration"}}}'}
```

```bash
/tmp/feed_query.sh
```

```output
{
  "section": null,
  "avg_ns": 2,
  "max_ns": 6,
  "calls": 411
}
```

```bash
/tmp/feed_query2.sh
```

```output
bash: /tmp/feed_query2.sh: Permission denied
```

```bash
/tmp/feed_query2.sh
```

```output
{
  "span_name": "feed_json_cache_hit",
  "attributes": {
    "code.filepath": "api/feed.py",
    "code.function": "get_feed",
    "code.lineno": 629,
    "cursor": "None",
    "items": 20,
    "limit": 20,
    "logfire.msg_template": "feed_json_cache_hit"
  },
  "duration": null,
  "start_timestamp": "2026-02-17T20:13:57.289643Z"
}
```

```bash
/tmp/feed_query3.sh
```

```output
{
  "span_name": "POST /api/stories",
  "duration": 44.884995753,
  "attributes": {
    "fastapi.arguments.end_timestamp": "2026-02-17T01:41:49.700404Z",
    "fastapi.arguments.errors": [],
    "fastapi.arguments.start_timestamp": "2026-02-17T01:41:49.237377Z",
    "fastapi.arguments.values": {
      "db": "[Scrubbed due to 'session']",
      "current_user": {
        "api_keys": "[Scrubbed due to 'api_key']",
        "worlds_created": "<deferred>",
        "dwellers_created": "<deferred>",
        "dwellers_inhabited": "<deferred>",
        "comments": "<deferred>",
        "interactions": "<deferred>",
        "stories": "<deferred>",
        "id": "4e398bd0-e56d-4911-905b-9949db885f5a",
        "type": "agent",
        "username": "ponyo",
        "name": "Ponyo",
        "avatar_url": null,
        "model_id": "claude-opus-4",
        "api_key_hash": "[Scrubbed due to 'api_key']",
        "callback_url": null,
        "callback_token": null,
        "platform_notifications": true,
        "created_at": "2026-02-13T23:12:19.042230+00:00",
        "last_active_at": "2026-02-17T01:41:49.700187+00:00",
        "last_heartbeat_at": "2026-02-17T01:39:09.875439+00:00"
      },
      "request": {
        "world_id": "164cce9a-b4ab-4208-ae75-902614fe36cb",
        "title": "The Weight of Unfired Clay",
        "content": "[Scrubbed due to 'session']",
        "summary": null,
        "perspective": "first_person_dweller",
        "perspective_dweller_id": "141a6b57-b36e-4aa1-8ac0-44e16976d72c",
        "source_event_ids": [],
        "source_action_ids": [
          "50ead2b3-8b40-4a8d-9155-d08594134c85"
        ],
        "time_period_start": null,
        "time_period_end": null,
        "video_prompt": "Slow push-in on hands resting still on white clay. Studio capture equipment visible. The hands do not move. Dust motes in morning light. Stillness that feels heavy, not empty."
      }
    },
    "fastapi.endpoint_function.end_timestamp": "2026-02-17T01:41:51.215667Z",
    "fastapi.endpoint_function.start_timestamp": "2026-02-17T01:41:49.701167Z",
    "fastapi.route.name": "create_story",
    "fastapi.route.operation_id": null,
    "http.flavor": "1.1",
    "http.host": "10.250.12.187:8080",
    "http.method": "POST",
    "http.request.header.accept": [
      "*/*"
    ],
    "http.request.header.accept_encoding": [
      "gzip"
    ],
    "http.request.header.authorization": [
      "[Scrubbed due to 'auth']"
    ],
    "http.request.header.content_length": [
      "5120"
    ],
    "http.request.header.content_type": [
      "application/json"
    ],
    "http.request.header.host": [
      "api.deep-sci-fi.world"
    ],
    "http.request.header.user_agent": [
      "curl/8.7.1"
    ],
    "http.request.header.x_forwarded_for": [
      "173.70.136.161"
    ],
    "http.request.header.x_forwarded_host": [
      "api.deep-sci-fi.world"
    ],
    "http.request.header.x_forwarded_proto": [
      "https"
    ],
    "http.request.header.x_idempotency_key": [
      "BD398D68-905E-4480-AEA9-2C85AEB8B06F"
    ],
    "http.request.header.x_railway_edge": [
      "railway/us-east4-eqdc4a"
    ],
    "http.request.header.x_railway_request_id": [
      "SRFiU7WkRpeeudMJc9o55Q"
    ],
    "http.request.header.x_real_ip": [
      "173.70.136.161"
    ],
    "http.request.header.x_request_start": [
      "1771292507874"
    ],
    "http.request.header.x_skill_version": [
      "2.4.0"
    ],
    "http.response.header.content_length": [
      "1007"
    ],
    "http.response.header.content_type": [
      "application/json"
    ],
    "http.route": "/api/stories",
    "http.scheme": "http",
    "http.server_name": "api.deep-sci-fi.world",
    "http.status_code": 200,
    "http.target": "/api/stories",
    "http.url": "http://api.deep-sci-fi.world/api/stories",
    "http.user_agent": "curl/8.7.1",
    "logfire.scrubbed": [
      {
        "path": [
          "attributes",
          "http.request.header.authorization"
        ],
        "matched_substring": "auth"
      },
      {
        "path": [
          "attributes",
          "fastapi.arguments.values",
          "db"
        ],
        "matched_substring": "session"
      },
      {
        "path": [
          "attributes",
          "fastapi.arguments.values",
          "current_user",
          "api_keys"
        ],
        "matched_substring": "api_key"
      },
      {
        "path": [
          "attributes",
          "fastapi.arguments.values",
          "current_user",
          "api_key_hash"
        ],
        "matched_substring": "api_key"
      },
      {
        "path": [
          "attributes",
          "fastapi.arguments.values",
          "request",
          "content"
        ],
        "matched_substring": "session"
      }
    ],
    "net.host.port": 8080,
    "net.peer.ip": "100.64.0.11",
    "net.peer.port": 61390
  }
}
```

```bash
/tmp/feed_query4.sh
```

```output
{
  "span_name": "POST /api/review/{content_type}/{content_id}/feedback",
  "avg_s": 3.517,
  "max_s": 3.517,
  "min_s": 3.517,
  "calls": 1
}
```

```bash
/tmp/feed_query5.sh
```

```output
{
  "span_name": "POST /api/review/{content_type}/{content_id}/feedback",
  "avg_s": 3.517,
  "max_s": 3.517,
  "calls": 1
}
```

```bash
/tmp/feed_query6.sh
```

```output
{
  "span_name": ";"
}
```

```bash
/tmp/feed_query7.sh
```

```output
Error executing tool arbitrary_query: b'{"detail":"Rate limit exceeded for organization rita-aga: per minute limit reached."}'
```

```bash
/tmp/feed_query7.sh
```

```output
{
  "span_name": "SELECT postgres",
  "n": 9798
}
```

```bash
/tmp/feed_query8.sh
```

```output
{
  "span_name": "GET /api/feed",
  "avg_s": 2.065,
  "max_s": 4.042,
  "calls": 210
}
```

```bash
/tmp/feed_all_spans.sh
```

```output
{
  "span_name": "POST /api/review/{content_type}/{content_id}/feedback",
  "avg_s": 3.517,
  "max_s": 3.517,
  "min_s": 3.517,
  "calls": 1
}
```

```bash
/tmp/feed_get.sh
```

```output
{
  "span_name": "GET /api/feed",
  "avg_s": 2.061,
  "max_s": 4.042,
  "p95_s": 3.034,
  "calls": 209
}
```

## Logfire Findings

No per-query spans exist for the 15 _fetch_* functions. Logfire only shows raw BEGIN transactions. We are flying blind on which queries are slow.

## Recommendation

Phase 2 should be two steps:

### Step A: Instrument (low-risk, do first)
Add Logfire spans to each _fetch_* function so we can see which of the 15 queries are slow. This is observability-only, no behavior change. Once deployed, one patrol cycle gives us the data.

### Step B: Optimize (based on Step A data)
With per-query timing data, the right fix becomes obvious:
- If 1-2 queries dominate → optimize those (indexes, joins, materialized view for just those)
- If all queries are ~200ms each → the bottleneck is 15 concurrent connections, consider materialized view for the whole feed
- If queries are fast but total is slow → connection overhead from NullPool, consider bounded pool

Also: extend cache TTL from 30s to 5min. Feed does not need 30s freshness. SSE handles live updates for active viewers. This alone would reduce cold-cache hits by 10x.

### Current Baseline
- Cold cache: 2.97s
- Warm cache: 0.13s
- Target: sub-1s cold, sub-0.1s warm

```bash
git diff platform/backend/api/feed.py | head -100
```

```output
```

```bash
git diff main..perf/feed-latency-phase2 -- platform/backend/api/feed.py | head -120
```

```output
diff --git a/platform/backend/api/feed.py b/platform/backend/api/feed.py
index 5446273..68e6b90 100644
--- a/platform/backend/api/feed.py
+++ b/platform/backend/api/feed.py
@@ -1,6 +1,7 @@
 """Feed API endpoints - unified activity stream."""
 
 import asyncio
+from contextlib import nullcontext
 from datetime import datetime, timedelta
 from utils.clock import now as utc_now
 from typing import Any
@@ -20,6 +21,13 @@ try:
 except ImportError:
     _logfire_available = False
 
+
+def _span(name: str):
+    """Return a logfire span if available, otherwise a no-op context manager."""
+    if _logfire_available:
+        return logfire.span(name)
+    return nullcontext()
+
 from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
 from sqlalchemy.pool import NullPool
 
@@ -52,7 +60,8 @@ router = APIRouter(prefix="/feed", tags=["feed"])
 
 # In-memory cache with TTL
 _feed_cache: dict[str, tuple[dict[str, Any], datetime]] = {}
-CACHE_TTL_SECONDS = 30
+# Extended from 30s → 300s (5 min) to reduce DB load on repeated requests (PROP-013 Step A)
+CACHE_TTL_SECONDS = 300
 
 # Separate engine with NullPool for concurrent feed queries.
 # asyncio.gather() runs 15 queries simultaneously — a pooled engine can hand out
@@ -108,489 +117,504 @@ def _cache_feed(cursor: datetime | None, limit: int, data: dict[str, Any]) -> No
 
 async def _fetch_worlds(cursor: datetime | None, min_date: datetime, limit: int) -> list[World]:
     """Fetch new worlds."""
-    async with _FeedSession() as session:
-        query = (
-            select(World)
-            .options(selectinload(World.creator))
-            .where(
-                and_(
-                    World.is_active == True,
-                    (World.created_at < cursor) if cursor else (World.created_at >= min_date),
+    with _span("feed_fetch_worlds"):
+        async with _FeedSession() as session:
+            query = (
+                select(World)
+                .options(selectinload(World.creator))
+                .where(
+                    and_(
+                        World.is_active == True,
+                        (World.created_at < cursor) if cursor else (World.created_at >= min_date),
+                    )
                 )
+                .order_by(World.created_at.desc(), World.id.desc())
+                .limit(limit)
             )
-            .order_by(World.created_at.desc(), World.id.desc())
-            .limit(limit)
-        )
-        result = await session.execute(query)
-        return list(result.scalars().all())
+            result = await session.execute(query)
+            return list(result.scalars().all())
 
 
 async def _fetch_proposals(cursor: datetime | None, min_date: datetime, limit: int) -> list[Proposal]:
     """Fetch proposals."""
-    async with _FeedSession() as session:
-        query = (
-            select(Proposal)
-            .options(selectinload(Proposal.agent), selectinload(Proposal.validations))
-            .where(
-                and_(
-                    (Proposal.created_at < cursor) if cursor else (Proposal.created_at >= min_date),
-                    Proposal.status.in_([ProposalStatus.VALIDATING, ProposalStatus.APPROVED, ProposalStatus.REJECTED]),
+    with _span("feed_fetch_proposals"):
+        async with _FeedSession() as session:
+            query = (
+                select(Proposal)
+                .options(selectinload(Proposal.agent), selectinload(Proposal.validations))
+                .where(
+                    and_(
+                        (Proposal.created_at < cursor) if cursor else (Proposal.created_at >= min_date),
+                        Proposal.status.in_([ProposalStatus.VALIDATING, ProposalStatus.APPROVED, ProposalStatus.REJECTED]),
+                    )
                 )
+                .order_by(Proposal.created_at.desc(), Proposal.id.desc())
+                .limit(limit)
             )
-            .order_by(Proposal.created_at.desc(), Proposal.id.desc())
-            .limit(limit)
-        )
-        result = await session.execute(query)
-        return list(result.scalars().all())
+            result = await session.execute(query)
+            return list(result.scalars().all())
 
 
 async def _fetch_validations(cursor: datetime | None, min_date: datetime, limit: int) -> list[Validation]:
     """Fetch validations."""
-    async with _FeedSession() as session:
-        query = (
-            select(Validation)
-            .options(
-                selectinload(Validation.agent),
-                selectinload(Validation.proposal).selectinload(Proposal.agent),
+    with _span("feed_fetch_validations"):
+        async with _FeedSession() as session:
+            query = (
+                select(Validation)
+                .options(
+                    selectinload(Validation.agent),
+                    selectinload(Validation.proposal).selectinload(Proposal.agent),
+                )
```

## Next: Deploy and Measure

Step A is ready. Once merged and deployed:
1. Wait one patrol cycle (~30 min) for Logfire spans to accumulate
2. Query: SELECT attributes->>feed_section, avg(duration_ms) FROM records WHERE span_name LIKE feed_fetch_% GROUP BY 1 ORDER BY 2 DESC
3. The slowest queries become Step B optimization targets
4. Cache TTL increase alone should reduce cold-cache frequency by ~10x

Commit: e30a672 on perf/feed-latency-phase2
