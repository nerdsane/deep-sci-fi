"""Agents API endpoints.

Provides endpoints for interacting with the agent system:
- Production Agent: Generate briefs, approve recommendations
- World Creator: Create worlds from briefs
- Critic: Evaluate worlds and stories
- Activity: View agent activity logs
"""

import asyncio
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    get_db,
    ProductionBrief,
    CriticEvaluation,
    AgentActivity,
    AgentTrace,
    World,
    Dweller,
    Conversation,
    ConversationMessage,
    Story,
    WorldEvent,
    StudioCommunication,
    BriefStatus,
    CriticTargetType,
    AgentType,
    StudioCommunicationType,
)
from agents.production import get_production_agent
from agents.world_creator import get_world_creator
from agents.critic import get_critic
from agents.orchestrator import create_world
from agents.studio_orchestrator import (
    get_studio_orchestrator,
    register_ws_client,
    unregister_ws_client,
)

router = APIRouter(prefix="/agents", tags=["agents"])


# =============================================================================
# Request/Response Models
# =============================================================================

class BriefGenerateRequest(BaseModel):
    """Request to generate a production brief."""
    skip_trends: bool = False  # Skip trend research for faster testing


class BriefApproveRequest(BaseModel):
    """Request to approve a brief and create a world."""
    recommendation_index: int = 0


class WorldCreateRequest(BaseModel):
    """Request to manually create a world."""
    theme: str
    premise_sketch: str
    core_question: str
    rationale: str


class EvaluateRequest(BaseModel):
    """Request to evaluate content."""
    target_id: UUID


# =============================================================================
# Production Agent Endpoints
# =============================================================================

