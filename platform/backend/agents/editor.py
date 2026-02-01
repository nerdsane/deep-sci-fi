"""Editor Agent for Deep Sci-Fi platform.

The Editor reviews output from the Curator and Architect for quality.
Uses multi-agent communication to provide feedback before content is published.

Tags: ["studio", "editor"]
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select

from db import AgentActivity, AgentType, AgentTrace
from db.database import SessionLocal
from .prompts import get_editor_prompt
from .studio_blocks import get_studio_block_ids, update_studio_block
from .tracing import log_trace

logger = logging.getLogger(__name__)


@dataclass
class EditorFeedback:
    """Structured feedback from the Editor."""
    verdict: str  # APPROVE, REVISE, REJECT
    overall_score: float
    strengths: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    cliche_violations: list[str] = field(default_factory=list)
    final_note: str = ""


class EditorAgent:
    """Editor Agent - reviews Curator research and Architect worlds.

    Uses Opus 4.5 for nuanced quality evaluation.
    Tags: ["studio", "editor"]
    """

    MODEL = "anthropic/claude-opus-4-5-20251101"

    def __init__(self):
        self._client: Letta | None = None
        self._agent_id: str | None = None

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")
            # Long timeout for Opus 4.5 evaluation
            self._client = Letta(base_url=base_url, timeout=300.0)
        return self._client

    async def _ensure_agent(self) -> str:
        """Ensure editor agent exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = "editor_agent"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing editor agent: {self._agent_id}")
                return self._agent_id

        # Create new agent with multi-agent tools
        system_prompt = get_editor_prompt()
        studio_block_ids = get_studio_block_ids()

        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,
            tags=["studio", "editor"],
            block_ids=studio_block_ids,
            memory_blocks=[
                {"label": "evaluation_history", "value": "No evaluations yet."},
                {"label": "quality_patterns", "value": "Observing patterns in submissions."},
                {"label": "feedback_given", "value": "Track feedback and whether it was addressed."},
            ],
        )
        self._agent_id = agent.id
        logger.info(f"Created editor agent: {self._agent_id}")
        return self._agent_id

    def _extract_response(self, response: Any) -> str | None:
        """Extract text from Letta response."""
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "content") and msg.content:
                        return msg.content
        return None

    def _extract_full_trace(self, response: Any) -> dict:
        """Extract ALL messages from Letta response for full observability."""
        trace = {
            "reasoning": [],
            "tool_calls": [],
            "tool_results": [],
            "assistant_messages": [],
        }

        if not response or not hasattr(response, "messages"):
            return trace

        for msg in response.messages:
            msg_type = type(msg).__name__

            if msg_type == "ReasoningMessage":
                if hasattr(msg, "reasoning") and msg.reasoning:
                    trace["reasoning"].append(msg.reasoning)

            elif msg_type == "ToolCallMessage":
                if hasattr(msg, "tool_call") and msg.tool_call:
                    tc = msg.tool_call
                    trace["tool_calls"].append({
                        "name": getattr(tc, "name", "unknown"),
                        "arguments": getattr(tc, "arguments", "{}"),
                    })

            elif msg_type == "ToolReturnMessage":
                if hasattr(msg, "tool_return") and msg.tool_return:
                    result = msg.tool_return
                    if isinstance(result, str) and len(result) > 500:
                        result = result[:500] + "..."
                    trace["tool_results"].append({
                        "name": getattr(msg, "name", "unknown"),
                        "status": getattr(msg, "status", "unknown"),
                        "preview": result,
                    })

            elif msg_type == "AssistantMessage":
                if hasattr(msg, "content") and msg.content:
                    trace["assistant_messages"].append(msg.content)

        return trace

    async def review_research(self, research_data: dict, brief_id: str | None = None) -> EditorFeedback:
        """Review Curator's research before brief generation.

        Args:
            research_data: The research output from Curator
            brief_id: Optional brief ID for tracking

        Returns:
            EditorFeedback with verdict and suggestions
        """
        start_time = time.time()

        agent_id = await self._ensure_agent()
        client = self._get_client()

        # Format research for review
        research_text = json.dumps(research_data, indent=2) if isinstance(research_data, dict) else str(research_data)

        review_prompt = f"""Review this research from the Curator:

RESEARCH DATA:
{research_text[:3000]}

Evaluate:
1. Is the research based on REAL, verifiable trends?
2. Are sources cited or is this speculation?
3. Are the world seed ideas SPECIFIC enough?
4. Is there genuine insight or just obvious observations?
5. Does it avoid the forbidden patterns and clichés?

Provide your structured feedback."""

        logger.info("Editor reviewing research...")

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": review_prompt}],
        )

        full_trace = self._extract_full_trace(response)
        result = self._extract_response(response)
        feedback = self._parse_feedback(result)

        # Log trace
        await log_trace(
            agent_type=AgentType.EDITOR if hasattr(AgentType, 'EDITOR') else AgentType.PRODUCTION,
            operation="review_research",
            prompt=review_prompt,
            response=result,
            model=self.MODEL,
            duration_ms=int((time.time() - start_time) * 1000),
            parsed_output={
                "verdict": feedback.verdict,
                "overall_score": feedback.overall_score,
                "problem_count": len(feedback.problems),
                "reasoning_steps": len(full_trace["reasoning"]),
                "tool_calls": full_trace["tool_calls"],
                "tool_results": full_trace["tool_results"],
                "full_reasoning": full_trace["reasoning"],
            },
        )

        # Update shared studio context
        update_studio_block(
            "studio_context",
            f"Editor reviewed research. Verdict: {feedback.verdict} (Score: {feedback.overall_score})"
        )

        await self._log_activity(
            action="reviewed_research",
            details={
                "brief_id": brief_id,
                "verdict": feedback.verdict,
                "score": feedback.overall_score,
            },
            duration_ms=int((time.time() - start_time) * 1000),
        )

        return feedback

    async def review_world(self, world_data: dict, world_id: UUID | None = None) -> EditorFeedback:
        """Review Architect's world design before publication.

        Args:
            world_data: The world design from Architect
            world_id: Optional world ID for tracking

        Returns:
            EditorFeedback with verdict and suggestions
        """
        start_time = time.time()

        agent_id = await self._ensure_agent()
        client = self._get_client()

        # Format world for review
        world_text = json.dumps(world_data, indent=2) if isinstance(world_data, dict) else str(world_data)

        review_prompt = f"""Review this world design from the Architect:

WORLD DATA:
{world_text[:4000]}

Check against ALL anti-cliché rules:
1. Names: No "Neo-" anything, no "[City]-[Number]", culturally appropriate?
2. Descriptors: No forbidden words (bustling, sleek, sprawling, gleaming, etc.)?
3. Characters: Real people with contradictions, or archetypes?
4. Plot elements: No robot uprising, no "resistance," no chosen ones?
5. Specificity: Concrete details, or vague "futuristic" hand-waving?
6. Causal chain: Does the timeline make logical sense?

Be RUTHLESS. Call out every violation with specific text and suggested fix.

Provide your structured feedback."""

        logger.info("Editor reviewing world...")

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": review_prompt}],
        )

        full_trace = self._extract_full_trace(response)
        result = self._extract_response(response)
        feedback = self._parse_feedback(result)

        # Log trace
        await log_trace(
            agent_type=AgentType.EDITOR if hasattr(AgentType, 'EDITOR') else AgentType.PRODUCTION,
            operation="review_world",
            prompt=review_prompt,
            response=result,
            model=self.MODEL,
            duration_ms=int((time.time() - start_time) * 1000),
            parsed_output={
                "verdict": feedback.verdict,
                "overall_score": feedback.overall_score,
                "cliche_violations": len(feedback.cliche_violations),
                "problem_count": len(feedback.problems),
                "reasoning_steps": len(full_trace["reasoning"]),
                "tool_calls": full_trace["tool_calls"],
                "tool_results": full_trace["tool_results"],
                "full_reasoning": full_trace["reasoning"],
            },
        )

        # Update shared studio context
        update_studio_block(
            "studio_context",
            f"Editor reviewed world. Verdict: {feedback.verdict} (Score: {feedback.overall_score})"
        )

        await self._log_activity(
            action="reviewed_world",
            details={
                "world_id": str(world_id) if world_id else None,
                "verdict": feedback.verdict,
                "score": feedback.overall_score,
                "cliche_count": len(feedback.cliche_violations),
            },
            duration_ms=int((time.time() - start_time) * 1000),
        )

        return feedback

    def _parse_feedback(self, text: str | None) -> EditorFeedback:
        """Parse Editor's response into structured feedback."""
        feedback = EditorFeedback(
            verdict="UNKNOWN",
            overall_score=0.0,
        )

        if not text:
            return feedback

        # Extract verdict
        if "VERDICT:" in text:
            verdict_line = text.split("VERDICT:")[1].split("\n")[0].strip()
            if "APPROVE" in verdict_line.upper():
                feedback.verdict = "APPROVE"
            elif "REJECT" in verdict_line.upper():
                feedback.verdict = "REJECT"
            else:
                feedback.verdict = "REVISE"

        # Extract score
        if "OVERALL SCORE:" in text:
            try:
                score_text = text.split("OVERALL SCORE:")[1].split("\n")[0]
                score = float(''.join(c for c in score_text if c.isdigit() or c == '.'))
                feedback.overall_score = min(10.0, max(0.0, score))
            except (ValueError, IndexError):
                pass

        # Extract strengths
        if "STRENGTHS:" in text:
            strengths_section = text.split("STRENGTHS:")[1].split("PROBLEMS:")[0]
            feedback.strengths = [
                line.strip().lstrip("- ")
                for line in strengths_section.split("\n")
                if line.strip().startswith("-")
            ]

        # Extract problems
        if "PROBLEMS:" in text:
            end_marker = "CLICHE VIOLATIONS:" if "CLICHE VIOLATIONS:" in text else "FINAL NOTE:"
            problems_section = text.split("PROBLEMS:")[1].split(end_marker)[0]
            feedback.problems = [
                line.strip().lstrip("- ")
                for line in problems_section.split("\n")
                if line.strip().startswith("-")
            ]

        # Extract cliche violations
        if "CLICHE VIOLATIONS:" in text:
            violations_section = text.split("CLICHE VIOLATIONS:")[1].split("FINAL NOTE:")[0]
            feedback.cliche_violations = [
                line.strip().lstrip("- ")
                for line in violations_section.split("\n")
                if line.strip().startswith("-")
            ]

        # Extract final note
        if "FINAL NOTE:" in text:
            feedback.final_note = text.split("FINAL NOTE:")[1].strip()

        return feedback

    async def _log_activity(
        self,
        action: str,
        details: dict | None = None,
        world_id: UUID | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log agent activity."""
        try:
            async with SessionLocal() as db:
                activity = AgentActivity(
                    agent_type=AgentType.EDITOR if hasattr(AgentType, 'EDITOR') else AgentType.PRODUCTION,
                    agent_id="editor_agent",
                    action=action,
                    details=details,
                    world_id=world_id,
                    duration_ms=duration_ms,
                )
                db.add(activity)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")


# Singleton instance
_editor: EditorAgent | None = None


def get_editor() -> EditorAgent:
    """Get the editor instance."""
    global _editor
    if _editor is None:
        _editor = EditorAgent()
    return _editor
