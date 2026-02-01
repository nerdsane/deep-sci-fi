"""Studio Agent Communication Tools.

Tools that enable Curator, Architect, and Editor to communicate directly,
request feedback, and collaborate autonomously.

Key principles from maximum agency architecture:
- Agents have tools to ACT, not just wait for input
- Direct agent-to-agent communication
- Structured feedback with clear verdicts
- Agents decide when to engage, not orchestrator
"""

import logging
import os
from typing import Any

from letta_client import Letta

logger = logging.getLogger(__name__)

# =============================================================================
# TOOL SOURCE CODE
# =============================================================================

# Shared tool for all studio agents
CHECK_INBOX_TOOL_SOURCE = '''
def check_inbox() -> dict:
    """Check your inbox for pending messages, feedback, and requests.

    Call this when you wake up or periodically to see what needs attention.
    Returns messages organized by priority and type.

    Returns:
        Dict with:
        - pending_feedback: Feedback waiting for your response
        - pending_requests: Review/clarification requests from other agents
        - unread_count: Total unread items
    """
    # Tool returns signal - orchestrator handles actual inbox retrieval
    return {
        "action": "check_inbox",
        "status": "checking",
    }
'''

SCHEDULE_STUDIO_ACTION_TOOL_SOURCE = '''
def schedule_studio_action(
    action_type: str,
    delay_minutes: int,
    context: str = "",
    target_agent: str = "",
) -> dict:
    """Schedule a future action for yourself.

    Use this to remind yourself to:
    - Check back on pending reviews
    - Follow up on unanswered requests
    - Do periodic research sweeps
    - Re-evaluate a piece of work after reflection

    Args:
        action_type: Type of action ("self_check", "follow_up", "research", "review")
        delay_minutes: Minutes from now to trigger (min 5, max 1440)
        context: What you want to remember when this triggers
        target_agent: Optional - who this relates to

    Returns:
        Dict with action_id and scheduled time
    """
    import uuid
    from datetime import datetime, timedelta

    if delay_minutes < 5:
        delay_minutes = 5
    if delay_minutes > 1440:
        delay_minutes = 1440

    trigger_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    return {
        "status": "scheduled",
        "action_id": str(uuid.uuid4()),
        "action_type": action_type,
        "trigger_at": trigger_at.isoformat(),
        "context": context,
        "target_agent": target_agent,
    }
'''

# Curator-specific tools
REQUEST_EDITORIAL_REVIEW_TOOL_SOURCE = '''
def request_editorial_review(
    content_type: str,
    content_id: str,
    summary: str,
    specific_questions: list = None,
) -> dict:
    """Request the Editor to review your work.

    Use this BEFORE finalizing briefs or research. The Editor's feedback
    will help you improve quality and avoid clichés.

    Args:
        content_type: What you're submitting ("research", "brief", "trend_analysis")
        content_id: Identifier for tracking (brief ID, etc.)
        summary: Brief summary of what you're submitting (1-2 sentences)
        specific_questions: Questions you want answered (optional list)

    Returns:
        Dict with review_request_id and status
    """
    import uuid
    from datetime import datetime

    if not content_type or not summary:
        return {
            "status": "failed",
            "error": "content_type and summary are required"
        }

    return {
        "status": "submitted",
        "review_request_id": str(uuid.uuid4()),
        "content_type": content_type,
        "content_id": content_id or str(uuid.uuid4()),
        "summary": summary,
        "questions": specific_questions or [],
        "submitted_at": datetime.utcnow().isoformat(),
        "to_agent": "editor",
    }
'''

RESPOND_TO_FEEDBACK_TOOL_SOURCE = '''
def respond_to_feedback(
    feedback_id: str,
    response_type: str,
    addressed_points: list,
    questions: list = None,
    revised_content_summary: str = "",
) -> dict:
    """Respond to feedback from the Editor.

    Use this after receiving feedback to:
    - Acknowledge and address the points raised
    - Ask clarifying questions if feedback is unclear
    - Explain why you disagree (respectfully) if appropriate

    Args:
        feedback_id: The feedback you're responding to
        response_type: "addressed", "question", "disagree"
        addressed_points: List of feedback points you've addressed
        questions: Clarifying questions (for "question" response)
        revised_content_summary: Brief summary of changes made

    Returns:
        Dict with response_id and delivery status
    """
    import uuid
    from datetime import datetime

    if not feedback_id or not response_type:
        return {
            "status": "failed",
            "error": "feedback_id and response_type are required"
        }

    return {
        "status": "sent",
        "response_id": str(uuid.uuid4()),
        "feedback_id": feedback_id,
        "response_type": response_type,
        "addressed_points": addressed_points or [],
        "questions": questions or [],
        "revised_content_summary": revised_content_summary,
        "sent_at": datetime.utcnow().isoformat(),
        "to_agent": "editor",
    }
'''

