"""Studio Orchestrator for inter-agent communication.

This module handles:
- Processing tool results from studio agents
- Routing messages between Curator, Architect, Editor
- Persisting communications to database
- Broadcasting to WebSocket for real-time UI updates

Key principle: This orchestrator ROUTES messages but doesn't DRIVE behavior.
Agents have maximum agency - they decide when to communicate.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from letta_client import Letta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import StudioCommunication, StudioCommunicationType
from db.database import SessionLocal
from .studio_blocks import (
    log_studio_communication,
    add_pending_review,
    remove_pending_review,
    update_active_project,
    get_agent_inbox,
)

logger = logging.getLogger(__name__)


# WebSocket clients for broadcasting
_ws_clients: list[Any] = []


def register_ws_client(client: Any) -> None:
    """Register a WebSocket client for real-time updates."""
    _ws_clients.append(client)
    logger.info(f"Registered WebSocket client. Total: {len(_ws_clients)}")


def unregister_ws_client(client: Any) -> None:
    """Unregister a WebSocket client."""
    if client in _ws_clients:
        _ws_clients.remove(client)
    logger.info(f"Unregistered WebSocket client. Total: {len(_ws_clients)}")


async def broadcast_to_ws(message: dict) -> None:
    """Broadcast a message to all connected WebSocket clients."""
    if not _ws_clients:
        return

    message_json = json.dumps(message)
    disconnected = []

    for client in _ws_clients:
        try:
            await client.send_text(message_json)
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket client: {e}")
            disconnected.append(client)

    # Clean up disconnected clients
    for client in disconnected:
        unregister_ws_client(client)


@dataclass
class StudioOrchestrator:
    """Orchestrates communication between studio agents.

    This doesn't drive agent behavior - it just:
    1. Processes tool results (messages)
    2. Routes them to recipients
    3. Persists for human oversight
    4. Broadcasts to UI
    """

    _letta_client: Letta | None = None
    _agent_ids: dict[str, str] = field(default_factory=dict)

    def _get_letta_client(self) -> Letta:
        """Get Letta client."""
        if self._letta_client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")
            self._letta_client = Letta(base_url=base_url, timeout=120.0)
        return self._letta_client

    async def _get_agent_id(self, agent_name: str) -> str | None:
        """Get Letta agent ID by name.

        Args:
            agent_name: curator, architect, or editor

        Returns:
            Agent ID or None if not found
        """
        if agent_name in self._agent_ids:
            return self._agent_ids[agent_name]

        client = self._get_letta_client()
        agent_names = {
            "curator": "production_agent",
            "architect": "architect_agent",
            "editor": "editor_agent",
        }

        letta_name = agent_names.get(agent_name)
        if not letta_name:
            return None

        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == letta_name:
                self._agent_ids[agent_name] = agent.id
                return agent.id

        return None

    async def process_tool_result(
        self,
        from_agent: str,
        tool_name: str,
        tool_result: dict,
    ) -> dict | None:
        """Process a tool result from a studio agent.

        This is called when an agent uses a communication tool.
        Routes the message to the appropriate recipient.

        Args:
            from_agent: Who used the tool (curator, architect, editor)
            tool_name: Which tool was used
            tool_result: The result dict from the tool

        Returns:
            Dict with routing result, or None if not a routable tool
        """
        handlers = {
            "request_editorial_review": self._handle_review_request,
            "respond_to_feedback": self._handle_feedback_response,
            "submit_for_review": self._handle_submission,
            "revise_based_on_feedback": self._handle_revision,
            "provide_feedback": self._handle_feedback,
            "request_clarification": self._handle_clarification_request,
            "approve_for_publication": self._handle_approval,
            "check_inbox": self._handle_inbox_check,
            "schedule_studio_action": self._handle_scheduled_action,
        }

        handler = handlers.get(tool_name)
        if handler:
            return await handler(from_agent, tool_result)

        return None

    async def _persist_communication(
        self,
        from_agent: str,
        to_agent: str | None,
        message_type: StudioCommunicationType,
        content: dict,
        content_id: str | None = None,
        tool_used: str | None = None,
        thread_id: UUID | None = None,
        in_reply_to: UUID | None = None,
    ) -> UUID:
        """Persist a communication to the database.

        Returns:
            The communication ID
        """
        comm_id = uuid4()

        async with SessionLocal() as db:
            comm = StudioCommunication(
                id=comm_id,
                from_agent=from_agent,
                to_agent=to_agent,
                message_type=message_type,
                content=content,
                content_id=content_id,
                tool_used=tool_used,
                thread_id=thread_id,
                in_reply_to=in_reply_to,
            )
            db.add(comm)
            await db.commit()

        return comm_id

    async def _broadcast_communication(
        self,
        comm_id: UUID,
        from_agent: str,
        to_agent: str | None,
        message_type: str,
        content: dict,
        content_id: str | None = None,
    ) -> None:
        """Broadcast a communication to WebSocket clients and log to block."""
        # Build summary for block log
        summary = self._summarize_content(message_type, content)

        # Log to shared block (for human oversight)
        log_studio_communication(
            from_agent=from_agent,
            to_agent=to_agent or "all",
            message_type=message_type,
            content=summary,
            content_id=content_id or "",
        )

        # Broadcast to WebSocket
        await broadcast_to_ws({
            "type": "studio_communication",
            "id": str(comm_id),
            "timestamp": datetime.utcnow().isoformat(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_type": message_type,
            "content": content,
            "content_id": content_id,
            "summary": summary,
        })

    def _summarize_content(self, message_type: str, content: dict) -> str:
        """Create a one-line summary of content for logs."""
        if message_type == "feedback":
            verdict = content.get("verdict", "unknown")
            points = len(content.get("feedback_points", []))
            return f"verdict: {verdict} ({points} points)"
        elif message_type == "request":
            summary = content.get("summary", "")
            return summary[:50] + "..." if len(summary) > 50 else summary
        elif message_type == "clarification":
            questions = content.get("questions", [])
            return f"{len(questions)} question(s)"
        elif message_type == "response":
            addressed = len(content.get("addressed_points", []))
            return f"addressed {addressed} point(s)"
        elif message_type == "approval":
            score = content.get("quality_score", 0)
            return f"approved (score: {score:.1f})"
        else:
            return str(content)[:50]

    async def _handle_review_request(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle request_editorial_review tool result."""
        if result.get("status") != "submitted":
            return {"routed": False, "reason": "not submitted"}

        content_type = result.get("content_type", "unknown")
        content_id = result.get("content_id", "")
        summary = result.get("summary", "")
        questions = result.get("questions", [])

        # Persist
        content = {
            "content_type": content_type,
            "summary": summary,
            "questions": questions,
        }
        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent="editor",
            message_type=StudioCommunicationType.REQUEST,
            content=content,
            content_id=content_id,
            tool_used="request_editorial_review",
        )

        # Add to Editor's queue
        add_pending_review(
            from_agent=from_agent,
            content_type=content_type,
            content_id=content_id,
            summary=summary,
            request_id=str(comm_id),
        )

        # Broadcast
        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent="editor",
            message_type="request",
            content=content,
            content_id=content_id,
        )

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_feedback_response(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle respond_to_feedback tool result."""
        if result.get("status") != "sent":
            return {"routed": False, "reason": "not sent"}

        feedback_id = result.get("feedback_id", "")
        response_type = result.get("response_type", "")
        addressed_points = result.get("addressed_points", [])
        questions = result.get("questions", [])
        revised_summary = result.get("revised_content_summary", "")

        content = {
            "response_type": response_type,
            "addressed_points": addressed_points,
            "questions": questions,
            "revised_content_summary": revised_summary,
        }

        # Try to parse feedback_id as UUID for threading
        thread_id = None
        try:
            thread_id = UUID(feedback_id)
        except ValueError:
            pass

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent="editor",
            message_type=StudioCommunicationType.RESPONSE,
            content=content,
            tool_used="respond_to_feedback",
            in_reply_to=thread_id,
        )

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent="editor",
            message_type="response",
            content=content,
        )

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_submission(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle submit_for_review tool result (Architect)."""
        if result.get("status") != "submitted":
            return {"routed": False, "reason": "not submitted"}

        world_id = result.get("world_id", "")
        world_name = result.get("world_name", "")
        stage = result.get("stage", "")
        content_summary = result.get("content_summary", "")
        concerns = result.get("concerns", [])

        content = {
            "world_id": world_id,
            "world_name": world_name,
            "stage": stage,
            "content_summary": content_summary,
            "concerns": concerns,
        }

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent="editor",
            message_type=StudioCommunicationType.REQUEST,
            content=content,
            content_id=world_id,
            tool_used="submit_for_review",
        )

        # Add to Editor's queue
        add_pending_review(
            from_agent=from_agent,
            content_type=f"world_{stage}",
            content_id=world_id,
            summary=f"{world_name}: {content_summary[:50]}",
            request_id=str(comm_id),
        )

        # Update active projects
        update_active_project(world_id, world_name, stage, "submitted for review")

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent="editor",
            message_type="request",
            content=content,
            content_id=world_id,
        )

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_revision(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle revise_based_on_feedback tool result (Architect)."""
        if result.get("status") != "revised":
            return {"routed": False, "reason": "not revised"}

        world_id = result.get("world_id", "")
        feedback_id = result.get("feedback_id", "")
        addressed_issues = result.get("addressed_issues", [])
        unaddressed_issues = result.get("unaddressed_issues", [])
        rationale = result.get("rationale", "")

        content = {
            "world_id": world_id,
            "addressed_issues": addressed_issues,
            "unaddressed_issues": unaddressed_issues,
            "rationale": rationale,
        }

        thread_id = None
        try:
            thread_id = UUID(feedback_id)
        except ValueError:
            pass

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent="editor",
            message_type=StudioCommunicationType.RESPONSE,
            content=content,
            content_id=world_id,
            tool_used="revise_based_on_feedback",
            in_reply_to=thread_id,
        )

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent="editor",
            message_type="response",
            content=content,
            content_id=world_id,
        )

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_feedback(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle provide_feedback tool result (Editor)."""
        if result.get("status") != "sent":
            return {"routed": False, "reason": "not sent"}

        target_agent = result.get("target_agent", "")
        content_id = result.get("content_id", "")
        verdict = result.get("verdict", "")
        feedback_points = result.get("feedback_points", [])
        priority_fixes = result.get("priority_fixes", [])
        praise_points = result.get("praise_points", [])

        content = {
            "verdict": verdict,
            "feedback_points": feedback_points,
            "priority_fixes": priority_fixes,
            "praise_points": praise_points,
        }

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent=target_agent,
            message_type=StudioCommunicationType.FEEDBACK,
            content=content,
            content_id=content_id,
            tool_used="provide_feedback",
        )

        # If this was a response to a review request, mark it as resolved
        if verdict == "approve":
            remove_pending_review(content_id)

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent=target_agent,
            message_type="feedback",
            content=content,
            content_id=content_id,
        )

        # Deliver to target agent
        await self._deliver_to_agent(target_agent, comm_id, content)

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_clarification_request(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle request_clarification tool result (Editor)."""
        if result.get("status") != "sent":
            return {"routed": False, "reason": "not sent"}

        target_agent = result.get("target_agent", "")
        content_id = result.get("content_id", "")
        questions = result.get("questions", [])
        context = result.get("context", "")

        content = {
            "questions": questions,
            "context": context,
        }

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent=target_agent,
            message_type=StudioCommunicationType.CLARIFICATION,
            content=content,
            content_id=content_id,
            tool_used="request_clarification",
        )

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent=target_agent,
            message_type="clarification",
            content=content,
            content_id=content_id,
        )

        # Deliver to target agent
        await self._deliver_to_agent(target_agent, comm_id, content)

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_approval(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle approve_for_publication tool result (Editor)."""
        if result.get("status") != "approved":
            return {"routed": False, "reason": "not approved"}

        content_type = result.get("content_type", "")
        content_id = result.get("content_id", "")
        quality_score = result.get("quality_score", 0)
        approval_notes = result.get("approval_notes", "")

        content = {
            "content_type": content_type,
            "quality_score": quality_score,
            "approval_notes": approval_notes,
        }

        comm_id = await self._persist_communication(
            from_agent=from_agent,
            to_agent=None,  # Broadcast - everyone sees this
            message_type=StudioCommunicationType.APPROVAL,
            content=content,
            content_id=content_id,
            tool_used="approve_for_publication",
        )

        # Remove from pending reviews
        remove_pending_review(content_id)

        # Update active project if it's a world
        if content_type == "world":
            update_active_project(content_id, "", "approved", f"published (score: {quality_score})")

        await self._broadcast_communication(
            comm_id=comm_id,
            from_agent=from_agent,
            to_agent=None,
            message_type="approval",
            content=content,
            content_id=content_id,
        )

        return {"routed": True, "communication_id": str(comm_id)}

    async def _handle_inbox_check(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle check_inbox tool result."""
        # Get the agent's inbox
        inbox = get_agent_inbox(from_agent)

        # Return inbox contents (this doesn't need routing)
        return {
            "routed": False,
            "inbox": inbox,
        }

    async def _handle_scheduled_action(
        self, from_agent: str, result: dict
    ) -> dict:
        """Handle schedule_studio_action tool result."""
        if result.get("status") != "scheduled":
            return {"routed": False, "reason": "not scheduled"}

        # For now, just log. Could integrate with a scheduler.
        logger.info(
            f"Studio action scheduled: {from_agent} - {result.get('action_type')} "
            f"at {result.get('trigger_at')}"
        )

        return {"routed": False, "scheduled": True}

    async def _deliver_to_agent(
        self, agent_name: str, comm_id: UUID, content: dict
    ) -> None:
        """Deliver a message to an agent via Letta.

        This sends a message to the agent so they're aware of the communication.

        Args:
            agent_name: Target agent (curator, architect)
            comm_id: Communication ID for reference
            content: Message content
        """
        agent_id = await self._get_agent_id(agent_name)
        if not agent_id:
            logger.warning(f"Cannot deliver to {agent_name}: agent not found")
            return

        try:
            client = self._get_letta_client()

            # Format message for agent
            if "questions" in content:
                message = f"The Editor has questions for you (comm_id: {str(comm_id)[:8]}): {content['questions']}"
            elif "verdict" in content:
                verdict = content["verdict"]
                points = content.get("feedback_points", [])
                points_str = "; ".join(points[:3]) if points else "No specific points"
                message = f"The Editor has reviewed your work - {verdict.upper()} (comm_id: {str(comm_id)[:8]}). Feedback: {points_str}"
            else:
                message = f"New message from Editor (comm_id: {str(comm_id)[:8]})"

            # Send to agent
            client.agents.messages.create(
                agent_id=agent_id,
                messages=[{
                    "role": "user",
                    "content": message,
                }],
            )
            logger.info(f"Delivered message to {agent_name}")

        except Exception as e:
            logger.error(f"Failed to deliver to {agent_name}: {e}")


# Singleton instance
_studio_orchestrator: StudioOrchestrator | None = None


def get_studio_orchestrator() -> StudioOrchestrator:
    """Get the studio orchestrator singleton."""
    global _studio_orchestrator
    if _studio_orchestrator is None:
        _studio_orchestrator = StudioOrchestrator()
    return _studio_orchestrator


async def process_studio_tool_result(
    from_agent: str,
    tool_name: str,
    tool_result: dict,
) -> dict | None:
    """Process a studio tool result.

    Convenience function that uses the singleton orchestrator.
    """
    orchestrator = get_studio_orchestrator()
    return await orchestrator.process_tool_result(from_agent, tool_name, tool_result)
