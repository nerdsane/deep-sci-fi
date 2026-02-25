"""Tests for the two-phase action flow (context → act) and conversation threading.

Tests:
1. POST /act without context_token → 400
2. POST /act/context returns a context_token
3. Replaced context token → 400
4. B speaks to A, A speaks to B without in_reply_to → 202 + warning (grace window)
5. B speaks to A, A replies with in_reply_to → 200
6. Context endpoint returns threaded conversations
7. Context endpoint returns open_threads + reply-required constraints
8. High-importance unresolved actions surface in open_threads
"""

import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db import DwellerAction
from tests.conftest import (
    SAMPLE_CAUSAL_CHAIN,
    SAMPLE_DWELLER,
    SAMPLE_REGION,
    approve_proposal,
    get_context_token,
    act_with_context,
)
from utils.clock import now as utc_now


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)",
)


@requires_postgres
class TestTwoPhaseAction:
    """Tests for the two-phase action flow."""

    @pytest.fixture
    async def two_dwellers(self, client: AsyncClient) -> dict:
        """Create a world with two dwellers claimed by different agents."""
        # Register agent A
        resp = await client.post(
            "/api/auth/agent",
            json={"name": "Agent A", "username": f"two-phase-agent-a-{uuid4().hex[:8]}"},
        )
        agent_a = resp.json()
        key_a = agent_a["api_key"]["key"]

        # Register agent B
        resp = await client.post(
            "/api/auth/agent",
            json={"name": "Agent B", "username": f"two-phase-agent-b-{uuid4().hex[:8]}"},
        )
        agent_b = resp.json()
        key_b = agent_b["api_key"]["key"]

        # Create and approve a proposal → world
        resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": key_a},
            json={
                "name": "Two-Phase World",
                "premise": "A world for testing the two-phase action flow with conversations",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current fusion research progress from ITER and private companies. "
                    "Cost curves follow historical patterns of energy technology deployment."
                ),
            "image_prompt": (
                "Cinematic wide shot of a futuristic test facility at golden hour. "
                "Advanced technological infrastructure with dramatic lighting. "
                "Photorealistic, sense of scale and scientific wonder."
            ),
            },
        )
        assert resp.status_code == 200, f"Proposal creation failed: {resp.json()}"
        proposal_id = resp.json()["id"]
        result = await approve_proposal(client, proposal_id, key_a)
        world_id = result.get("world_created", {}).get("id")
        assert world_id, f"No world_id in approval result: {result}"

        # Add region
        resp = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": key_a},
            json=SAMPLE_REGION,
        )
        assert resp.status_code == 200, f"Region creation failed: {resp.json()}"

        # Create dweller A
        resp = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": key_a},
            json={
                **SAMPLE_DWELLER,
                "name": "Edmund Whitestone",
                "name_context": (
                    "Edmund is a traditional name preserved by first-generation settlers; "
                    "Whitestone references the limestone cliffs of this region's early settlements."
                ),
            },
        )
        assert resp.status_code == 200, f"Dweller A creation failed: {resp.json()}"
        dweller_a_id = resp.json()["dweller"]["id"]

        # Claim dweller A
        resp = await client.post(
            f"/api/dwellers/{dweller_a_id}/claim",
            headers={"X-API-Key": key_a},
        )
        assert resp.status_code == 200, f"Claim A failed: {resp.json()}"

        # Create dweller B
        resp = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": key_b},
            json={
                **SAMPLE_DWELLER,
                "name": "Margaret Haldane",
                "name_context": (
                    "Margaret is a heritage name common among first-generation settler families; "
                    "Haldane derives from the old Scottish surname adapted by early colonists."
                ),
            },
        )
        assert resp.status_code == 200, f"Dweller B creation failed: {resp.json()}"
        dweller_b_id = resp.json()["dweller"]["id"]

        # Claim dweller B
        resp = await client.post(
            f"/api/dwellers/{dweller_b_id}/claim",
            headers={"X-API-Key": key_b},
        )
        assert resp.status_code == 200, f"Claim B failed: {resp.json()}"

        return {
            "world_id": world_id,
            "key_a": key_a,
            "key_b": key_b,
            "dweller_a_id": dweller_a_id,
            "dweller_b_id": dweller_b_id,
            "dweller_a_name": "Edmund Whitestone",
            "dweller_b_name": "Margaret Haldane",
        }

    # ==========================================================================
    # Context token tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_act_requires_context_token(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """POST /act without context_token → 400."""
        resp = await client.post(
            f"/api/dwellers/{two_dwellers['dweller_a_id']}/act",
            headers={"X-API-Key": two_dwellers["key_a"]},
            json={
                "context_token": str(uuid4()),  # random invalid token
                "action_type": "speak",
                "content": "Hello, world!",
                "importance": 0.3,
            },
        )
        assert resp.status_code == 400
        assert "context" in resp.json()["detail"]["error"].lower()

    @pytest.mark.asyncio
    async def test_act_context_returns_token(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """POST /act/context → response has context_token."""
        resp = await client.post(
            f"/api/dwellers/{two_dwellers['dweller_a_id']}/act/context",
            headers={"X-API-Key": two_dwellers["key_a"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "context_token" in data
        # Token should be a valid UUID string
        token = data["context_token"]
        assert len(token) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_replaced_context_token_rejected(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """Replaced context token (new token invalidates old) → 400 on /act."""
        # Get a valid token first
        token = await get_context_token(
            client, two_dwellers["dweller_a_id"], two_dwellers["key_a"]
        )

        # Manually expire the token by patching last_context_at
        # We'll use the admin key to directly modify the database via the API
        # Instead, we'll just verify the mechanism exists by:
        # 1. Getting a token
        # 2. Getting a NEW token (invalidating the old one since last_context_token changes)
        # 3. Trying to use the old token
        new_token = await get_context_token(
            client, two_dwellers["dweller_a_id"], two_dwellers["key_a"]
        )
        assert token != new_token

        # Old token should be rejected (token mismatch, not expiry per se,
        # but same error path)
        resp = await client.post(
            f"/api/dwellers/{two_dwellers['dweller_a_id']}/act",
            headers={"X-API-Key": two_dwellers["key_a"]},
            json={
                "context_token": token,
                "action_type": "observe",
                "content": "Looking around at the test world with curiosity.",
                "importance": 0.2,
            },
        )
        assert resp.status_code == 400

    # ==========================================================================
    # Conversation threading tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_speak_requires_reply_to(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """B speaks to A, A speaks to B without in_reply_to → 202 warning."""
        d = two_dwellers

        # B speaks to A
        resp = await act_with_context(
            client, d["dweller_b_id"], d["key_b"],
            action_type="speak",
            content="Hello Dweller Alpha, how are you doing today?",
            target=d["dweller_a_name"],
        )
        assert resp.status_code == 200, f"B speak to A failed: {resp.json()}"

        # A speaks without in_reply_to during grace period.
        resp = await act_with_context(
            client, d["dweller_a_id"], d["key_a"],
            action_type="speak",
            content="Hey Beta, I wanted to tell you something new.",
            target=d["dweller_b_name"],
        )
        assert resp.status_code == 202, (
            f"Expected 202 reply_pending warning, got {resp.status_code}: {resp.json()}"
        )
        data = resp.json()
        assert "warnings" in data
        assert data["warnings"][0]["type"] == "reply_pending"
        assert data["warnings"][0]["partner"] == d["dweller_b_name"]

    @pytest.mark.asyncio
    async def test_speak_without_reply_hard_blocks_after_grace(
        self, client: AsyncClient, db_session: AsyncSession, two_dwellers: dict
    ) -> None:
        """Unanswered speak older than grace window hard-blocks with 403."""
        d = two_dwellers

        # B speaks to A
        resp = await act_with_context(
            client, d["dweller_b_id"], d["key_b"],
            action_type="speak",
            content="Alpha, please reply when you can.",
            target=d["dweller_a_name"],
        )
        assert resp.status_code == 200, f"B speak to A failed: {resp.json()}"
        b_action_id = UUID(resp.json()["action"]["id"])

        # Age the unanswered message past grace (48h).
        action = await db_session.get(DwellerAction, b_action_id)
        assert action is not None
        action.created_at = utc_now() - timedelta(hours=49)
        await db_session.commit()

        # A speaks without in_reply_to → should now hard-block.
        resp = await act_with_context(
            client, d["dweller_a_id"], d["key_a"],
            action_type="speak",
            content="I am skipping the reply despite overdue thread.",
            target=d["dweller_b_name"],
        )
        assert resp.status_code == 403, resp.json()
        detail = resp.json()["detail"]
        assert detail["context"]["grace_period_hours"] == 48.0
        assert detail["context"]["unanswered_since_hours"] >= 49.0

    @pytest.mark.asyncio
    async def test_speak_with_reply_to_succeeds(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """B speaks to A, A replies with in_reply_to → 200."""
        d = two_dwellers

        # B speaks to A
        resp = await act_with_context(
            client, d["dweller_b_id"], d["key_b"],
            action_type="speak",
            content="Greetings Dweller Alpha, I have news about the fusion grid.",
            target=d["dweller_a_name"],
        )
        assert resp.status_code == 200, f"B speak to A failed: {resp.json()}"
        b_action_id = resp.json()["action"]["id"]

        # A replies with in_reply_to → should succeed
        resp = await act_with_context(
            client, d["dweller_a_id"], d["key_a"],
            action_type="speak",
            content="Thank you Beta, tell me more about what happened.",
            target=d["dweller_b_name"],
            in_reply_to_action_id=b_action_id,
        )
        assert resp.status_code == 200, (
            f"Reply with in_reply_to failed: {resp.json()}"
        )

    @pytest.mark.asyncio
    async def test_context_returns_threaded_conversations(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """Context endpoint returns grouped conversation threads."""
        d = two_dwellers

        # B speaks to A
        resp = await act_with_context(
            client, d["dweller_b_id"], d["key_b"],
            action_type="speak",
            content="Alpha, the grid synchronization tests were successful today.",
            target=d["dweller_a_name"],
        )
        assert resp.status_code == 200

        # Get context for A — should show the conversation
        resp = await client.post(
            f"/api/dwellers/{d['dweller_a_id']}/act/context",
            headers={"X-API-Key": d["key_a"]},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Should have conversations
        assert "conversations" in data
        assert "open_threads" in data
        conversations = data["conversations"]
        assert len(conversations) >= 1

        # Find conversation with B
        b_conv = next(
            (c for c in conversations if c.get("with_dweller") == d["dweller_b_name"]),
            None,
        )
        assert b_conv is not None, (
            f"No conversation with {d['dweller_b_name']} found in: {conversations}"
        )
        assert len(b_conv.get("thread", [])) >= 1
        assert b_conv.get("your_turn") is True

        open_threads = data["open_threads"]
        assert len(open_threads) >= 1
        b_open_thread = next(
            (t for t in open_threads if t.get("partner") == d["dweller_b_name"]),
            None,
        )
        assert b_open_thread is not None
        assert b_open_thread["urgency"] == "high"

    @pytest.mark.asyncio
    async def test_context_surfaces_open_threads_and_reply_constraints(
        self, client: AsyncClient, db_session, two_dwellers: dict
    ) -> None:
        """Overdue unanswered speaks become open_threads + reply_required constraints."""
        d = two_dwellers

        # B speaks to A.
        resp = await act_with_context(
            client, d["dweller_b_id"], d["key_b"],
            action_type="speak",
            content="Alpha, this challenge cannot wait. I need your answer.",
            target=d["dweller_a_name"],
        )
        assert resp.status_code == 200, f"B speak to A failed: {resp.json()}"
        b_action_id = resp.json()["action"]["id"]

        # Backdate to exceed default 12h grace period.
        await db_session.execute(
            sa.text(
                "UPDATE platform_dweller_actions "
                "SET created_at = NOW() - interval '13 hours' "
                "WHERE id = :action_id"
            ),
            {"action_id": b_action_id},
        )
        await db_session.commit()

        # A gets context.
        resp = await client.post(
            f"/api/dwellers/{d['dweller_a_id']}/act/context",
            headers={"X-API-Key": d["key_a"]},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert "open_threads" in data
        assert "constraints" in data
        assert isinstance(data["open_threads"], list)
        assert isinstance(data["constraints"], list)
        assert data["open_threads"], "Expected at least one open thread for unanswered speak."

        first_keys = list(data.keys())
        assert first_keys.index("open_threads") < first_keys.index("memory")

        thread = next(
            (
                t for t in data["open_threads"]
                if t.get("arc_type") == "speak_chain"
                and t.get("partner") == d["dweller_b_name"]
                and t.get("is_awaiting_your_response") is True
            ),
            None,
        )
        assert thread is not None, f"Expected speak_chain thread in open_threads: {data['open_threads']}"
        assert float(thread.get("open_for_hours", 0)) >= 12

        constraint = next(
            (
                c for c in data["constraints"]
                if c.get("type") == "reply_required"
                and c.get("partner") == d["dweller_b_name"]
            ),
            None,
        )
        assert constraint is not None, f"Expected reply_required constraint: {data['constraints']}"
        assert constraint.get("urgency") == "high"

    @pytest.mark.asyncio
    async def test_context_surfaces_high_importance_unresolved_thread(
        self, client: AsyncClient, two_dwellers: dict
    ) -> None:
        """A recent high-importance action with no follow-up appears as open thread."""
        d = two_dwellers

        # A makes high-importance decision and takes no execution action after it.
        resp = await act_with_context(
            client, d["dweller_a_id"], d["key_a"],
            action_type="decide",
            content="I decide to confront the council about the rationing fraud.",
            importance=0.95,
        )
        assert resp.status_code == 200, f"High-importance decide failed: {resp.json()}"

        resp = await client.post(
            f"/api/dwellers/{d['dweller_a_id']}/act/context",
            headers={"X-API-Key": d["key_a"]},
        )
        assert resp.status_code == 200
        data = resp.json()

        high_arc = next(
            (t for t in data.get("open_threads", []) if t.get("arc_type") == "high_importance_unresolved"),
            None,
        )
        assert high_arc is not None, f"Expected high_importance_unresolved arc: {data.get('open_threads', [])}"
        assert high_arc.get("urgency") in {"high", "medium"}
