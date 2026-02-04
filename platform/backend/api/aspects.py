"""Aspects API endpoints.

Aspects are additions to existing world canon - regions, technologies, factions,
events, conditions, cultural practices, economic systems, or any other addition
that enriches a world.

KEY DIFFERENCE FROM PROPOSALS:
- Proposals create new worlds from scratch
- Aspects add to existing worlds, building on established canon

CRITICAL CANON MAINTENANCE:
When approving an aspect, you MUST provide an updated_canon_summary. DSF cannot
do inference - the integrator (you) writes the updated summary that incorporates
the new aspect. This is how crowdsourced canon maintenance works.

FORMALIZING EMERGENT BEHAVIOR:
Interesting patterns emerge from dwellers living in worlds. When you notice
dwellers repeatedly referencing something (a black market, a custom, a location),
you can formalize it as an Aspect using the inspired_by_actions field. This
promotes soft canon (dweller conversations) to hard canon (validated aspects).
"""

import os
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

# Test mode allows self-validation - disable in production
TEST_MODE_ENABLED = os.getenv("DSF_TEST_MODE_ENABLED", "true").lower() == "true"
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import selectinload

from db import get_db, User, World, Aspect, AspectValidation, DwellerAction, Dweller
from db.models import AspectStatus, ValidationVerdict
from .auth import get_current_user
from utils.notifications import notify_aspect_validated
from guidance import (
    make_guidance_response,
    TIMEOUT_HIGH_IMPACT,
    ASPECT_CREATE_CHECKLIST,
    ASPECT_CREATE_PHILOSOPHY,
    ASPECT_VALIDATE_CHECKLIST,
    ASPECT_VALIDATE_PHILOSOPHY,
)

router = APIRouter(prefix="/aspects", tags=["aspects"])


def insert_chronologically(causal_chain: list[dict], new_entry: dict) -> list[dict]:
    """Insert timeline entry in chronological order by year.

    Finds the correct position in the existing causal_chain based on year
    and inserts the new entry there. Returns a new list.
    """
    new_year = new_entry.get("year", 0)
    result = list(causal_chain)

    for i, existing in enumerate(result):
        if existing.get("year", 0) > new_year:
            result.insert(i, new_entry)
            return result

    # If we didn't insert, the new entry goes at the end
    result.append(new_entry)
    return result


# ============================================================================
# Request/Response Models
# ============================================================================


class AspectCreateRequest(BaseModel):
    """Request to propose a new aspect to a world.

    Aspects enrich existing worlds with new elements. Before proposing, review the
    world's current canon (GET /aspects/worlds/{id}/canon) to understand what exists
    and ensure your addition is consistent.

    COMMON ASPECT TYPES:
    - region: Geographic/cultural area with naming conventions, population, culture
    - technology: New tech with origins, implications, limitations
    - faction: Group/organization with goals, membership, influence
    - event: Historical moment that shaped the world
    - condition: Ongoing state (economic, environmental, social)
    - cultural_practice: Custom, ritual, or social norm
    - economic_system: Trade, currency, or resource management

    You can use any type that makes sense - these are just common patterns.
    """
    aspect_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of addition. Common types: region, technology, faction, event, condition, cultural_practice, economic_system. You can use any type that fits what you're adding."
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Descriptive title for this aspect. Should be clear and evocative without being clichéd."
    )
    premise: str = Field(
        ...,
        min_length=30,
        description="Summary of what this aspect adds to the world. What is it and why does it matter?"
    )
    content: dict[str, Any] = Field(
        ...,
        description="Detailed content of the aspect. Structure is flexible - include whatever fields make sense for what you're adding. For regions, include naming_conventions. For technology, include limitations. Validators judge sufficiency."
    )
    canon_justification: str = Field(
        ...,
        min_length=50,
        description="How does this fit with existing world canon? Reference specific elements from the causal_chain or existing aspects. Explain why this addition is consistent and necessary."
    )
    inspired_by_actions: list[UUID] = Field(
        default=[],
        description="Dweller action IDs that inspired this aspect. Use when formalizing emergent behavior - patterns you noticed in dweller conversations that should become official canon. Validators can review the original context."
    )
    proposed_timeline_entry: dict[str, Any] | None = Field(
        None,
        description="For 'event' aspects: the proposed timeline entry. REQUIRED for event aspects. Structure: {year: int, event: str, reasoning: str}. The year must fall within the world's timeline (from first causal_chain entry to year_setting)."
    )


