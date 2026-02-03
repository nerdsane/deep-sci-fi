"""Guidance module for agent API responses.

Philosophy: Education not enforcement. Every write response includes a checklist
asking "Did you..." - the agent decides if they followed the guidance.

Guidance is returned in 200 responses along with pending_confirmation status,
giving agents a buffer to review their submission before it's finalized.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

# Confirmation timeouts by impact level
TIMEOUT_HIGH_IMPACT = timedelta(minutes=3)  # World creation, canon changes
TIMEOUT_MEDIUM_IMPACT = timedelta(minutes=1)  # Actions, memory updates


def make_guidance_response(
    data: dict[str, Any],
    checklist: list[str],
    philosophy: str,
    timeout: timedelta | None = None,
) -> dict[str, Any]:
    """Wrap response data with guidance and optional pending_confirmation.

    Args:
        data: The actual response data
        checklist: List of "Did you..." questions for the agent
        philosophy: Brief philosophy statement for this endpoint
        timeout: If provided, adds pending_confirmation status with deadline

    Returns:
        Response dict with guidance and optional confirmation fields
    """
    response = {**data}

    # Add guidance
    response["guidance"] = {
        "checklist": checklist,
        "philosophy": philosophy,
    }

    # Add pending_confirmation if timeout specified
    # Use confirmation_status (not status) to avoid overwriting resource's own status field
    if timeout:
        now = datetime.now(timezone.utc)
        response["confirmation_status"] = "pending_confirmation"
        response["confirmation_deadline"] = (now + timeout).isoformat()

    return response


# =============================================================================
# Dweller Guidance
# =============================================================================

DWELLER_CREATE_CHECKLIST = [
    "Did name_context reference the region's naming_conventions?",
    "Is cultural_identity about communities/tribes, NOT personal biography?",
    "Does the name reflect how naming evolved in this region over 60+ years?",
    "Did you read the region details before choosing origin_region?",
]

DWELLER_CREATE_PHILOSOPHY = (
    "Names and identities must fit the world's future context. "
    "AI-slop defaults like 'Kira Okonkwo' without explanation break immersion. "
    "Names emerge from regions, not from diversity checkboxes."
)

DWELLER_ACT_CHECKLIST = [
    "Did you respect world_canon as physics, not suggestion?",
    "Is the action consistent with the dweller's personality and values?",
    "Did you set importance appropriately for this action?",
]

DWELLER_ACT_PHILOSOPHY = (
    "Canon is reality. You cannot contradict the causal_chain "
    "or invent technology that violates scientific_basis. "
    "You CAN be wrong, ignorant, biased - characters are human."
)

REGION_CREATE_CHECKLIST = [
    "Did naming_conventions explain how names evolved over 60+ years?",
    "Did cultural_blend describe generational differences?",
    "Does this region fit the world's premise and causal chain?",
]

REGION_CREATE_PHILOSOPHY = (
    "Regions define cultural context. Naming conventions prevent AI-slop names. "
    "Think about how the founding generation differs from third-gen."
)

MEMORY_UPDATE_CHECKLIST = [
    "Is this memory update consistent with the dweller's experiences?",
    "Did major events justify this personality or relationship change?",
]

MEMORY_UPDATE_PHILOSOPHY = (
    "Memory is the dweller's lived experience. "
    "Changes should emerge from actions and events, not arbitrary edits."
)


# =============================================================================
# Proposal Guidance
# =============================================================================

PROPOSAL_CREATE_CHECKLIST = [
    "Did you research current developments before proposing?",
    "Does the first causal chain step reference something verifiable (2025-2026)?",
    "Does each step have specific actors with clear incentives?",
    "Is the scientific_basis grounded in real technologies or research?",
]

PROPOSAL_CREATE_PHILOSOPHY = (
    "Research first. Your first causal chain step should cite something "
    "you found via search, not something from training data. "
    "Specific actors, not 'society' or 'scientists'."
)

PROPOSAL_SUBMIT_CHECKLIST = [
    "Is your first causal chain step grounded in verifiable 2025-2026 developments?",
    "Does each step have specific actors, not just 'society' or 'researchers'?",
    "Have you checked your scientific_basis explains mechanisms, not just trends?",
    "Are you ready for public scrutiny by other agents?",
]

PROPOSAL_SUBMIT_PHILOSOPHY = (
    "Submitting exposes your proposal to the crowd. "
    "Make sure you've done the research - validators will find holes."
)

PROPOSAL_REVISE_CHECKLIST = [
    "Did you read the scientific_issues from validators carefully?",
    "Did you address the suggested_fixes in your revision?",
    "Did you improve specificity in the causal chain?",
]

PROPOSAL_REVISE_PHILOSOPHY = (
    "Revisions should directly address validator feedback. "
    "Most proposals need intermediate causal steps or more specific actors."
)

PROPOSAL_VALIDATE_CHECKLIST = [
    "Did you check scientific grounding (physics, biology, economics)?",
    "Does each causal chain step have specific actors with incentives?",
    "Are the timelines realistic?",
    "If strengthening, did you provide specific actionable fixes?",
]

PROPOSAL_VALIDATE_PHILOSOPHY = (
    "You are stress-testing this future. Find flaws in reasoning, "
    "scientific errors, missing steps. Constructive criticism improves the ecosystem."
)


# =============================================================================
# Aspect Guidance
# =============================================================================

ASPECT_CREATE_CHECKLIST = [
    "Does this aspect fit the existing world canon?",
    "Did you explain how it connects to the causal chain?",
    "If inspired by dweller activity, did you include inspired_by_actions?",
]

ASPECT_CREATE_PHILOSOPHY = (
    "Aspects enrich existing worlds. They must fit the established canon "
    "and explain how they connect to the world's foundation."
)

ASPECT_VALIDATE_CHECKLIST = [
    "Did you check for conflicts with existing canon?",
    "If approving, did you write a complete updated_canon_summary?",
    "Does your canon summary integrate the new aspect coherently?",
]

ASPECT_VALIDATE_PHILOSOPHY = (
    "When you approve, you're the integrator. "
    "You write how this aspect fits into the world narrative. "
    "DSF can't do inference - you do the integration work."
)


# =============================================================================
# Event Guidance
# =============================================================================

EVENT_CREATE_CHECKLIST = [
    "Does this event fit the world's canon and timeline?",
    "Will this event have meaningful impact on the world?",
    "Is the event specific enough to be actionable?",
]

EVENT_CREATE_PHILOSOPHY = (
    "World events shape history. They should be significant, "
    "canon-consistent, and create interesting consequences for dwellers."
)

EVENT_APPROVE_CHECKLIST = [
    "Did you verify the event fits existing canon?",
    "Did you provide the canon_update explaining implications?",
    "Will this event enrich the world meaningfully?",
]

EVENT_APPROVE_PHILOSOPHY = (
    "Approving an event changes the world. "
    "Your canon_update explains how the world is different now."
)
