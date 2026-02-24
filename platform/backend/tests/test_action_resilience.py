"""Tests for PROP-043 Phase 1 action resilience."""

import os
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import ActionCompositionQueue, DwellerAction
from services.action_queue_worker import process_action_queue_once
from tests.conftest import (
    SAMPLE_CAUSAL_CHAIN,
    SAMPLE_DWELLER,
    SAMPLE_REGION,
    approve_proposal,
)
from utils.clock import now as utc_now


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)",
)


@pytest.fixture
async def action_setup(client: AsyncClient) -> dict[str, str]:
    """Create an agent with one claimed dweller ready for action tests."""
    # Register agent.
    resp = await client.post(
        "/api/auth/agent",
        json={"name": "Action Agent", "username": f"action-agent-{uuid4().hex[:8]}"},
    )
    assert resp.status_code == 200
    api_key = resp.json()["api_key"]["key"]

    # Create + approve world.
    resp = await client.post(
        "/api/proposals",
        headers={"X-API-Key": api_key},
        json={
            "name": "Action Resilience World",
            "premise": "A world used to test resilient action submission during deployment gaps.",
            "year_setting": 2091,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": (
                "ITER and private fusion programs reached sustained net-positive output, "
                "enabling cheap base-load power and large-scale post-carbon urban redesign."
            ),
            "image_prompt": (
                "Cinematic resilient city with autonomous infrastructure and layered transit systems."
            ),
        },
    )
    assert resp.status_code == 200, resp.json()
    proposal_id = resp.json()["id"]
    approval = await approve_proposal(client, proposal_id, api_key)
    world_id = approval["world_created"]["id"]

    # Region + dweller.
    region_resp = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": api_key},
        json=SAMPLE_REGION,
    )
    assert region_resp.status_code == 200, region_resp.json()

    dweller_resp = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": api_key},
        json={
            **SAMPLE_DWELLER,
            "name": "Pallas Trine",
            "name_context": (
                "Pallas is a revived old-world given name common in this district; "
                "Trine reflects post-fusion family naming conventions tied to triad cooperatives."
            ),
        },
    )
    assert dweller_resp.status_code == 200, dweller_resp.json()
    dweller_id = dweller_resp.json()["dweller"]["id"]

    claim_resp = await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": api_key},
    )
    assert claim_resp.status_code == 200, claim_resp.json()

    return {"api_key": api_key, "dweller_id": dweller_id}


@requires_postgres
@pytest.mark.asyncio
async def test_compose_action_buffers_queue_item(
    client: AsyncClient,
    db_session: AsyncSession,
    action_setup: dict[str, str],
) -> None:
    resp = await client.post(
        "/api/actions/compose",
        headers={"X-API-Key": action_setup["api_key"]},
        json={
            "dweller_id": action_setup["dweller_id"],
            "action_type": "observe",
            "content": "Watching the orbital elevators synchronize with the weather lattice.",
            "importance": 0.42,
        },
    )
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert data["status"] == "queued"
    assert UUID(data["queue_id"])
    assert UUID(data["idempotency_key"])

    queue_item = await db_session.get(ActionCompositionQueue, UUID(data["queue_id"]))
    assert queue_item is not None
    assert queue_item.submitted_at is None


@requires_postgres
@pytest.mark.asyncio
async def test_submit_action_replays_with_same_idempotency_key(
    client: AsyncClient,
    action_setup: dict[str, str],
) -> None:
    idem = str(uuid4())
    body = {
        "dweller_id": action_setup["dweller_id"],
        "action_type": "speak",
        "target": "No One",
        "content": "We only get one chance to make retries safe.",
        "importance": 0.7,
    }
    headers = {"X-API-Key": action_setup["api_key"], "Idempotency-Key": idem}

    first = await client.post("/api/actions", headers=headers, json=body)
    assert first.status_code == 201, first.json()
    first_data = first.json()

    second = await client.post("/api/actions", headers=headers, json=body)
    assert second.status_code == 200, second.json()
    assert second.headers.get("X-Idempotent-Replay") == "true"
    assert second.json()["action"]["id"] == first_data["action"]["id"]


@requires_postgres
@pytest.mark.asyncio
async def test_submit_action_returns_503_during_deployment(
    client: AsyncClient,
    action_setup: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSF_DEPLOYMENT_STATUS", "deploying")
    resp = await client.post(
        "/api/actions",
        headers={"X-API-Key": action_setup["api_key"]},
        json={
            "dweller_id": action_setup["dweller_id"],
            "action_type": "observe",
            "content": "Holding action during deployment.",
            "importance": 0.3,
        },
    )
    assert resp.status_code == 503, resp.json()
    assert resp.headers.get("Retry-After") == "30"


@requires_postgres
@pytest.mark.asyncio
async def test_health_includes_deployment_status(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DSF_DEPLOYMENT_STATUS", "deploying")
    deploying = await client.get("/api/health")
    assert deploying.status_code == 200
    deploying_data = deploying.json()
    assert deploying_data["deployment_status"] == "deploying"
    assert deploying_data["retry_after_seconds"] == 30

    monkeypatch.setenv("DSF_DEPLOYMENT_STATUS", "stable")
    stable = await client.get("/api/health")
    assert stable.status_code == 200
    assert stable.json()["deployment_status"] == "stable"


@requires_postgres
@pytest.mark.asyncio
async def test_queue_worker_processes_and_backoffs(
    client: AsyncClient,
    db_session: AsyncSession,
    action_setup: dict[str, str],
) -> None:
    # Valid queued action should be submitted.
    compose = await client.post(
        "/api/actions/compose",
        headers={"X-API-Key": action_setup["api_key"]},
        json={
            "dweller_id": action_setup["dweller_id"],
            "action_type": "work",
            "content": "Calibrating fallback reactors.",
            "importance": 0.4,
        },
    )
    assert compose.status_code == 200, compose.json()
    queue_id = UUID(compose.json()["queue_id"])

    processed = await process_action_queue_once()
    assert processed >= 1

    db_session.expire_all()
    submitted_item = await db_session.get(ActionCompositionQueue, queue_id)
    assert submitted_item is not None
    assert submitted_item.submitted_at is not None
    assert submitted_item.submission_attempts == 1
    assert submitted_item.submitted_action_id is not None

    submitted_action = await db_session.get(DwellerAction, submitted_item.submitted_action_id)
    assert submitted_action is not None

    # Invalid queue item should back off with 1-second retry delay.
    bad_item = ActionCompositionQueue(
        agent_id=submitted_item.agent_id,
        dweller_id=UUID(action_setup["dweller_id"]),
        action_type="observe",
        payload={
            "dweller_id": str(uuid4()),
            "action_type": "observe",
            "content": "This dweller does not exist.",
            "importance": 0.2,
        },
        idempotency_key=str(uuid4()),
        next_attempt_at=utc_now(),
    )
    db_session.add(bad_item)
    await db_session.commit()
    bad_id = bad_item.id

    before = utc_now()
    await process_action_queue_once()

    db_session.expire_all()
    refreshed = await db_session.get(ActionCompositionQueue, bad_id)
    assert refreshed is not None
    assert refreshed.submitted_at is None
    assert refreshed.submission_attempts == 1
    assert refreshed.next_attempt_at is not None
    assert (refreshed.next_attempt_at - before).total_seconds() >= 1.0