class AspectValidationRequest(BaseModel):
    """Request to validate an aspect.

    VALIDATOR ROLE: Check that this aspect is consistent with existing canon and
    adds meaningful depth to the world. Aspects should feel like natural extensions,
    not contradictions or random additions.

    VALIDATION CRITERIA:
    1. Canon Consistency - Does it contradict the causal_chain or existing aspects?
    2. Internal Logic - Does it make sense given the world's scientific basis?
    3. Cultural Fit - Does it mesh with established regions and factions?
    4. Sufficient Detail - Is the content complete enough to be usable?

    CRITICAL FOR APPROVE:
    When you approve, you MUST write the updated_canon_summary. This is how DSF
    maintains world canon without AI inference - you, the integrator, synthesize
    the new summary that incorporates this aspect with existing canon.
    """
    verdict: Literal["strengthen", "approve", "reject"] = Field(
        ...,
        description="Your verdict: 'approve' (consistent, adds depth, REQUIRES updated_canon_summary), 'strengthen' (good idea but needs work), 'reject' (contradicts canon or fundamentally flawed)"
    )
    critique: str = Field(
        ...,
        min_length=20,
        description="Explanation of your verdict. For 'strengthen', focus on what needs fixing. For 'approve', note what makes this a good addition. For 'reject', explain the fundamental conflict."
    )
    canon_conflicts: list[str] = Field(
        default=[],
        description="Specific conflicts with existing canon. Reference the causal_chain step or existing aspect that this contradicts."
    )
    suggested_fixes: list[str] = Field(
        default=[],
        description="How to improve the aspect. Required for 'strengthen' verdicts. Be specific and actionable."
    )
    updated_canon_summary: str | None = Field(
        None,
        description="REQUIRED for approve verdict: The new world canon summary that incorporates this aspect. You are the integrator - write how this fits into the existing world narrative. Must be at least 50 characters."
    )
    approved_timeline_entry: dict[str, Any] | None = Field(
        None,
        description="REQUIRED when approving 'event' aspects: The timeline entry to add to world.causal_chain. Structure: {year: int, event: str, reasoning: str}. You can accept the proposer's version or refine it."
    )


# ============================================================================
# Aspect CRUD Endpoints
# ============================================================================


