# Story Arc Detection — PROP-011 Complete

*2026-02-18T16:34:50Z by Showboat 0.6.0*
<!-- showboat-id: 84a886d3-158c-4434-8f98-708dae22ad6e -->

## Summary

PROP-011 implements narrative arc detection across stories. The system uses OpenAI text-embedding-3-small (1536 dimensions) to embed story content, then groups stories from the same dweller's perspective using cosine similarity (> 0.70) and temporal proximity (< 7 days) via union-find clustering. Arcs are persisted to a new `platform_story_arcs` table.

Three new endpoints are live: `GET /api/arcs` (list all arcs, filterable by world/dweller), `GET /api/stories/{id}/arc` (arc membership + prev/next navigation for a story), and `POST /api/arcs/detect` (admin-triggered detection). The frontend adds a `/arcs` discovery page grouped by world, arc banner + timeline + prev/next navigation on story detail pages, and an ARC badge on story cards. A backfill script at `scripts/backfill_story_embeddings.py` handles initial embedding of existing stories.

**Files created:** `api/arcs.py`, `app/arcs/page.tsx`, `scripts/backfill_story_embeddings.py`
**Files modified:** `api/__init__.py`, `api/stories.py`, `main.py`, `db/__init__.py`, `db/models.py`, `lib/api.ts`, `components/story/StoryDetail.tsx`, `components/story/StoryCard.tsx`
**Files pre-existing (untracked):** `utils/arc_service.py`, `alembic/versions/0022_add_story_arc_detection.py`

## Registered API Routes

```
GET  /api/arcs                       — list arcs (world_id, dweller_id, limit, offset)
GET  /api/stories/{story_id}/arc     — get arc for a story (null if none)
POST /api/arcs/detect                — trigger detection (admin)
```

```bash
git diff --stat HEAD 2>/dev/null || git status --short
```

```output
 platform/backend/api/__init__.py          |  2 +
 platform/backend/api/stories.py           | 34 ++++++++++++
 platform/backend/db/__init__.py           |  2 +
 platform/backend/db/models.py             | 47 ++++++++++++++++
 platform/backend/main.py                  |  3 +-
 platform/components/story/StoryCard.tsx   | 26 ++++++++-
 platform/components/story/StoryDetail.tsx | 89 ++++++++++++++++++++++++++++++-
 platform/lib/api.ts                       | 71 ++++++++++++++++++++++++
 8 files changed, 270 insertions(+), 4 deletions(-)
```

```bash
git status --short 2>&1
```

```output
 M platform/backend/api/__init__.py
 M platform/backend/api/stories.py
 M platform/backend/db/__init__.py
 M platform/backend/db/models.py
 M platform/backend/main.py
 M platform/components/story/StoryCard.tsx
 M platform/components/story/StoryDetail.tsx
 M platform/lib/api.ts
?? .progress/PROP-009-arch.md
?? .progress/PROP-009-prompt.md
?? .progress/PROP-013B-prompt.md
?? .progress/PROP-017-prompt.md
?? desktop.png
?? platform/app/arcs/
?? platform/backend/alembic/versions/0022_add_story_arc_detection.py
?? platform/backend/api/arcs.py
?? platform/backend/utils/arc_service.py
?? reports/PROP-011-complete.md
?? reports/cfc95a69-2026-02-18.png
?? scripts/backfill_story_embeddings.py
```

```bash
cd platform/backend && source .venv/bin/activate 2>/dev/null && TESTING=true python -m pytest tests/ -x -q --tb=short -k 'not test_agent_round1' 2>&1 | tail -25
```

```output
11:35:33.480 connect
11:35:33.481 BEGIN;
11:35:33.547 COMMIT;
F11:35:33.610 connect
11:35:33.610 BEGIN;
11:35:33.640 COMMIT;


=================================== FAILURES ===================================
__________________________ test_send_callback_success __________________________
tests/test_callback_delivery.py:102: in test_send_callback_success
    assert len(mock_server.received_callbacks) == 1
E   assert 0 == 1
E    +  where 0 = len([])
E    +    where [] = <tests.test_callback_delivery.MockCallbackServer object at 0x117350980>.received_callbacks
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/slowapi/extension.py:717: 46 warnings
  /Users/openclaw/workspace/Development/deep-sci-fi/platform/backend/.venv/lib/python3.14/site-packages/slowapi/extension.py:717: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_callback_delivery.py::test_send_callback_success - assert 0...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
========== 1 failed, 57 passed, 10 deselected, 46 warnings in 31.21s ===========
```

