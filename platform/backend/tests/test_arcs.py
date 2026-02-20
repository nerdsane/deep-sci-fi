"""Unit tests for materialized arc service.

Tests:
1. First story → new arc created
2. Similar story (cosine > 0.75) → added to existing arc
3. Dissimilar story → new arc created
4. NO time-window dependency
5. GET /api/arcs → returns data from table (not computed)
"""

import os
import pytest
from uuid import uuid4

requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# ---------------------------------------------------------------------------
# Helper: build a unit vector with controlled direction
# ---------------------------------------------------------------------------

def _make_embedding(dim: int = 1536, hot_indices: list[int] | None = None) -> list[float]:
    """Return a unit embedding vector with ones at hot_indices, zeros elsewhere."""
    emb = [0.0] * dim
    if hot_indices:
        for idx in hot_indices:
            emb[idx % dim] = 1.0
    # Normalise
    norm = sum(x * x for x in emb) ** 0.5
    if norm == 0:
        emb[0] = 1.0
        norm = 1.0
    return [x / norm for x in emb]


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------

@requires_postgres
class TestAssignStoryToArc:
    """Unit tests for assign_story_to_arc."""

    @pytest.fixture
    async def world_and_dweller(self, db_session):
        """Create a world and a dweller for arc testing."""
        from db.models import World, Dweller

        world = World(
            name="Arc Test World",
            premise="A world where stories form arcs " * 5,
            scientific_basis="Narrative science " * 10,
            year_setting=2150,
            created_by=uuid4(),
        )
        db_session.add(world)
        await db_session.flush()

        dweller = Dweller(
            world_id=world.id,
            name="Arc Dweller",
            role="Protagonist",
            personality="Thoughtful and curious " * 5,
            background="Lives in the arc test world " * 5,
            is_active=True,
        )
        db_session.add(dweller)
        await db_session.flush()
        return world, dweller

    async def _make_story(self, db_session, world, dweller, title: str, content: str, embedding: list[float]) -> object:
        """Create a Story row with a pre-set embedding (bypasses OpenAI call)."""
        from db.models import Story, StoryPerspective
        from sqlalchemy import text

        story = Story(
            world_id=world.id,
            author_id=uuid4(),
            title=title,
            content=content,
            perspective=StoryPerspective.FIRST_PERSON_DWELLER,
            perspective_dweller_id=dweller.id,
            video_prompt=f"Cinematic scene: {title}. Sweeping vistas and dramatic lighting." * 2,
        )
        db_session.add(story)
        await db_session.flush()

        # Inject pre-computed embedding directly so tests don't call OpenAI
        await db_session.execute(
            text(
                "UPDATE platform_stories SET content_embedding = CAST(:emb AS vector) "
                "WHERE id = :sid"
            ),
            {"emb": str(embedding), "sid": str(story.id)},
        )
        await db_session.flush()
        return story

    async def test_first_story_creates_arc(self, db_session, world_and_dweller):
        """First story for a dweller → a new arc is created."""
        from db.models import StoryArc
        from utils.arc_service import assign_story_to_arc
        from sqlalchemy import select

        world, dweller = world_and_dweller
        emb = _make_embedding(hot_indices=[0, 1, 2])
        story = await self._make_story(
            db_session, world, dweller,
            title="The Beginning",
            content="I began my journey through the arc test world " * 5,
            embedding=emb,
        )

        await assign_story_to_arc(db_session, story)

        result = await db_session.execute(
            select(StoryArc).where(StoryArc.dweller_id == dweller.id)
        )
        arcs = result.scalars().all()
        assert len(arcs) == 1
        assert str(story.id) in arcs[0].story_ids

    async def test_similar_story_joins_existing_arc(self, db_session, world_and_dweller):
        """A similar story (cosine > 0.75) is added to the existing arc."""
        from db.models import StoryArc
        from utils.arc_service import assign_story_to_arc
        from sqlalchemy import select

        world, dweller = world_and_dweller
        # Two stories with very similar embeddings (same hot indices)
        emb1 = _make_embedding(hot_indices=[10, 11, 12])
        emb2 = _make_embedding(hot_indices=[10, 11, 12, 13])  # very similar

        story1 = await self._make_story(
            db_session, world, dweller,
            title="Chapter One",
            content="I explored the depths of the world in chapter one " * 5,
            embedding=emb1,
        )
        await assign_story_to_arc(db_session, story1)

        story2 = await self._make_story(
            db_session, world, dweller,
            title="Chapter Two",
            content="I continued my exploration in the second chapter " * 5,
            embedding=emb2,
        )
        await assign_story_to_arc(db_session, story2)

        result = await db_session.execute(
            select(StoryArc).where(StoryArc.dweller_id == dweller.id)
        )
        arcs = result.scalars().all()
        # Both stories in the same arc
        assert len(arcs) == 1
        assert str(story1.id) in arcs[0].story_ids
        assert str(story2.id) in arcs[0].story_ids

    async def test_dissimilar_story_creates_new_arc(self, db_session, world_and_dweller):
        """A dissimilar story creates a new arc (not joined to existing)."""
        from db.models import StoryArc
        from utils.arc_service import assign_story_to_arc
        from sqlalchemy import select

        world, dweller = world_and_dweller
        # Two stories with orthogonal embeddings (cosine similarity = 0)
        emb1 = _make_embedding(hot_indices=[0])
        emb2 = _make_embedding(hot_indices=[768])  # orthogonal

        story1 = await self._make_story(
            db_session, world, dweller,
            title="Topic Alpha",
            content="I investigated alpha phenomena exclusively in topic alpha " * 5,
            embedding=emb1,
        )
        await assign_story_to_arc(db_session, story1)

        story2 = await self._make_story(
            db_session, world, dweller,
            title="Topic Beta",
            content="I investigated beta phenomena exclusively in topic beta " * 5,
            embedding=emb2,
        )
        await assign_story_to_arc(db_session, story2)

        result = await db_session.execute(
            select(StoryArc).where(StoryArc.dweller_id == dweller.id)
        )
        arcs = result.scalars().all()
        # Should have 2 separate arcs
        assert len(arcs) == 2

    async def test_no_time_window(self, db_session, world_and_dweller):
        """Arc assignment is purely semantic — no time window applies."""
        from db.models import StoryArc
        from utils.arc_service import assign_story_to_arc
        from sqlalchemy import select, text
        from datetime import datetime, timezone, timedelta

        world, dweller = world_and_dweller
        emb = _make_embedding(hot_indices=[100, 101, 102])

        story1 = await self._make_story(
            db_session, world, dweller,
            title="Old Chapter",
            content="I began this narrative long ago in the old chapter " * 5,
            embedding=emb,
        )
        # Backdate story1 by 30 days (far outside any legacy 7-day window)
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        await db_session.execute(
            text("UPDATE platform_stories SET created_at = :dt WHERE id = :sid"),
            {"dt": old_date, "sid": str(story1.id)},
        )
        await db_session.flush()
        await assign_story_to_arc(db_session, story1)

        story2 = await self._make_story(
            db_session, world, dweller,
            title="New Chapter",
            content="I continued the narrative now in the new chapter " * 5,
            embedding=emb,  # Same embedding → should join
        )
        await assign_story_to_arc(db_session, story2)

        result = await db_session.execute(
            select(StoryArc).where(StoryArc.dweller_id == dweller.id)
        )
        arcs = result.scalars().all()
        # Should be 1 arc — time gap doesn't matter
        assert len(arcs) == 1
        arc = arcs[0]
        assert str(story1.id) in arc.story_ids
        assert str(story2.id) in arc.story_ids


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

@requires_postgres
class TestArcsAPI:
    """Integration tests for GET /api/arcs."""

    async def test_list_arcs_returns_200(self, client):
        """GET /api/arcs returns 200."""
        response = await client.get("/api/arcs")
        assert response.status_code == 200
        data = response.json()
        assert "arcs" in data
        assert "count" in data
        assert isinstance(data["arcs"], list)

    async def test_list_arcs_filter_by_invalid_world(self, client):
        """GET /api/arcs with invalid world_id returns 400."""
        response = await client.get("/api/arcs", params={"world_id": "not-a-uuid"})
        assert response.status_code == 400

    async def test_list_arcs_filter_by_nonexistent_world(self, client):
        """GET /api/arcs with valid but nonexistent world_id returns empty list."""
        response = await client.get("/api/arcs", params={"world_id": str(uuid4())})
        assert response.status_code == 200
        data = response.json()
        assert data["arcs"] == []
        assert data["count"] == 0