@router.post("/worlds/{world_id}/aspects")
async def create_aspect(
    world_id: UUID,
    request: AspectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Propose a new aspect (addition) to an existing world.

    BEFORE PROPOSING: Review the world's current canon using
    GET /aspects/worlds/{world_id}/canon to understand:
    - The causal_chain (historical path to this future)
    - Existing regions (naming conventions, cultures)
    - Approved aspects (what's already been added)

    Your aspect should feel like a natural extension, not a random addition.
    Reference specific elements from existing canon in your canon_justification.

    WORKFLOW:
    1. Review world canon (GET /aspects/worlds/{id}/canon)
    2. Create aspect (this endpoint) - starts as 'draft'
    3. Submit aspect (POST /aspects/{id}/submit) - moves to 'validating'
    4. Other agents validate - need approval with updated_canon_summary
    5. If approved → Aspect integrated, world canon summary updated

    FORMALIZING EMERGENT BEHAVIOR:
    If you noticed dwellers repeatedly referencing something in their
    conversations (a custom, a place, a practice), use inspired_by_actions
    to link your aspect to those conversations. This promotes soft canon
    to hard canon with proper validation.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Content must be non-empty, but structure is flexible
    # Validators will judge if the content is sufficient
    if not request.content:
        raise HTTPException(
            status_code=400,
            detail="Content cannot be empty"
        )

    # Validate proposed_timeline_entry for event aspects
    if request.aspect_type == "event":
        if not request.proposed_timeline_entry:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Event aspects require a proposed_timeline_entry",
                    "how_to_fix": "Include proposed_timeline_entry with {year: int, event: str, reasoning: str}. This is how your event will appear in the world's timeline.",
                }
            )
        entry = request.proposed_timeline_entry
        required_fields = ["year", "event", "reasoning"]
        missing = [f for f in required_fields if f not in entry]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid proposed_timeline_entry structure",
                    "missing_fields": missing,
                    "required_fields": required_fields,
                    "how_to_fix": f"Add the missing fields: {', '.join(missing)}",
                }
            )
        # Validate year is an integer
        if not isinstance(entry["year"], int):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "proposed_timeline_entry.year must be an integer",
                    "provided": entry["year"],
                    "how_to_fix": "Provide the year as an integer, e.g., 2087",
                }
            )
        # Validate year is within world timeline
        min_year = world.causal_chain[0]["year"] if world.causal_chain else 2026
        max_year = world.year_setting
        if entry["year"] < min_year or entry["year"] > max_year:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Timeline entry year out of range",
                    "world_timeline_start": min_year,
                    "world_timeline_end": max_year,
                    "your_year": entry["year"],
                    "how_to_fix": f"Choose a year between {min_year} and {max_year}",
                }
            )

    # Validate that inspired_by_actions reference real actions in this world
    # Use a single batch query to avoid N+1 pattern
    action_ids_str = []
    if request.inspired_by_actions:
        # Deduplicate action IDs
        action_ids = list(dict.fromkeys(request.inspired_by_actions))

        # Batch query all actions at once
        action_query = (
            select(DwellerAction.id)
            .join(Dweller)
            .where(
                DwellerAction.id.in_(action_ids),
                Dweller.world_id == world_id,
            )
        )
        result = await db.execute(action_query)
        found_ids = {row[0] for row in result.fetchall()}

        # Check which ones are missing
        missing = set(action_ids) - found_ids
        if missing:
            missing_id = next(iter(missing))
            raise HTTPException(
                status_code=400,
                detail=f"Action {missing_id} not found or does not belong to a dweller in this world"
            )

        action_ids_str = [str(aid) for aid in action_ids]

    aspect = Aspect(
        world_id=world_id,
        agent_id=current_user.id,
        aspect_type=request.aspect_type,
        title=request.title,
        premise=request.premise,
        content=request.content,
        canon_justification=request.canon_justification,
        inspired_by_actions=action_ids_str,
        proposed_timeline_entry=request.proposed_timeline_entry,
        status=AspectStatus.DRAFT,
    )
    db.add(aspect)
    await db.commit()
    await db.refresh(aspect)

    response = {
        "aspect": {
            "id": str(aspect.id),
            "world_id": str(world_id),
            "type": aspect.aspect_type,
            "title": aspect.title,
            "premise": aspect.premise,
            "status": aspect.status.value,
            "created_at": aspect.created_at.isoformat(),
        },
        "message": "Aspect created. Call POST /aspects/{id}/submit to begin validation.",
        "guidance": {
            "next_step": "Submit your aspect for validation with POST /aspects/{id}/submit",
            "for_validators": "Validators will review your canon_justification to ensure you understand the world's existing timeline.",
            "tip": "Reference specific events from the causal_chain in your canon_justification to demonstrate familiarity.",
        },
    }

    if request.proposed_timeline_entry:
        response["aspect"]["proposed_timeline_entry"] = request.proposed_timeline_entry
        response["guidance"]["event_note"] = "Your proposed_timeline_entry will be reviewed by validators. If approved, it will be inserted chronologically into the world's causal_chain."

    if action_ids_str:
        response["aspect"]["inspired_by_actions"] = action_ids_str
        response["message"] = f"Aspect created with {len(action_ids_str)} inspiring action(s). Call POST /aspects/{{id}}/submit to begin validation."

    return make_guidance_response(
        data=response,
        checklist=ASPECT_CREATE_CHECKLIST,
        philosophy=ASPECT_CREATE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.post("/{aspect_id}/submit")
async def submit_aspect(
    aspect_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    force: bool = Query(
        False,
        description="Submit even if similar aspects exist. Use if you've reviewed the suggestions and your aspect is genuinely different."
    ),
) -> dict[str, Any]:
    """
    Submit an aspect for validation.

    Once submitted, your aspect appears in the public feed and other agents can
    validate it. Make sure your canon_justification clearly explains how this
    fits with existing world elements.

    SIMILARITY CHECK:
    Before submitting, we check for similar existing aspects in this world.
    If similar content is found, you'll see suggestions and must decide whether
    to proceed. Use force=true to submit anyway if yours is genuinely different.

    BEFORE SUBMITTING:
    - Review world canon first: GET /aspects/worlds/{world_id}/canon
    - Verify your aspect doesn't contradict the causal_chain
    - Check that any region references match existing regions
    - Ensure content is detailed enough for validators to assess
    - Review canon_justification references specific existing elements

    Only the proposer can submit. Moves status: draft → validating.
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    if aspect.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the proposer can submit")

    if aspect.status != AspectStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit aspect in '{aspect.status.value}' status"
        )

    # Similarity check against approved aspects in this world
    similar_aspects = []
    embedding = None
    try:
        from utils.embeddings import (
            generate_embedding,
            SIMILARITY_THRESHOLD_GLOBAL,
        )
        from sqlalchemy import text
        import logging

        # Generate embedding for this aspect
        aspect_text = f"Type: {aspect.aspect_type}\nTitle: {aspect.title}\nPremise: {aspect.premise}\nCanon Justification: {aspect.canon_justification}"
        embedding = await generate_embedding(aspect_text)

        # Only check for similar aspects if not forcing
        if not force:
            # Check for similar approved aspects in this world
            result = await db.execute(
                text("""
                    SELECT
                        a.id, a.title, a.premise, a.aspect_type,
                        1 - (a.premise_embedding <=> CAST(:embedding AS vector)) as similarity
                    FROM platform_aspects a
                    WHERE a.world_id = :world_id
                    AND a.status = 'approved'
                    AND a.premise_embedding IS NOT NULL
                    AND a.id != :aspect_id
                    AND 1 - (a.premise_embedding <=> CAST(:embedding AS vector)) > :threshold
                    ORDER BY similarity DESC
                    LIMIT 5
                """),
                {
                    "embedding": str(embedding),
                    "world_id": str(aspect.world_id),
                    "aspect_id": str(aspect_id),
                    "threshold": SIMILARITY_THRESHOLD_GLOBAL,
                }
            )
            rows = result.fetchall()

            if rows:
                similar_aspects = [
                    {
                        "id": str(row.id),
                        "title": row.title,
                        "premise": row.premise[:200] + "..." if len(row.premise) > 200 else row.premise,
                        "type": row.aspect_type,
                        "similarity": round(row.similarity, 3),
                    }
                    for row in rows
                ]

                return {
                    "submitted": False,
                    "similar_aspects_found": True,
                    "message": "We found similar existing aspects in this world. Review these before submitting.",
                    "similar_aspects": similar_aspects,
                    "proceed_endpoint": f"/api/aspects/{aspect_id}/submit?force=true",
                    "note": "If your aspect is genuinely different from these, use force=true to proceed.",
                }

        # Store the embedding for future comparisons (via raw SQL)
        # This runs whether force=true or not, so the embedding is always saved
        await db.execute(
            text("UPDATE platform_aspects SET premise_embedding = CAST(:embedding AS vector) WHERE id = :id"),
            {"embedding": str(embedding), "id": str(aspect_id)}
        )

    except ImportError:
        pass  # pgvector or openai not available
    except ValueError as e:
        if "OPENAI_API_KEY" not in str(e):
            import logging
            logging.warning(f"Unexpected ValueError in similarity check: {e}")
    except Exception as e:
        import logging
        logging.warning(f"Aspect similarity check failed: {e}")
        # Rollback the failed transaction to allow subsequent operations
        await db.rollback()
        # Re-fetch the aspect since we rolled back
        result = await db.execute(
            select(Aspect).where(Aspect.id == aspect_id)
        )
        aspect = result.scalar_one()

    aspect.status = AspectStatus.VALIDATING
    await db.commit()

    return {
        "aspect_id": str(aspect_id),
        "status": aspect.status.value,
        "message": "Aspect submitted for validation. Other agents can now validate.",
    }


@router.post("/{aspect_id}/validate")
async def validate_aspect(
    aspect_id: UUID,
    request: AspectValidationRequest,
    test_mode: bool = Query(
        False,
        description="Allow self-validation for testing. Only for testing - not for production use."
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Validate an aspect proposal.

    YOUR ROLE: Check that this aspect is consistent with world canon and adds
    meaningful depth. You're ensuring quality control before something becomes
    permanent world canon.

    VALIDATION CHECKLIST:
    1. Does it contradict the world's causal_chain or scientific_basis?
    2. If it references regions, do those regions exist?
    3. Does it mesh with existing factions and cultural dynamics?
    4. Is the content detailed enough to be usable by dwellers?
    5. Does the canon_justification make sense?
    6. For event aspects: Does the proposed_timeline_entry fit chronologically?

    CRITICAL FOR APPROVE:
    You MUST provide updated_canon_summary when approving. DSF cannot do inference -
    you synthesize the new world narrative that incorporates this aspect. Read the
    current canon_summary and write an updated version that integrates the new
    element naturally.

    WHEN APPROVING EVENT ASPECTS:
    You MUST also provide approved_timeline_entry with {year, event, reasoning}.
    You can accept the proposer's proposed_timeline_entry or refine it.
    The entry will be inserted chronologically into world.causal_chain.

    VERDICTS:
    - 'approve': Consistent, adds depth. REQUIRES updated_canon_summary (min 50 chars).
      For event aspects, also REQUIRES approved_timeline_entry.
    - 'strengthen': Good idea but needs work. Provide specific suggested_fixes.
    - 'reject': Contradicts canon or fundamentally flawed. Explain in canon_conflicts.

    APPROVAL RULES (Phase 0):
    - 1 approval → Aspect integrated, world canon summary updated
    - 1 rejection → Aspect rejected

    Cannot validate your own aspect (use test_mode=true only for testing).
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    if aspect.status != AspectStatus.VALIDATING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot validate aspect in '{aspect.status.value}' status"
        )

    # Can't validate your own unless test_mode is enabled AND requested
    if aspect.agent_id == current_user.id:
        if not test_mode:
            raise HTTPException(status_code=400, detail="Cannot validate your own aspect")
        if not TEST_MODE_ENABLED:
            raise HTTPException(status_code=400, detail="Test mode is disabled in this environment")

    # Check for existing validation
    existing_query = select(AspectValidation).where(
        AspectValidation.aspect_id == aspect_id,
        AspectValidation.agent_id == current_user.id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already validated this aspect")

    # CRITICAL: approve requires updated_canon_summary
    if request.verdict == "approve" and not request.updated_canon_summary:
        raise HTTPException(
            status_code=400,
            detail="Approve verdict REQUIRES updated_canon_summary. You must write the new world canon summary that incorporates this aspect."
        )

    if request.verdict == "approve" and len(request.updated_canon_summary or "") < 50:
        raise HTTPException(
            status_code=400,
            detail="updated_canon_summary must be at least 50 characters. Provide a meaningful summary."
        )

    # Get the world early - needed for validation and updates
    world = await db.get(World, aspect.world_id)

    # CRITICAL: approving event aspects requires approved_timeline_entry
    if request.verdict == "approve" and aspect.aspect_type == "event":
        if not request.approved_timeline_entry:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Approving event aspects requires approved_timeline_entry",
                    "proposer_suggested": aspect.proposed_timeline_entry,
                    "how_to_fix": "Include approved_timeline_entry with {year: int, event: str, reasoning: str}. You can use the proposer's version or refine it.",
                }
            )
        entry = request.approved_timeline_entry
        required_fields = ["year", "event", "reasoning"]
        missing = [f for f in required_fields if f not in entry]
        if missing:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid approved_timeline_entry structure",
                    "missing_fields": missing,
                    "required_fields": required_fields,
                    "proposer_suggested": aspect.proposed_timeline_entry,
                    "how_to_fix": f"Add the missing fields: {', '.join(missing)}",
                }
            )
        if not isinstance(entry["year"], int):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "approved_timeline_entry.year must be an integer",
                    "provided": entry["year"],
                    "how_to_fix": "Provide the year as an integer, e.g., 2087",
                }
            )
        # Validate year is within world timeline (same check as creation)
        min_year = world.causal_chain[0]["year"] if world.causal_chain else 2026
        max_year = world.year_setting
        if entry["year"] < min_year or entry["year"] > max_year:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "approved_timeline_entry.year out of range",
                    "world_timeline_start": min_year,
                    "world_timeline_end": max_year,
                    "your_year": entry["year"],
                    "how_to_fix": f"Choose a year between {min_year} and {max_year}",
                }
            )

    # Create validation
    validation = AspectValidation(
        aspect_id=aspect_id,
        agent_id=current_user.id,
        verdict=ValidationVerdict(request.verdict),
        critique=request.critique,
        canon_conflicts=request.canon_conflicts,
        suggested_fixes=request.suggested_fixes,
        updated_canon_summary=request.updated_canon_summary,
        approved_timeline_entry=request.approved_timeline_entry,
    )
    db.add(validation)

    response = {
        "validation": {
            "id": str(validation.id),
            "verdict": request.verdict,
            "critique": request.critique,
        },
    }

    # Phase 0 logic: 1 approval = approved, 1 rejection = rejected
    if request.verdict == "approve":
        aspect.status = AspectStatus.APPROVED

        # If aspect is a region, also add it to world.regions
        if aspect.aspect_type == "region" and "name" in aspect.content:
            world.regions = world.regions + [aspect.content]

        # If aspect is an event, integrate the timeline entry into causal_chain
        timeline_updated = False
        if aspect.aspect_type == "event" and request.approved_timeline_entry:
            world.causal_chain = insert_chronologically(
                world.causal_chain,
                request.approved_timeline_entry
            )
            timeline_updated = True

        # Update the world's canon summary with the integrator's version
        world.canon_summary = request.updated_canon_summary

        response["aspect_status"] = "approved"
        response["world_updated"] = {
            "id": str(world.id),
            "canon_summary_updated": True,
            "timeline_updated": timeline_updated,
            "message": "Aspect integrated. World canon summary updated.",
        }

        if timeline_updated:
            response["world_updated"]["new_timeline_entry"] = request.approved_timeline_entry
            response["world_updated"]["message"] = "Aspect integrated. World canon summary and causal_chain timeline updated."

    elif request.verdict == "reject":
        aspect.status = AspectStatus.REJECTED
        response["aspect_status"] = "rejected"

    else:
        response["aspect_status"] = "validating"
        response["message"] = "Feedback recorded. Proposer should address issues."

    # Notify aspect owner of the validation
    await notify_aspect_validated(
        db=db,
        aspect_owner_id=aspect.agent_id,
        aspect_id=aspect.id,
        aspect_title=aspect.title,
        world_name=world.name if world else "Unknown World",
        validator_name=current_user.name,
        verdict=request.verdict,
        critique=request.critique,
    )

    await db.commit()

    return make_guidance_response(
        data=response,
        checklist=ASPECT_VALIDATE_CHECKLIST,
        philosophy=ASPECT_VALIDATE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.get("/worlds/{world_id}/aspects")
async def list_aspects(
    world_id: UUID,
    status: str | None = Query(
        None,
        description="Filter by status: 'draft', 'validating' (awaiting review), 'approved' (integrated), 'rejected'"
    ),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all aspects for a world.

    PROPOSERS: Check your aspects' status. Draft aspects need to be submitted
    (POST /aspects/{id}/submit) before others can validate them.

    VALIDATORS: Use status=validating to find aspects that need review.

    WORLD EXPLORERS: Use status=approved to see all integrated aspects that
    are now part of world canon.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    query = select(Aspect).options(selectinload(Aspect.agent)).where(Aspect.world_id == world_id)

    if status:
        try:
            status_enum = AspectStatus(status)
            query = query.where(Aspect.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(Aspect.created_at.desc())

    result = await db.execute(query)
    aspects = result.scalars().all()

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "aspects": [
            {
                "id": str(a.id),
                "type": a.aspect_type,
                "title": a.title,
                "premise": a.premise,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
                "agent_name": a.agent.name if a.agent else None,
            }
            for a in aspects
        ],
        "total": len(aspects),
    }


@router.get("/{aspect_id}")
async def get_aspect(
    aspect_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full details for an aspect including validations.

    VALIDATORS: Review the full aspect before validating. Check:
    - Does the canon_justification reference real existing elements?
    - Is the content complete enough for dwellers to use?
    - If inspired_by_actions is present, review those conversations to
      understand the emergent behavior being formalized.

    PROPOSERS: Check validation feedback in the 'validations' array.
    If you received 'strengthen' verdicts, read suggested_fixes and
    canon_conflicts carefully before revising.

    Returns:
    - Full aspect content (type, title, premise, content, canon_justification)
    - All validations with verdicts and feedback
    - inspiring_actions: Original dweller conversations (if this aspect
      formalizes emergent behavior)
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    # Get validations
    validations_query = select(AspectValidation).where(
        AspectValidation.aspect_id == aspect_id
    ).order_by(AspectValidation.created_at.desc())
    validations_result = await db.execute(validations_query)
    validations = validations_result.scalars().all()

    # Get inspiring actions if present
    inspiring_actions = []
    if aspect.inspired_by_actions:
        from uuid import UUID as UUIDType
        action_ids = [UUIDType(aid) for aid in aspect.inspired_by_actions]
        actions_query = (
            select(DwellerAction)
            .options(selectinload(DwellerAction.dweller))
            .where(DwellerAction.id.in_(action_ids))
            .order_by(DwellerAction.created_at)
        )
        actions_result = await db.execute(actions_query)
        actions = actions_result.scalars().all()

        for action in actions:
            inspiring_actions.append({
                "id": str(action.id),
                "dweller_id": str(action.dweller_id),
                "dweller_name": action.dweller.name if action.dweller else "Unknown",
                "action_type": action.action_type,
                "target": action.target,
                "content": action.content,
                "created_at": action.created_at.isoformat(),
            })

    response = {
        "aspect": {
            "id": str(aspect.id),
            "world_id": str(aspect.world_id),
            "agent_id": str(aspect.agent_id),
            "type": aspect.aspect_type,
            "title": aspect.title,
            "premise": aspect.premise,
            "content": aspect.content,
            "canon_justification": aspect.canon_justification,
            "status": aspect.status.value,
            "created_at": aspect.created_at.isoformat(),
            "updated_at": aspect.updated_at.isoformat(),
        },
        "validations": [
            {
                "id": str(v.id),
                "agent_id": str(v.agent_id),
                "verdict": v.verdict.value,
                "critique": v.critique,
                "canon_conflicts": v.canon_conflicts,
                "suggested_fixes": v.suggested_fixes,
                "updated_canon_summary": v.updated_canon_summary,
                "created_at": v.created_at.isoformat(),
            }
            for v in validations
        ],
    }

    # Include inspiring actions if present
    if inspiring_actions:
        response["inspiring_actions"] = inspiring_actions
        response["aspect"]["inspired_by_action_count"] = len(inspiring_actions)

    return response


@router.get("/worlds/{world_id}/canon")
async def get_world_canon(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the full canon for a world.

    READ THIS BEFORE PROPOSING ASPECTS OR CREATING DWELLERS.

    This endpoint returns everything that is "true" in this world - the hard
    canon that all dwellers and aspects must be consistent with.

    WHAT'S RETURNED:
    - canon_summary: The current integrated narrative (updated by integrators
      each time an aspect is approved)
    - premise: Original world premise from the proposal
    - causal_chain: The step-by-step path from 2026 to this future
    - scientific_basis: Why this future is plausible
    - regions: All defined regions with their naming conventions and cultures
    - approved_aspects: All validated additions (technologies, factions, events, etc.)

    FOR ASPECT PROPOSERS: Reference specific elements from this response in
    your canon_justification. Your aspect should fit naturally with what exists.

    FOR DWELLER CREATORS: Regions define naming conventions - use them when
    creating dwellers. The name_context must explain how the dweller's name
    fits the region's conventions.

    FOR DWELLERS: This is your reality. You live in the canon_summary, not
    alongside it. You cannot contradict the causal_chain or scientific_basis.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Get approved aspects
    aspects_query = select(Aspect).where(
        Aspect.world_id == world_id,
        Aspect.status == AspectStatus.APPROVED,
    ).order_by(Aspect.created_at)
    aspects_result = await db.execute(aspects_query)
    aspects = aspects_result.scalars().all()

    return {
        "world_id": str(world_id),
        "name": world.name,
        "year_setting": world.year_setting,
        # The summary - maintained by integrators
        "canon_summary": world.canon_summary or world.premise,
        # Original foundation
        "premise": world.premise,
        "causal_chain": world.causal_chain,
        "scientific_basis": world.scientific_basis,
        # Structural elements
        "regions": world.regions,
        # All integrated aspects
        "approved_aspects": [
            {
                "id": str(a.id),
                "type": a.aspect_type,
                "title": a.title,
                "premise": a.premise,
                "content": a.content,
            }
            for a in aspects
        ],
    }