# Architect-specific tools
SUBMIT_FOR_REVIEW_TOOL_SOURCE = '''
def submit_for_review(
    world_id: str,
    world_name: str,
    stage: str,
    content_summary: str,
    concerns: list = None,
) -> dict:
    """Submit a world design for Editor review.

    Use this at key development stages to get feedback:
    - "concept": Initial world idea, before detailed design
    - "draft": Core world built, before polishing
    - "final": Ready for publication, final check

    Args:
        world_id: The world's ID
        world_name: The world's name
        stage: Development stage ("concept", "draft", "final")
        content_summary: Summary of current state (2-3 sentences)
        concerns: Areas you're uncertain about (optional list)

    Returns:
        Dict with submission_id and status
    """
    import uuid
    from datetime import datetime

    if not world_id or not stage:
        return {
            "status": "failed",
            "error": "world_id and stage are required"
        }

    valid_stages = ["concept", "draft", "final"]
    if stage not in valid_stages:
        return {
            "status": "failed",
            "error": f"stage must be one of: {valid_stages}"
        }

    return {
        "status": "submitted",
        "submission_id": str(uuid.uuid4()),
        "world_id": world_id,
        "world_name": world_name,
        "stage": stage,
        "content_summary": content_summary,
        "concerns": concerns or [],
        "submitted_at": datetime.utcnow().isoformat(),
        "to_agent": "editor",
    }
'''

REVISE_BASED_ON_FEEDBACK_TOOL_SOURCE = '''
def revise_based_on_feedback(
    world_id: str,
    feedback_id: str,
    addressed_issues: list,
    unaddressed_issues: list = None,
    rationale: str = "",
) -> dict:
    """Signal that you've revised work based on Editor feedback.

    Use this after making changes to let the Editor know you've
    addressed their concerns. Be specific about what you changed.

    Args:
        world_id: The world being revised
        feedback_id: The feedback being addressed
        addressed_issues: List of issues you fixed (be specific)
        unaddressed_issues: Issues you chose not to address (with reasons)
        rationale: Overall approach to the revision

    Returns:
        Dict with revision_id and status
    """
    import uuid
    from datetime import datetime

    if not world_id or not feedback_id:
        return {
            "status": "failed",
            "error": "world_id and feedback_id are required"
        }

    return {
        "status": "revised",
        "revision_id": str(uuid.uuid4()),
        "world_id": world_id,
        "feedback_id": feedback_id,
        "addressed_issues": addressed_issues or [],
        "unaddressed_issues": unaddressed_issues or [],
        "rationale": rationale,
        "revised_at": datetime.utcnow().isoformat(),
        "to_agent": "editor",
    }
'''

# Editor-specific tools
PROVIDE_FEEDBACK_TOOL_SOURCE = '''
def provide_feedback(
    target_agent: str,
    content_id: str,
    verdict: str,
    feedback_points: list,
    priority_fixes: list = None,
    praise_points: list = None,
) -> dict:
    """Provide structured feedback to another agent.

    Use this to send actionable feedback. Be specific and constructive.
    The receiving agent will see this and can respond.

    Args:
        target_agent: Who to send feedback to ("curator" or "architect")
        content_id: What content this is about (brief_id, world_id, etc.)
        verdict: Overall decision ("approve", "revise", "reject")
        feedback_points: List of specific feedback items (be constructive)
        priority_fixes: Must-fix issues for "revise" verdict (optional)
        praise_points: What works well - always include something positive

    Returns:
        Dict with feedback_id and delivery status
    """
    import uuid
    from datetime import datetime

    if not target_agent or not content_id or not verdict:
        return {
            "status": "failed",
            "error": "target_agent, content_id, and verdict are required"
        }

    valid_verdicts = ["approve", "revise", "reject"]
    if verdict not in valid_verdicts:
        return {
            "status": "failed",
            "error": f"verdict must be one of: {valid_verdicts}"
        }

    valid_agents = ["curator", "architect"]
    if target_agent not in valid_agents:
        return {
            "status": "failed",
            "error": f"target_agent must be one of: {valid_agents}"
        }

    return {
        "status": "sent",
        "feedback_id": str(uuid.uuid4()),
        "target_agent": target_agent,
        "content_id": content_id,
        "verdict": verdict,
        "feedback_points": feedback_points or [],
        "priority_fixes": priority_fixes or [],
        "praise_points": praise_points or [],
        "sent_at": datetime.utcnow().isoformat(),
    }
'''

REQUEST_CLARIFICATION_TOOL_SOURCE = '''
def request_clarification(
    target_agent: str,
    content_id: str,
    questions: list,
    context: str = "",
) -> dict:
    """Request clarification from another agent before providing feedback.

    Use when you need more information to make a good decision.
    The agent will respond, then you can provide proper feedback.

    Args:
        target_agent: Who to ask ("curator" or "architect")
        content_id: What content this is about
        questions: Specific questions (be clear about what you need)
        context: Why you're asking (helps them understand)

    Returns:
        Dict with request_id and status
    """
    import uuid
    from datetime import datetime

    if not target_agent or not questions:
        return {
            "status": "failed",
            "error": "target_agent and questions are required"
        }

    return {
        "status": "sent",
        "clarification_request_id": str(uuid.uuid4()),
        "target_agent": target_agent,
        "content_id": content_id or "",
        "questions": questions,
        "context": context,
        "sent_at": datetime.utcnow().isoformat(),
    }
'''

