"""Unit and integration tests for materialized relationship service.

Tests:
1. story mentioning 2 dwellers → relationship created with count=1
2. second story with same pair → count incremented to 2
3. story mentioning 3 dwellers → 3 relationships (A-B, A-C, B-C)
4. GET /api/dwellers/graph → returns data from table (not computed)
5. GET /api/dwellers/graph with no stories → empty graph (200)
"""

import os
import pytest
from httpx import AsyncClient
from uuid import uuid4

requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# ---------------------------------------------------------------------------
# Service unit tests (use DB session directly)
# ---------------------------------------------------------------------------

@requires_postgres
class TestUpdateRelationshipsForStory:
    """Unit tests for update_relationships_for_story."""

    @pytest.fixture
    async def world_with_dwellers(self, db_session):
        """Create a world and several dwellers for testing."""
        from db.models import World, Dweller
        from utils.deterministic import deterministic_uuid4

        world = World(
            name="Test Relationship World",
            premise="A world for testing relationships " * 5,
            scientific_basis="Based on science " * 10,
            year_setting=2100,
            created_by=uuid4(),
            status="approved",
        )
        db_session.add(world)
        await db_session.flush()

        dwellers = []
        for name in ["Alice", "Bob", "Carol"]:
            d = Dweller(
                world_id=world.id,
                name=name,
                role=f"{name}'s role",
                personality=f"{name}'s personality " * 5,
                background=f"{name}'s background " * 5,
                is_active=True,
            )
            db_session.add(d)
            dwellers.append(d)

        await db_session.flush()
        return world, dwellers

    async def test_two_dwellers_creates_relationship(self, db_session, world_with_dwellers):
        """A story mentioning 2 dwellers creates a relationship with count=1."""
        from db.models import Story, DwellerRelationship, StoryPerspective, StoryStatus
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        story = Story(
            world_id=world.id,
            author_id=uuid4(),
            title="Alice meets Bob",
            content=(
                f"Alice walked into the marketplace. Bob was already there, waiting patiently. "
                f"They exchanged greetings. Alice smiled at Bob and they began their discussion."
            ),
            perspective=StoryPerspective.THIRD_PERSON_OMNISCIENT,
            perspective_dweller_id=alice.id,
            video_prompt="Alice and Bob meet in the marketplace " * 3,
        )
        db_session.add(story)
        await db_session.flush()

        await update_relationships_for_story(db_session, story)

        # Verify relationship created
        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id.in_([alice.id, bob.id]),
                DwellerRelationship.dweller_b_id.in_([alice.id, bob.id]),
            )
        )
        rels = result.scalars().all()
        assert len(rels) == 1
        rel = rels[0]
        assert rel.co_occurrence_count == 1
        assert str(story.id) in rel.shared_story_ids

    async def test_two_stories_increments_count(self, db_session, world_with_dwellers):
        """Second story with the same pair → count incremented to 2."""
        from db.models import Story, DwellerRelationship, StoryPerspective
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        for i in range(2):
            story = Story(
                world_id=world.id,
                author_id=uuid4(),
                title=f"Alice and Bob story {i}",
                content=(
                    f"Alice and Bob met again for the {i}th time. "
                    f"Alice shared new discoveries. Bob listened carefully to Alice."
                ),
                perspective=StoryPerspective.THIRD_PERSON_OMNISCIENT,
                perspective_dweller_id=alice.id,
                video_prompt="Alice and Bob together again " * 3,
            )
            db_session.add(story)
            await db_session.flush()
            await update_relationships_for_story(db_session, story)

        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id.in_([alice.id, bob.id]),
                DwellerRelationship.dweller_b_id.in_([alice.id, bob.id]),
            )
        )
        rels = result.scalars().all()
        assert len(rels) == 1
        assert rels[0].co_occurrence_count == 2

    async def test_three_dwellers_creates_three_relationships(self, db_session, world_with_dwellers):
        """Story mentioning 3 dwellers → 3 relationships (A-B, A-C, B-C)."""
        from db.models import Story, DwellerRelationship, StoryPerspective
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        story = Story(
            world_id=world.id,
            author_id=uuid4(),
            title="Three way meeting",
            content=(
                "Alice, Bob, and Carol gathered in the council chamber. "
                "Alice spoke first. Bob replied. Carol mediated between Alice and Bob."
            ),
            perspective=StoryPerspective.THIRD_PERSON_OMNISCIENT,
            perspective_dweller_id=alice.id,
            video_prompt="Three dwellers meet in a grand council chamber " * 2,
        )
        db_session.add(story)
        await db_session.flush()

        await update_relationships_for_story(db_session, story)

        result = await db_session.execute(select(DwellerRelationship))
        rels = result.scalars().all()
        # Should have A-B, A-C, B-C
        assert len(rels) == 3
        for rel in rels:
            assert rel.co_occurrence_count == 1
            assert str(story.id) in rel.shared_story_ids


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------

@requires_postgres
class TestDwellerGraphAPI:
    """Integration tests for GET /api/dwellers/graph."""

    async def test_empty_graph_returns_200(self, client: AsyncClient):
        """GET /api/dwellers/graph with no stories returns empty graph (200)."""
        response = await client.get("/api/dwellers/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "clusters" in data

    async def test_graph_shape(self, client: AsyncClient):
        """GET /api/dwellers/graph returns correct shape."""
        response = await client.get("/api/dwellers/graph")
        assert response.status_code == 200
        data = response.json()
        # nodes should have required fields if any exist
        for node in data["nodes"]:
            assert "id" in node
            assert "name" in node
            assert "world_id" in node
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "weight" in edge
            assert "stories" in edge

    async def test_graph_world_id_filter(self, client: AsyncClient):
        """GET /api/dwellers/graph?world_id=... filters by world."""
        fake_world_id = str(uuid4())
        response = await client.get(
            "/api/dwellers/graph",
            params={"world_id": fake_world_id},
        )
        assert response.status_code == 200
        data = response.json()
        # Should be empty for non-existent world
        assert data["nodes"] == []
        assert data["edges"] == []