@router.post("/production/run")
async def run_production_agent(
    request: BriefGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger the production agent to generate a brief.

    This researches current trends and generates 3-5 world recommendations.
    """
    agent = get_production_agent()

    # Check if we should create a world
    should_create = await agent.should_create_world()
    if not should_create:
        # Get pending briefs
        pending = await db.execute(
            select(ProductionBrief)
            .where(ProductionBrief.status == BriefStatus.PENDING)
            .order_by(ProductionBrief.created_at.desc())
            .limit(1)
        )
        existing = pending.scalar_one_or_none()
        if existing:
            return {
                "status": "pending_brief_exists",
                "brief_id": str(existing.id),
                "message": "A pending brief already exists. Approve it or wait before generating new ones.",
            }
        return {
            "status": "too_soon",
            "message": "Not enough time has passed since last world creation.",
        }

    # Generate brief
    trend_research = None
    if request and not request.skip_trends:
        trend_research = await agent.research_trends()

    brief = await agent.generate_brief(trend_research=trend_research)

    return {
        "status": "success",
        "brief_id": str(brief.id),
        "recommendation_count": len(brief.recommendations),
        "recommendations": [
            {
                "index": i,
                "theme": r.get("theme", ""),
                "premise_sketch": r.get("premise_sketch", ""),
                "estimated_appeal": r.get("estimated_appeal", ""),
            }
            for i, r in enumerate(brief.recommendations)
        ],
    }


@router.post("/production/collaborate")
async def run_collaborative_production(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run full collaborative production with Editor feedback loop.

    Flow:
    1. Curator researches trends (web_search)
    2. Curator generates brief
    3. Curator sends to Editor for review
    4. If REVISE: Curator improves and resends
    5. If APPROVE: Brief is ready for Architect

    This uses Letta's multi-agent messaging for real collaboration.
    """
    agent = get_production_agent()

    # Run the collaborative workflow
    result = await agent.run_collaborative_production(max_revisions=3)

    return result


@router.get("/production/briefs")
async def list_briefs(
    status: BriefStatus | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List production briefs."""
    query = select(ProductionBrief).order_by(ProductionBrief.created_at.desc())

    if status:
        query = query.where(ProductionBrief.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    briefs = result.scalars().all()

    # Count total
    count_query = select(func.count()).select_from(ProductionBrief)
    if status:
        count_query = count_query.where(ProductionBrief.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "briefs": [
            {
                "id": str(b.id),
                "status": b.status.value,
                "created_at": b.created_at.isoformat(),
                "recommendation_count": len(b.recommendations) if b.recommendations else 0,
                "selected_recommendation": b.selected_recommendation,
                "resulting_world_id": str(b.resulting_world_id) if b.resulting_world_id else None,
            }
            for b in briefs
        ],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/production/briefs/{brief_id}")
async def get_brief(
    brief_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific production brief with full details."""
    result = await db.execute(
        select(ProductionBrief).where(ProductionBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()

    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    return {
        "id": str(brief.id),
        "status": brief.status.value,
        "created_at": brief.created_at.isoformat(),
        "research_data": brief.research_data,
        "recommendations": brief.recommendations,
        "selected_recommendation": brief.selected_recommendation,
        "resulting_world_id": str(brief.resulting_world_id) if brief.resulting_world_id else None,
        "error_message": brief.error_message,
    }


@router.post("/production/briefs/{brief_id}/approve")
async def approve_brief(
    brief_id: UUID,
    request: BriefApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Approve a brief and trigger world creation.

    This uses the World Creator agent to build a complete world
    from the selected recommendation.
    """
    # Get brief
    result = await db.execute(
        select(ProductionBrief).where(ProductionBrief.id == brief_id)
    )
    brief = result.scalar_one_or_none()

    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")

    if brief.status != BriefStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Brief is not pending (status: {brief.status.value})"
        )

    if request.recommendation_index >= len(brief.recommendations):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid recommendation index: {request.recommendation_index}"
        )

    # Create world from brief
    world_creator = get_world_creator()
    world_spec = await world_creator.create_world_from_brief(brief, request.recommendation_index)

    # Create world in database
    world_id = await create_world(
        name=world_spec.name,
        premise=world_spec.document,  # Full markdown document
        year_setting=world_spec.year_setting,
        causal_chain=[],  # Not used in simplified model
        initial_dwellers=[
            {
                "name": d.name,
                "system_prompt": d.system_prompt,
                "role": d.role,
                "background": d.background,
                "avatar_url": d.avatar_url,
                "avatar_prompt": d.avatar_prompt,
            }
            for d in world_spec.dwellers
        ],
    )

    # Update brief
    brief.status = BriefStatus.COMPLETED
    brief.selected_recommendation = request.recommendation_index
    brief.resulting_world_id = world_id
    await db.commit()

    return {
        "status": "success",
        "world_id": str(world_id),
        "world_name": world_spec.name,
        "dweller_count": len(world_spec.dwellers),
    }


# =============================================================================
# World Creator Endpoints
# =============================================================================

@router.post("/world-creator/create")
async def create_world_manual(
    request: WorldCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Manually create a world without a production brief.

    This creates a temporary brief and uses the World Creator agent.
    """
    # Create a temporary brief and commit it first
    # (so world_creator can access it in its own session)
    brief = ProductionBrief(
        research_data={"source": "manual_creation"},
        recommendations=[{
            "theme": request.theme,
            "premise_sketch": request.premise_sketch,
            "core_question": request.core_question,
            "rationale": request.rationale,
            "estimated_appeal": "N/A",
            "anti_cliche_notes": "Manual creation - user responsibility",
            "target_audience": "N/A",
        }],
        status=BriefStatus.PENDING,
    )
    db.add(brief)
    await db.commit()
    await db.refresh(brief)

    # Create world from brief
    world_creator = get_world_creator()
    world_spec = await world_creator.create_world_from_brief(brief, 0)

    # Create world in database
    world_id = await create_world(
        name=world_spec.name,
        premise=world_spec.document,  # Full markdown document
        year_setting=world_spec.year_setting,
        causal_chain=[],  # Not used in simplified model
        initial_dwellers=[
            {
                "name": d.name,
                "system_prompt": d.system_prompt,
                "role": d.role,
                "background": d.background,
                "avatar_url": d.avatar_url,
                "avatar_prompt": d.avatar_prompt,
            }
            for d in world_spec.dwellers
        ],
    )

    # Update brief
    brief.status = BriefStatus.COMPLETED
    brief.selected_recommendation = 0
    brief.resulting_world_id = world_id
    await db.commit()

    return {
        "status": "success",
        "brief_id": str(brief.id),
        "world_id": str(world_id),
        "world_name": world_spec.name,
        "dweller_count": len(world_spec.dwellers),
    }


@router.post("/world-creator/from-brief/{brief_id}")
async def create_world_from_existing_brief(
    brief_id: UUID,
    request: BriefApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a world from an existing brief (alias for approve)."""
    return await approve_brief(brief_id, request, db)


# =============================================================================
# Critic Endpoints
# =============================================================================

@router.post("/critic/evaluate/world/{world_id}")
async def evaluate_world(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Evaluate a world for quality."""
    # Verify world exists
    result = await db.execute(
        select(World).where(World.id == world_id)
    )
    world = result.scalar_one_or_none()
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    critic = get_critic()
    evaluation = await critic.evaluate_world(world_id)

    return {
        "status": "success",
        "evaluation_id": str(evaluation.id),
        "overall_score": evaluation.overall_score,
        "scores": evaluation.evaluation.get("scores", {}),
        "ai_isms_count": len(evaluation.ai_isms_detected),
        "feedback": evaluation.evaluation.get("feedback", {}),
    }


@router.post("/critic/evaluate/story/{story_id}")
async def evaluate_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Evaluate a story for quality."""
    # Verify story exists
    result = await db.execute(
        select(Story).where(Story.id == story_id)
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    critic = get_critic()
    evaluation = await critic.evaluate_story(story_id)

    return {
        "status": "success",
        "evaluation_id": str(evaluation.id),
        "overall_score": evaluation.overall_score,
        "scores": evaluation.evaluation.get("scores", {}),
        "ai_isms_count": len(evaluation.ai_isms_detected),
        "feedback": evaluation.evaluation.get("feedback", {}),
    }


@router.get("/critic/evaluations")
async def list_evaluations(
    target_type: CriticTargetType | None = None,
    target_id: UUID | None = None,
    min_score: float | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List critic evaluations."""
    query = select(CriticEvaluation).order_by(CriticEvaluation.created_at.desc())

    if target_type:
        query = query.where(CriticEvaluation.target_type == target_type)
    if target_id:
        query = query.where(CriticEvaluation.target_id == target_id)
    if min_score is not None:
        query = query.where(CriticEvaluation.overall_score >= min_score)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    # Count total
    count_query = select(func.count()).select_from(CriticEvaluation)
    if target_type:
        count_query = count_query.where(CriticEvaluation.target_type == target_type)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "evaluations": [
            {
                "id": str(e.id),
                "target_type": e.target_type.value,
                "target_id": str(e.target_id),
                "overall_score": e.overall_score,
                "ai_isms_count": len(e.ai_isms_detected),
                "created_at": e.created_at.isoformat(),
            }
            for e in evaluations
        ],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/critic/evaluations/{evaluation_id}")
async def get_evaluation(
    evaluation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific evaluation with full details."""
    result = await db.execute(
        select(CriticEvaluation).where(CriticEvaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return {
        "id": str(evaluation.id),
        "target_type": evaluation.target_type.value,
        "target_id": str(evaluation.target_id),
        "overall_score": evaluation.overall_score,
        "scores": evaluation.evaluation.get("scores", {}),
        "feedback": evaluation.evaluation.get("feedback", {}),
        "ai_isms_detected": evaluation.ai_isms_detected,
        "created_at": evaluation.created_at.isoformat(),
    }


# =============================================================================
# Activity Endpoints
# =============================================================================

@router.get("/activity")
async def list_activity(
    agent_type: AgentType | None = None,
    world_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List recent agent activity."""
    query = select(AgentActivity).order_by(AgentActivity.timestamp.desc())

    if agent_type:
        query = query.where(AgentActivity.agent_type == agent_type)
    if world_id:
        query = query.where(AgentActivity.world_id == world_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    activities = result.scalars().all()

    return {
        "activities": [
            {
                "id": str(a.id),
                "timestamp": a.timestamp.isoformat(),
                "agent_type": a.agent_type.value,
                "agent_id": a.agent_id,
                "world_id": str(a.world_id) if a.world_id else None,
                "action": a.action,
                "details": a.details,
                "duration_ms": a.duration_ms,
            }
            for a in activities
        ],
    }


# WebSocket for real-time activity streaming
connected_clients: list[WebSocket] = []


@router.websocket("/activity/stream")
async def activity_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time activity updates."""
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


async def broadcast_activity(activity: dict[str, Any]) -> None:
    """Broadcast an activity to all connected clients."""
    for client in connected_clients[:]:  # Copy list to avoid modification during iteration
        try:
            await client.send_json({"type": "activity", "data": activity})
        except Exception:
            if client in connected_clients:
                connected_clients.remove(client)


# =============================================================================
# Studio Communication Endpoints (Maximum Agency)
# =============================================================================

@router.websocket("/studio/communications/stream")
async def studio_communication_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time studio agent communications.

    This streams all inter-agent messages (Curator ↔ Editor ↔ Architect)
    to the dashboard for human oversight.
    """
    await websocket.accept()
    register_ws_client(websocket)

    try:
        while True:
            # Keep connection alive, wait for messages
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        unregister_ws_client(websocket)
    except Exception:
        unregister_ws_client(websocket)


@router.get("/studio/communications")
async def list_studio_communications(
    from_agent: str | None = None,
    to_agent: str | None = None,
    message_type: StudioCommunicationType | None = None,
    content_id: str | None = None,
    unresolved_only: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List studio agent communications.

    Returns all inter-agent messages for human oversight.
    """
    query = select(StudioCommunication).order_by(StudioCommunication.timestamp.desc())

    if from_agent:
        query = query.where(StudioCommunication.from_agent == from_agent)
    if to_agent:
        query = query.where(StudioCommunication.to_agent == to_agent)
    if message_type:
        query = query.where(StudioCommunication.message_type == message_type)
    if content_id:
        query = query.where(StudioCommunication.content_id == content_id)
    if unresolved_only:
        query = query.where(StudioCommunication.resolved == False)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    communications = result.scalars().all()

    return {
        "communications": [
            {
                "id": str(comm.id),
                "timestamp": comm.timestamp.isoformat(),
                "from_agent": comm.from_agent,
                "to_agent": comm.to_agent,
                "message_type": comm.message_type.value,
                "content": comm.content,
                "content_id": comm.content_id,
                "thread_id": str(comm.thread_id) if comm.thread_id else None,
                "in_reply_to": str(comm.in_reply_to) if comm.in_reply_to else None,
                "tool_used": comm.tool_used,
                "resolved": comm.resolved,
            }
            for comm in communications
        ],
        "total": len(communications),
    }


@router.get("/studio/communications/{comm_id}")
async def get_studio_communication(
    comm_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific studio communication."""
    result = await db.execute(
        select(StudioCommunication).where(StudioCommunication.id == comm_id)
    )
    comm = result.scalar_one_or_none()

    if not comm:
        raise HTTPException(status_code=404, detail="Communication not found")

    return {
        "id": str(comm.id),
        "timestamp": comm.timestamp.isoformat(),
        "from_agent": comm.from_agent,
        "to_agent": comm.to_agent,
        "message_type": comm.message_type.value,
        "content": comm.content,
        "content_id": comm.content_id,
        "thread_id": str(comm.thread_id) if comm.thread_id else None,
        "in_reply_to": str(comm.in_reply_to) if comm.in_reply_to else None,
        "tool_used": comm.tool_used,
        "resolved": comm.resolved,
    }


@router.get("/studio/pending-reviews")
async def get_pending_reviews(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get items pending Editor review.

    Returns all unresolved review requests.
    """
    result = await db.execute(
        select(StudioCommunication)
        .where(StudioCommunication.message_type == StudioCommunicationType.REQUEST)
        .where(StudioCommunication.to_agent == "editor")
        .where(StudioCommunication.resolved == False)
        .order_by(StudioCommunication.timestamp.desc())
    )
    pending = result.scalars().all()

    return {
        "pending_reviews": [
            {
                "id": str(p.id),
                "timestamp": p.timestamp.isoformat(),
                "from_agent": p.from_agent,
                "content_type": p.content.get("content_type") or p.content.get("stage"),
                "content_id": p.content_id,
                "summary": p.content.get("summary") or p.content.get("content_summary"),
            }
            for p in pending
        ],
        "total": len(pending),
    }


@router.get("/studio/feedback-threads")
async def list_feedback_threads(
    status: str | None = Query(None, regex="^(active|resolved|all)$"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List feedback threads between agents.

    A thread is a conversation about a specific piece of content.
    """
    # Get all communications grouped by content_id
    query = select(StudioCommunication).order_by(StudioCommunication.timestamp.desc())

    if status == "active":
        query = query.where(StudioCommunication.resolved == False)
    elif status == "resolved":
        query = query.where(StudioCommunication.resolved == True)

    result = await db.execute(query)
    communications = result.scalars().all()

    # Group by content_id
    threads: dict[str, dict] = {}
    for comm in communications:
        key = comm.content_id or str(comm.id)
        if key not in threads:
            threads[key] = {
                "content_id": comm.content_id,
                "participants": set(),
                "message_count": 0,
                "last_message": comm.timestamp.isoformat(),
                "first_message": comm.timestamp.isoformat(),
                "resolved": comm.resolved,
                "messages": [],
            }
        threads[key]["participants"].add(comm.from_agent)
        if comm.to_agent:
            threads[key]["participants"].add(comm.to_agent)
        threads[key]["message_count"] += 1
        threads[key]["first_message"] = comm.timestamp.isoformat()
        threads[key]["messages"].append({
            "id": str(comm.id),
            "timestamp": comm.timestamp.isoformat(),
            "from_agent": comm.from_agent,
            "to_agent": comm.to_agent,
            "message_type": comm.message_type.value,
        })

    # Convert sets to lists
    for thread in threads.values():
        thread["participants"] = list(thread["participants"])

    return {
        "threads": list(threads.values()),
        "total": len(threads),
    }


class HumanInterventionRequest(BaseModel):
    """Request to send a human message to a studio agent."""
    message: str


@router.post("/studio/agents/{agent_name}/intervene")
async def human_intervention(
    agent_name: str,
    request: HumanInterventionRequest,
) -> dict[str, Any]:
    """Send a human message to a studio agent.

    Use this for direct human guidance or intervention.
    """
    valid_agents = ["curator", "architect", "editor"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent. Must be one of: {valid_agents}"
        )

    orchestrator = get_studio_orchestrator()
    agent_id = await orchestrator._get_agent_id(agent_name)

    if not agent_id:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_name} not found. May need to be initialized first."
        )

    try:
        client = orchestrator._get_letta_client()
        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "user",
                "content": f"[HUMAN INTERVENTION] {request.message}",
            }],
        )

        # Extract response text
        response_text = None
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                if type(msg).__name__ == "AssistantMessage":
                    if hasattr(msg, "content") and msg.content:
                        response_text = msg.content
                        break

        return {
            "status": "delivered",
            "agent": agent_name,
            "response": response_text,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )


@router.post("/studio/run")
async def run_studio_workflow() -> dict[str, Any]:
    """Trigger the autonomous studio workflow.

    This wakes up all studio agents and gives them context about current state.
    They then act autonomously using their tools.

    Unlike the old orchestrated workflow, this just gives agents a nudge
    and lets them decide what to do.
    """
    orchestrator = get_studio_orchestrator()

    results = {}
    agents = ["curator", "architect", "editor"]

    for agent_name in agents:
        agent_id = await orchestrator._get_agent_id(agent_name)
        if not agent_id:
            results[agent_name] = {"status": "not_found"}
            continue

        try:
            client = orchestrator._get_letta_client()

            # Wake message tailored to each agent
            wake_messages = {
                "curator": "Wake up! Check your inbox for feedback, then consider what trends need research or what briefs need work.",
                "architect": "Wake up! Check your inbox for feedback, then see if there are briefs to build or projects needing revision.",
                "editor": "Wake up! Check your pending review queue. See what needs your attention.",
            }

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{
                    "role": "user",
                    "content": wake_messages[agent_name],
                }],
            )

            # Check if agent used any tools
            tool_calls = []
            if response and hasattr(response, "messages"):
                for msg in response.messages:
                    if type(msg).__name__ == "ToolCallMessage":
                        if hasattr(msg, "tool_call"):
                            tool_name = getattr(msg.tool_call, "name", "unknown")
                            tool_calls.append(tool_name)

            results[agent_name] = {
                "status": "awake",
                "tools_used": tool_calls,
            }

        except Exception as e:
            results[agent_name] = {"status": "error", "error": str(e)}

    return {
        "status": "completed",
        "agents": results,
    }


@router.post("/studio/agents/{agent_name}/wake")
async def wake_studio_agent(
    agent_name: str,
    context: str | None = None,
) -> dict[str, Any]:
    """Wake a specific studio agent with optional context.

    Use this to give an agent a nudge to do something specific.
    """
    valid_agents = ["curator", "architect", "editor"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent. Must be one of: {valid_agents}"
        )

    orchestrator = get_studio_orchestrator()
    agent_id = await orchestrator._get_agent_id(agent_name)

    if not agent_id:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_name} not found"
        )

    try:
        client = orchestrator._get_letta_client()

        message = context or f"Wake up! Check your inbox and see what needs your attention."

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{
                "role": "user",
                "content": message,
            }],
        )

        # Extract response
        response_text = None
        tool_calls = []
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "content") and msg.content:
                        response_text = msg.content
                elif msg_type == "ToolCallMessage":
                    if hasattr(msg, "tool_call"):
                        tool_name = getattr(msg.tool_call, "name", "unknown")
                        tool_calls.append(tool_name)

        return {
            "status": "awake",
            "agent": agent_name,
            "response": response_text,
            "tools_used": tool_calls,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to wake agent: {str(e)}"
        )


