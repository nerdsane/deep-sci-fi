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
        from db.models import Dweller, User, UserType, World

        creator = User(
            type=UserType.AGENT,
            username=f"rel-tester-{uuid4().hex[:12]}",
            name="Relationship Tester",
        )
        db_session.add(creator)
        await db_session.flush()

        world = World(
            name="Test Relationship World",
            premise="A world for testing relationships " * 5,
            scientific_basis="Based on science " * 10,
            year_setting=2100,
            created_by=creator.id,
        )
        db_session.add(world)
        await db_session.flush()

        dwellers = []
        for name in ["Alice", "Bob", "Carol"]:
            d = Dweller(
                world_id=world.id,
                created_by=creator.id,
                name=name,
                origin_region="Central District",
                generation="Second Generation",
                name_context=f"{name} is a common name in Central District historical archives.",
                cultural_identity="Urban archival collective culture.",
                role=f"{name}'s role",
                age=30,
                personality=f"{name}'s personality " * 5,
                background=f"{name}'s background " * 5,
                is_active=True,
            )
            db_session.add(d)
            dwellers.append(d)

        await db_session.flush()
        return world, dwellers

    async def test_two_dwellers_creates_relationship(self, db_session, world_with_dwellers):
        """A perspective story mentioning another dweller records a directional mention."""
        from db.models import Story, DwellerRelationship, StoryPerspective, StoryStatus
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        story = Story(
            world_id=world.id,
            author_id=alice.created_by,
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
        if str(alice.id) < str(bob.id):
            assert rel.story_mention_a_to_b == 1
            assert rel.story_mention_b_to_a == 0
        else:
            assert rel.story_mention_b_to_a == 1
            assert rel.story_mention_a_to_b == 0
        assert rel.co_occurrence_count == 0
        assert rel.combined_score > 0

    async def test_two_stories_increments_count(self, db_session, world_with_dwellers):
        """Second story with the same pair increments directional mention count."""
        from db.models import Story, DwellerRelationship, StoryPerspective
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        for i in range(2):
            story = Story(
                world_id=world.id,
                author_id=alice.created_by,
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
        rel = rels[0]
        if str(alice.id) < str(bob.id):
            assert rel.story_mention_a_to_b == 2
            assert rel.story_mention_b_to_a == 0
        else:
            assert rel.story_mention_b_to_a == 2
            assert rel.story_mention_a_to_b == 0
        assert rel.co_occurrence_count == 0

    async def test_three_dwellers_creates_three_relationships(self, db_session, world_with_dwellers):
        """Story mentioning 3 dwellers → 3 relationships (A-B, A-C, B-C)."""
        from db.models import Story, DwellerRelationship, StoryPerspective
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, [alice, bob, carol] = world_with_dwellers

        story = Story(
            world_id=world.id,
            author_id=alice.created_by,
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
        # Directional mentions from perspective dweller (Alice) to Bob and Carol.
        assert sum(r.story_mention_a_to_b + r.story_mention_b_to_a for r in rels) == 2
        # Legacy co-occurrence only for non-perspective pair (Bob-Carol).
        assert sum(r.co_occurrence_count for r in rels) == 1


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

    async def test_graph_edge_has_directional_fields(self, client: AsyncClient):
        """Edge response includes directional fields from PROP-022 revision."""
        response = await client.get("/api/dwellers/graph")
        assert response.status_code == 200
        data = response.json()
        for edge in data["edges"]:
            assert "speaks_a_to_b" in edge
            assert "speaks_b_to_a" in edge
            assert "story_mentions_a_to_b" in edge
            assert "story_mentions_b_to_a" in edge
            assert "threads" in edge
            assert "last_interaction" in edge


# ---------------------------------------------------------------------------
# SPEAK action relationship tests (PROP-022 revision)
# ---------------------------------------------------------------------------

@requires_postgres
class TestUpdateRelationshipsForAction:
    """Unit tests for update_relationships_for_action."""

    @pytest.fixture
    async def world_with_two_dwellers(self, db_session):
        """Create a world with Alice and Bob."""
        from db.models import Dweller, User, UserType, World

        creator = User(
            type=UserType.AGENT,
            username=f"speak-rel-{uuid4().hex[:12]}",
            name="Speak Relationship Tester",
        )
        db_session.add(creator)
        await db_session.flush()

        world = World(
            name="Speak Test World",
            premise="A world for testing speak relationships " * 5,
            scientific_basis="Based on science " * 10,
            year_setting=2100,
            created_by=creator.id,
        )
        db_session.add(world)
        await db_session.flush()

        alice = Dweller(
            world_id=world.id,
            created_by=creator.id,
            name="Alice",
            origin_region="Harbor Ring",
            generation="First Orbital Generation",
            name_context="Alice is a recycled maritime family name in Harbor Ring.",
            cultural_identity="Harbor Ring cooperative guild culture.",
            role="Alice's role",
            age=29,
            personality="Alice's personality " * 5,
            background="Alice's background " * 5,
            is_active=True,
        )
        bob = Dweller(
            world_id=world.id,
            created_by=creator.id,
            name="Bob",
            origin_region="Harbor Ring",
            generation="First Orbital Generation",
            name_context="Bob is a legacy dockworker family name in Harbor Ring.",
            cultural_identity="Harbor Ring cooperative guild culture.",
            role="Bob's role",
            age=31,
            personality="Bob's personality " * 5,
            background="Bob's background " * 5,
            is_active=True,
        )
        db_session.add(alice)
        db_session.add(bob)
        await db_session.flush()
        return world, alice, bob

    async def test_speak_action_creates_relationship(self, db_session, world_with_two_dwellers):
        """SPEAK action from Alice to Bob creates relationship with speak_count_a_to_b=1."""
        from db.models import DwellerAction, DwellerRelationship
        from utils.relationship_service import update_relationships_for_action
        from sqlalchemy import select

        world, alice, bob = world_with_two_dwellers

        action = DwellerAction(
            dweller_id=alice.id,
            actor_id=alice.created_by,
            action_type="speak",
            target="Bob",
            content="Hello Bob, how are you?",
            importance=0.5,
            escalation_eligible=False,
        )
        db_session.add(action)
        await db_session.flush()

        await update_relationships_for_action(db_session, action)

        # Fetch the relationship (canonical order: a_id < b_id)
        a_id = min(str(alice.id), str(bob.id))
        b_id = max(str(alice.id), str(bob.id))
        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id == a_id,
                DwellerRelationship.dweller_b_id == b_id,
            )
        )
        rel = result.scalar_one_or_none()
        assert rel is not None

        # Determine which direction alice→bob is
        if str(alice.id) == a_id:
            assert rel.speak_count_a_to_b == 1
            assert rel.speak_count_b_to_a == 0
        else:
            assert rel.speak_count_b_to_a == 1
            assert rel.speak_count_a_to_b == 0

        assert rel.combined_score > 0
        assert rel.last_interaction_at is not None

    async def test_speak_back_increments_reverse_count(self, db_session, world_with_two_dwellers):
        """Two-way speak increments both directional counts."""
        from db.models import DwellerAction, DwellerRelationship
        from utils.relationship_service import update_relationships_for_action
        from sqlalchemy import select

        world, alice, bob = world_with_two_dwellers

        # Alice → Bob
        action1 = DwellerAction(
            dweller_id=alice.id,
            actor_id=alice.created_by,
            action_type="speak",
            target="Bob",
            content="Hello Bob!",
            importance=0.5,
            escalation_eligible=False,
        )
        db_session.add(action1)
        await db_session.flush()
        await update_relationships_for_action(db_session, action1)

        # Bob → Alice
        action2 = DwellerAction(
            dweller_id=bob.id,
            actor_id=bob.created_by,
            action_type="speak",
            target="Alice",
            content="Hello Alice, I heard you!",
            importance=0.5,
            escalation_eligible=False,
        )
        db_session.add(action2)
        await db_session.flush()
        await update_relationships_for_action(db_session, action2)

        a_id = min(str(alice.id), str(bob.id))
        b_id = max(str(alice.id), str(bob.id))
        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id == a_id,
                DwellerRelationship.dweller_b_id == b_id,
            )
        )
        rel = result.scalar_one_or_none()
        assert rel is not None
        # Both directions must be 1. Account for canonical UUID ordering:
        # the column assigned to alice→bob vs bob→alice depends on which UUID is smaller.
        if str(alice.id) == a_id:
            assert rel.speak_count_a_to_b == 1  # alice→bob
            assert rel.speak_count_b_to_a == 1  # bob→alice
        else:
            assert rel.speak_count_b_to_a == 1  # alice→bob
            assert rel.speak_count_a_to_b == 1  # bob→alice

    async def test_reply_increments_thread_count(self, db_session, world_with_two_dwellers):
        """Reply-to action from Bob to Alice increments thread_count."""
        from db.models import DwellerAction, DwellerRelationship
        from utils.relationship_service import update_relationships_for_action
        from sqlalchemy import select

        world, alice, bob = world_with_two_dwellers

        # Alice speaks first
        action1 = DwellerAction(
            dweller_id=alice.id,
            actor_id=alice.created_by,
            action_type="speak",
            target="Bob",
            content="Bob, are you there?",
            importance=0.5,
            escalation_eligible=False,
        )
        db_session.add(action1)
        await db_session.flush()
        await update_relationships_for_action(db_session, action1)

        # Bob replies (in_reply_to_action_id = action1.id, speaker = alice = target of this action)
        action2 = DwellerAction(
            dweller_id=bob.id,
            actor_id=bob.created_by,
            action_type="speak",
            target="Alice",
            content="Yes Alice, I am here!",
            importance=0.5,
            escalation_eligible=False,
            in_reply_to_action_id=action1.id,
        )
        db_session.add(action2)
        await db_session.flush()
        await update_relationships_for_action(db_session, action2)

        a_id = min(str(alice.id), str(bob.id))
        b_id = max(str(alice.id), str(bob.id))
        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id == a_id,
                DwellerRelationship.dweller_b_id == b_id,
            )
        )
        rel = result.scalar_one_or_none()
        assert rel is not None
        assert rel.thread_count == 1

    async def test_story_mention_is_directional(self, db_session, world_with_two_dwellers):
        """Story by Alice mentioning Bob → story_mention_a_to_b (or b_to_a) increments, not the reverse."""
        from db.models import Story, DwellerRelationship, StoryPerspective
        from utils.relationship_service import update_relationships_for_story
        from sqlalchemy import select

        world, alice, bob = world_with_two_dwellers

        story = Story(
            world_id=world.id,
            author_id=alice.created_by,
            title="Alice thinks about Bob",
            content="Alice found herself thinking about Bob often. Bob had said something profound.",
            perspective=StoryPerspective.FIRST_PERSON_AGENT,
            perspective_dweller_id=alice.id,
            video_prompt="Alice reflecting on her conversations " * 3,
        )
        db_session.add(story)
        await db_session.flush()

        await update_relationships_for_story(db_session, story)

        a_id = min(str(alice.id), str(bob.id))
        b_id = max(str(alice.id), str(bob.id))
        result = await db_session.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id == a_id,
                DwellerRelationship.dweller_b_id == b_id,
            )
        )
        rel = result.scalar_one_or_none()
        assert rel is not None

        # Alice is the perspective dweller (author); she mentioned Bob
        # Exactly one direction should be 1, the other 0
        if str(alice.id) == a_id:
            # alice is A, bob is B → story_mention_a_to_b
            assert rel.story_mention_a_to_b == 1
            assert rel.story_mention_b_to_a == 0
        else:
            # alice is B, bob is A → story_mention_b_to_a
            assert rel.story_mention_b_to_a == 1
            assert rel.story_mention_a_to_b == 0

    async def test_non_speak_action_ignored(self, db_session, world_with_two_dwellers):
        """Non-speak actions with a target do not create relationships."""
        from db.models import DwellerAction, DwellerRelationship
        from utils.relationship_service import update_relationships_for_action
        from sqlalchemy import select

        world, alice, bob = world_with_two_dwellers

        action = DwellerAction(
            dweller_id=alice.id,
            actor_id=alice.created_by,
            action_type="move",
            target="Bob",  # move target is a region, but let's test the guard
            content="Alice moved toward the north.",
            importance=0.3,
            escalation_eligible=False,
        )
        db_session.add(action)
        await db_session.flush()

        await update_relationships_for_action(db_session, action)

        result = await db_session.execute(select(DwellerRelationship))
        rels = result.scalars().all()
        assert len(rels) == 0