APPROVE_FOR_PUBLICATION_TOOL_SOURCE = '''
def approve_for_publication(
    content_type: str,
    content_id: str,
    quality_score: float,
    approval_notes: str = "",
) -> dict:
    """Give final approval for content to be published.

    This is the green light for briefs to go to Architect,
    or worlds to go live on the platform.

    Args:
        content_type: What you're approving ("brief", "world")
        content_id: The ID of the content
        quality_score: Your rating 0.0-1.0
        approval_notes: Any notes for the record

    Returns:
        Dict with approval_id and status
    """
    import uuid
    from datetime import datetime

    if not content_type or not content_id:
        return {
            "status": "failed",
            "error": "content_type and content_id are required"
        }

    if quality_score < 0:
        quality_score = 0.0
    if quality_score > 1:
        quality_score = 1.0

    return {
        "status": "approved",
        "approval_id": str(uuid.uuid4()),
        "content_type": content_type,
        "content_id": content_id,
        "quality_score": quality_score,
        "approval_notes": approval_notes,
        "approved_at": datetime.utcnow().isoformat(),
    }
'''


# =============================================================================
# TOOL MANAGEMENT
# =============================================================================

# Cache for tool IDs
_studio_tool_ids: dict[str, str] = {}


def get_letta_client() -> Letta:
    """Get Letta client."""
    base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
    return Letta(base_url=base_url, timeout=120.0)


async def ensure_studio_tools() -> dict[str, str]:
    """Ensure all studio communication tools exist and return their IDs.

    Returns:
        Dict mapping tool name to tool ID
    """
    global _studio_tool_ids

    if _studio_tool_ids:
        return _studio_tool_ids

    client = get_letta_client()

    # Tool definitions
    tool_sources = {
        "check_inbox": CHECK_INBOX_TOOL_SOURCE,
        "schedule_studio_action": SCHEDULE_STUDIO_ACTION_TOOL_SOURCE,
        "request_editorial_review": REQUEST_EDITORIAL_REVIEW_TOOL_SOURCE,
        "respond_to_feedback": RESPOND_TO_FEEDBACK_TOOL_SOURCE,
        "submit_for_review": SUBMIT_FOR_REVIEW_TOOL_SOURCE,
        "revise_based_on_feedback": REVISE_BASED_ON_FEEDBACK_TOOL_SOURCE,
        "provide_feedback": PROVIDE_FEEDBACK_TOOL_SOURCE,
        "request_clarification": REQUEST_CLARIFICATION_TOOL_SOURCE,
        "approve_for_publication": APPROVE_FOR_PUBLICATION_TOOL_SOURCE,
    }

    # Get existing tools
    existing_tools = client.tools.list()
    existing_by_name = {t.name: t for t in existing_tools}

    for name, source_code in tool_sources.items():
        if name in existing_by_name:
            _studio_tool_ids[name] = existing_by_name[name].id
            logger.info(f"Found existing studio tool: {name}")
        else:
            # Create the tool
            tool = client.tools.create(
                source_code=source_code,
                name=name,
            )
            _studio_tool_ids[name] = tool.id
            logger.info(f"Created studio tool: {name} ({tool.id})")

    return _studio_tool_ids


async def get_curator_tool_ids() -> list[str]:
    """Get tool IDs for Curator agent.

    Curator tools:
    - check_inbox: See pending feedback
    - schedule_studio_action: Plan future actions
    - request_editorial_review: Ask Editor to review work
    - respond_to_feedback: Respond to Editor feedback
    """
    tools = await ensure_studio_tools()
    return [
        tools["check_inbox"],
        tools["schedule_studio_action"],
        tools["request_editorial_review"],
        tools["respond_to_feedback"],
    ]


async def get_architect_tool_ids() -> list[str]:
    """Get tool IDs for Architect agent.

    Architect tools:
    - check_inbox: See pending feedback
    - schedule_studio_action: Plan future actions
    - submit_for_review: Submit world for Editor review
    - revise_based_on_feedback: Signal revision complete
    """
    tools = await ensure_studio_tools()
    return [
        tools["check_inbox"],
        tools["schedule_studio_action"],
        tools["submit_for_review"],
        tools["revise_based_on_feedback"],
    ]


async def get_editor_tool_ids() -> list[str]:
    """Get tool IDs for Editor agent.

    Editor tools:
    - check_inbox: See pending review requests
    - schedule_studio_action: Plan future actions
    - provide_feedback: Send feedback to Curator/Architect
    - request_clarification: Ask questions before deciding
    - approve_for_publication: Green light for publication
    """
    tools = await ensure_studio_tools()
    return [
        tools["check_inbox"],
        tools["schedule_studio_action"],
        tools["provide_feedback"],
        tools["request_clarification"],
        tools["approve_for_publication"],
    ]