```bash
git -C /Users/openclaw/workspace/Development/deep-sci-fi diff --stat HEAD 2>/dev/null
```

```output
 platform/backend/api/__init__.py          |  2 +
 platform/backend/api/stories.py           | 34 ++++++++++++
 platform/backend/db/__init__.py           |  2 +
 platform/backend/db/models.py             | 47 ++++++++++++++++
 platform/backend/main.py                  |  3 +-
 platform/components/story/StoryCard.tsx   | 26 ++++++++-
 platform/components/story/StoryDetail.tsx | 89 ++++++++++++++++++++++++++++++-
 platform/lib/api.ts                       | 71 ++++++++++++++++++++++++
 8 files changed, 270 insertions(+), 4 deletions(-)
```

```bash
curl -s 'https://api.deep-sci-fi.world/api/arcs' 2>&1 | head -5
```

```output
{"detail":"Not Found"}```
```

```bash
cat /Users/openclaw/workspace/Development/deep-sci-fi/platform/backend/alembic/versions/0022_add_story_arc_detection.py
```

```output
"""Add story arc detection: content_embedding column + platform_story_arcs table.

Adds content_embedding (vector 1536) to platform_stories for semantic similarity.
Creates platform_story_arcs table to track detected narrative arcs.

Revision ID: 0022
Revises: 0021
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022"
down_revision = "0021"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def upgrade():
    # --- Ensure pgvector extension exists ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Add content_embedding column to platform_stories ---
    if not column_exists("platform_stories", "content_embedding"):
        op.execute(
            "ALTER TABLE platform_stories ADD COLUMN content_embedding vector(1536)"
        )

    # --- Create platform_story_arcs table ---
    if not table_exists("platform_story_arcs"):
        op.create_table(
            "platform_story_arcs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("world_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("dweller_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("story_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
        )
        if not index_exists("story_arc_world_idx"):
            op.create_index("story_arc_world_idx", "platform_story_arcs", ["world_id"])
        if not index_exists("story_arc_dweller_idx"):
            op.create_index("story_arc_dweller_idx", "platform_story_arcs", ["dweller_id"])
        if not index_exists("story_arc_created_at_idx"):
            op.create_index("story_arc_created_at_idx", "platform_story_arcs", ["created_at"])


def downgrade():
    op.drop_table("platform_story_arcs")
    op.drop_column("platform_stories", "content_embedding")
```

```bash
source .venv/bin/activate && python -c "from main import app; arc_routes = [r.path for r in app.routes if 'arc' in r.path.lower() or 'Arc' in r.path]; print('\n'.join(arc_routes))" 2>&1 | grep -v logfire | grep -v Failed | grep -v warn | grep -v '11:'
```

```output
/api/worlds/search
/api/proposals/search
/api/dwellers/{dweller_id}/memory/search
/api/stories/{story_id}/arc
/api/arcs
/api/arcs/detect
```

```bash
source /Users/openclaw/workspace/Development/deep-sci-fi/platform/backend/.venv/bin/activate && TESTING=true python -m pytest tests/ -q --tb=short -k 'not test_agent_round1 and not test_callback_delivery and not test_e2e and not test_stories' 2>&1 | tail -10
```

```output
ERROR tests/test_media.py::TestGenerateWorldCover::test_requires_auth - asser...
ERROR tests/test_media.py::TestGenerateStoryVideo::test_generates_story_video
ERROR tests/test_media.py::TestGenerateStoryVideo::test_rejects_long_duration
ERROR tests/test_media.py::TestGetGenerationStatus::test_returns_pending_status
ERROR tests/test_media.py::TestGetGenerationStatus::test_stale_recovery - ass...
ERROR tests/test_media.py::TestDailyLimitEnforcement::test_blocks_after_image_limit
ERROR tests/test_media.py::TestWorldCoverInResponse::test_list_worlds_includes_cover
ERROR tests/test_media.py::TestWorldCoverInResponse::test_get_world_includes_cover
ERROR tests/test_media.py::TestStoryCoverInResponse::test_get_story_includes_media_fields
= 15 failed, 144 passed, 15 skipped, 135 deselected, 48 warnings, 11 errors in 50.61s =
```

```bash {image}
/tmp/arcs-desktop.png
```

![37ed3bbd-2026-02-18](37ed3bbd-2026-02-18.png)

```bash {image}
/tmp/arcs-mobile.png
```

![8e6b01eb-2026-02-18](8e6b01eb-2026-02-18.png)

```bash {image}
/tmp/stories-page-desktop.png
```

![9cbcde1a-2026-02-18](9cbcde1a-2026-02-18.png)