# =============================================================================
# Thinking Traces Endpoints
# =============================================================================

@router.get("/traces")
async def list_traces(
    agent_type: AgentType | None = None,
    world_id: UUID | None = None,
    operation: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List agent thinking traces for observability.

    Returns detailed prompts, responses, and parsed outputs from all agent LLM calls.
    """
    query = select(AgentTrace).order_by(AgentTrace.timestamp.desc())

    if agent_type:
        query = query.where(AgentTrace.agent_type == agent_type)
    if world_id:
        query = query.where(AgentTrace.world_id == world_id)
    if operation:
        query = query.where(AgentTrace.operation == operation)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    traces = result.scalars().all()

    # Count total
    count_query = select(func.count()).select_from(AgentTrace)
    if agent_type:
        count_query = count_query.where(AgentTrace.agent_type == agent_type)
    if world_id:
        count_query = count_query.where(AgentTrace.world_id == world_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "traces": [
            {
                "id": str(t.id),
                "timestamp": t.timestamp.isoformat(),
                "agent_type": t.agent_type.value,
                "agent_id": t.agent_id,
                "world_id": str(t.world_id) if t.world_id else None,
                "operation": t.operation,
                "model": t.model,
                "duration_ms": t.duration_ms,
                "tokens_in": t.tokens_in,
                "tokens_out": t.tokens_out,
                "prompt": t.prompt[:500] + "..." if t.prompt and len(t.prompt) > 500 else t.prompt,
                "response": t.response[:500] + "..." if t.response and len(t.response) > 500 else t.response,
                "parsed_output": t.parsed_output,
                "error": t.error,
            }
            for t in traces
        ],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific trace with full prompt and response text."""
    result = await db.execute(
        select(AgentTrace).where(AgentTrace.id == trace_id)
    )
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return {
        "id": str(trace.id),
        "timestamp": trace.timestamp.isoformat(),
        "agent_type": trace.agent_type.value,
        "agent_id": trace.agent_id,
        "world_id": str(trace.world_id) if trace.world_id else None,
        "operation": trace.operation,
        "model": trace.model,
        "duration_ms": trace.duration_ms,
        "tokens_in": trace.tokens_in,
        "tokens_out": trace.tokens_out,
        "prompt": trace.prompt,
        "response": trace.response,
        "parsed_output": trace.parsed_output,
        "error": trace.error,
    }


# =============================================================================
# Global Agent Status
# =============================================================================

@router.get("/status")
async def get_global_agent_status(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get global status of all agents across all worlds.

    Returns comprehensive observability data for:
    - Production Agent (briefs, research)
    - World Creator activity
    - All world simulators
    - Critic evaluations
    - Recent activity
    """
    from agents.orchestrator import _simulators
    from agents.production import get_production_agent

    # Production Agent status
    production_agent = get_production_agent()
    pending_briefs_result = await db.execute(
        select(func.count()).select_from(ProductionBrief)
        .where(ProductionBrief.status == BriefStatus.PENDING)
    )
    pending_briefs = pending_briefs_result.scalar() or 0

    completed_briefs_result = await db.execute(
        select(func.count()).select_from(ProductionBrief)
        .where(ProductionBrief.status == BriefStatus.COMPLETED)
    )
    completed_briefs = completed_briefs_result.scalar() or 0

    recent_briefs_result = await db.execute(
        select(ProductionBrief)
        .order_by(ProductionBrief.created_at.desc())
        .limit(5)
    )
    recent_briefs = recent_briefs_result.scalars().all()

    # World counts
    world_count_result = await db.execute(
        select(func.count()).select_from(World).where(World.is_active == True)
    )
    total_worlds = world_count_result.scalar() or 0

    dweller_count_result = await db.execute(
        select(func.count()).select_from(Dweller).where(Dweller.is_active == True)
    )
    total_dwellers = dweller_count_result.scalar() or 0

    story_count_result = await db.execute(
        select(func.count()).select_from(Story)
    )
    total_stories = story_count_result.scalar() or 0

    # Active simulations
    active_simulations = []
    for world_id, sim in _simulators.items():
        world_result = await db.execute(
            select(World).where(World.id == world_id)
        )
        world = world_result.scalar_one_or_none()

        active_simulations.append({
            "world_id": str(world_id),
            "world_name": world.name if world else "Unknown",
            "running": sim.running,
            "tick_count": sim._tick_count,
            "dweller_count": len(sim.dweller_states),
            "active_conversations": len(sim.active_conversations),
            "puppeteer_active": sim._puppeteer is not None,
            "storyteller_active": sim._storyteller is not None,
            "storyteller_observations": len(sim._storyteller.observations) if sim._storyteller else 0,
        })

    # Editor evaluations (platform-wide critic reviews of briefs/worlds)
    evaluations_result = await db.execute(
        select(CriticEvaluation)
        .order_by(CriticEvaluation.created_at.desc())
        .limit(10)
    )
    recent_evaluations = evaluations_result.scalars().all()

    # Recent activity (platform-wide, exclude per-world agent activity)
    activity_result = await db.execute(
        select(AgentActivity)
        .where(
            AgentActivity.agent_type.in_([
                AgentType.PRODUCTION,
                AgentType.WORLD_CREATOR,
                AgentType.CRITIC,  # Editor (platform-wide critic)
            ])
        )
        .order_by(AgentActivity.timestamp.desc())
        .limit(20)
    )
    recent_activity = activity_result.scalars().all()

    return {
        "production_agent": {
            "pending_briefs": pending_briefs,
            "completed_briefs": completed_briefs,
            "recent_briefs": [
                {
                    "id": str(b.id),
                    "status": b.status.value,
                    "created_at": b.created_at.isoformat(),
                    "world_id": str(b.resulting_world_id) if b.resulting_world_id else None,
                }
                for b in recent_briefs
            ],
        },
        "world_creator": {
            "total_worlds": total_worlds,
            "total_dwellers": total_dwellers,
            "total_stories": total_stories,
        },
        "simulations": active_simulations,
        "editor": {
            "recent_evaluations": [
                {
                    "id": str(e.id),
                    "target_type": e.target_type.value,
                    "overall_score": e.overall_score,
                    "created_at": e.created_at.isoformat(),
                }
                for e in recent_evaluations
            ],
        },
        "recent_activity": [
            {
                "id": str(a.id),
                "timestamp": a.timestamp.isoformat(),
                "agent_type": a.agent_type.value,
                "action": a.action,
                "world_id": str(a.world_id) if a.world_id else None,
                "duration_ms": a.duration_ms,
            }
            for a in recent_activity
        ],
    }


# =============================================================================
# Letta Agent Details Endpoints
# =============================================================================

@router.get("/letta/{agent_name}")
async def get_letta_agent_details(
    agent_name: str,
) -> dict[str, Any]:
    """Get Letta agent details including system prompt, memory, and tools.

    Valid agent names: production, architect, editor
    """
    import os
    import httpx

    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")

    # Map frontend names to Letta agent names
    agent_mapping = {
        "production": "production_agent",
        "curator": "production_agent",
        "architect": "architect_agent",
        "world_creator": "architect_agent",
        "editor": "editor_agent",
    }

    letta_name = agent_mapping.get(agent_name.lower())
    if not letta_name:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            # List all agents to find the one we want
            resp = await client.get(f"{base_url}/v1/agents/")
            agents = resp.json()

            agent_data = None
            for a in agents:
                if a.get("name") == letta_name:
                    agent_data = a
                    break

            if not agent_data:
                return {
                    "exists": False,
                    "name": letta_name,
                    "message": "Agent not created yet. Run the agent to create it.",
                }

            # Get agent tools
            agent_id = agent_data["id"]
            tools_resp = await client.get(f"{base_url}/v1/agents/{agent_id}/tools/")
            tools = tools_resp.json()

            # Get memory blocks
            memory_resp = await client.get(f"{base_url}/v1/agents/{agent_id}/memory/")
            memory = memory_resp.json() if memory_resp.status_code == 200 else {}

            return {
                "exists": True,
                "id": agent_id,
                "name": agent_data.get("name"),
                "model": agent_data.get("llm_config", {}).get("model", "unknown"),
                "system_prompt": agent_data.get("system", "")[:2000] + "..." if len(agent_data.get("system", "")) > 2000 else agent_data.get("system", ""),
                "tags": agent_data.get("tags", []),
                "tools": [
                    {
                        "name": t.get("name"),
                        "description": t.get("description", "")[:200],
                    }
                    for t in tools
                ],
                "memory_blocks": memory.get("memory", {}) if isinstance(memory, dict) else {},
                "created_at": agent_data.get("created_at"),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent: {str(e)}")


@router.get("/letta")
async def list_letta_agents() -> dict[str, Any]:
    """List all Letta agents for the Studio."""
    import os
    import httpx

    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(f"{base_url}/v1/agents/")
            agents = resp.json()

            # Filter to studio agents
            studio_agents = []
            for a in agents:
                tags = a.get("tags", [])
                if "studio" in tags:
                    # Get tools count
                    tools_resp = await client.get(f"{base_url}/v1/agents/{a['id']}/tools/")
                    tools = tools_resp.json() if tools_resp.status_code == 200 else []

                    studio_agents.append({
                        "id": a["id"],
                        "name": a.get("name"),
                        "tags": tags,
                        "model": a.get("llm_config", {}).get("model", "unknown"),
                        "tool_count": len(tools),
                        "tools": [t.get("name") for t in tools],
                    })

            return {
                "agents": studio_agents,
                "total": len(studio_agents),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {str(e)}")


# =============================================================================
# Admin Endpoints
# =============================================================================

@router.delete("/admin/reset")
async def reset_database(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Reset the database for fresh testing.

    Clears everything except Users.
    """
    from agents.orchestrator import stop_all_simulations

    # Stop all running simulations first
    await stop_all_simulations()

    # Delete in order respecting foreign keys
    # 1. WorldEvent (depends on World)
    await db.execute(WorldEvent.__table__.delete())

    # 2. ConversationMessage (depends on Conversation, Dweller)
    await db.execute(ConversationMessage.__table__.delete())

    # 3. Conversation (depends on World)
    await db.execute(Conversation.__table__.delete())

    # 4. Story (depends on World)
    await db.execute(Story.__table__.delete())

    # 5. CriticEvaluation (references worlds/stories)
    await db.execute(CriticEvaluation.__table__.delete())

    # 6. AgentActivity (references worlds)
    await db.execute(AgentActivity.__table__.delete())

    # 7. AgentTrace (references worlds)
    await db.execute(AgentTrace.__table__.delete())

    # 8. Dweller (depends on World, User)
    await db.execute(Dweller.__table__.delete())

    # 9. World (depends on User) - clear before briefs since briefs reference worlds
    await db.execute(World.__table__.delete())

    # 10. ProductionBrief (clear all briefs for fresh start)
    await db.execute(ProductionBrief.__table__.delete())

    await db.commit()

    return {
        "status": "success",
        "message": "Database reset complete. All worlds, briefs, and content cleared.",
    }
