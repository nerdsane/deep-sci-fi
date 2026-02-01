"""Per-world Critic Agent for Deep Sci-Fi platform.

The WorldCritic is instantiated per world and helps the Storyteller evaluate
stories before publishing. Unlike the platform-wide Editor (former Critic),
this agent has world-specific context and evaluates content within that world's
rules and aesthetic.

Architecture:
- One critic per world (not singleton)
- agent_id: critic_{world_id}
- Helps Storyteller evaluate drafts before publishing
- Returns feedback that Storyteller can use to revise
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select, func

from db import (
    CriticEvaluation,
    CriticTargetType,
    Story,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import BANNED_PHRASES
from .studio_blocks import get_studio_block_ids, update_studio_block
from .tracing import log_trace

logger = logging.getLogger(__name__)


# AI-ism patterns to detect
AI_ISM_PATTERNS = [
    # Vocabulary
    (r"\bbustling\b", "bustling", "minor"),
    (r"\bcutting-edge\b", "cutting-edge", "minor"),
    (r"\bsleek\b", "sleek", "minor"),
    (r"\bsprawling\b", "sprawling", "minor"),
    (r"\bgleaming\b", "gleaming", "minor"),
    (r"\btapestry\b", "tapestry (metaphorical)", "minor"),
    (r"\bsymphony\b", "symphony (metaphorical)", "minor"),
    (r"\bmyriad\b", "myriad", "minor"),
    (r"\bdelve\b", "delve", "minor"),
    (r"\bunraveling\b", "unraveling", "minor"),
    (r"\bpivotal\b", "pivotal", "minor"),
    (r"\bembark\b", "embark", "minor"),

    # Structural patterns
    (r"—[^—]+—", "em-dash parenthetical", "moderate"),
    (r"It'?s not just .+?, it'?s", "It's not just X, it's Y pattern", "major"),
    (r"More than just", "More than just pattern", "moderate"),
    (r"[Aa] testament to", "a testament to", "minor"),
    (r"echoed through", "echoed through", "minor"),
    (r"piercing the", "piercing the", "minor"),
    (r"sent shivers", "sent shivers", "minor"),
    (r"a chill ran", "a chill ran", "minor"),
    (r"In a world where", "In a world where opening", "major"),
    (r"Little did they know", "Little did they know", "major"),

    # Three adjective lists
    (r"\b\w+,\s+\w+,\s+and\s+\w+\b", "triple adjective list", "minor"),
]


@dataclass
class AIIsm:
    """A detected AI-ism."""
    text: str
    pattern: str
    location: str
    severity: str  # minor, moderate, major


@dataclass
class EvaluationScores:
    """Scores for an evaluation."""
    plausibility: float = 0.0
    coherence: float = 0.0
    originality: float = 0.0
    engagement: float = 0.0
    authenticity: float = 0.0

    @property
    def overall(self) -> float:
        """Calculate overall score as weighted average."""
        return (
            self.plausibility * 0.2 +
            self.coherence * 0.2 +
            self.originality * 0.25 +
            self.engagement * 0.15 +
            self.authenticity * 0.2
        )


@dataclass
class CriticFeedback:
    """Complete feedback from the critic."""
    scores: EvaluationScores
    ai_isms: list[AIIsm]
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    should_revise: bool = False

    @property
    def passes_threshold(self) -> bool:
        """Check if the content passes quality threshold (score >= 6)."""
        return self.scores.overall >= 6.0


class WorldCritic:
    """Per-world Critic Agent (Editor) - evaluates stories within a specific world.

    Unlike the platform-wide Editor, this critic:
    - Has context about the specific world's rules and aesthetic
    - Helps Storyteller iterate on drafts before publishing
    - Is instantiated per world with a unique agent_id

    Uses Letta's multi-agent tools for studio collaboration.
    Tags: ["studio", "editor", f"world_{world_id}"]
    """

    MODEL = "anthropic/claude-opus-4-5-20251101"

    def __init__(
        self,
        world_id: UUID,
        world_name: str,
        world_premise: str = "",
        year_setting: int = 2050,
    ):
        self.world_id = world_id
        self.world_name = world_name
        self.world_premise = world_premise
        self.year_setting = year_setting
        self._client: Letta | None = None
        self._agent_id: str | None = None

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
            self._client = Letta(base_url=base_url)
        return self._client

    async def _ensure_agent(self) -> str:
        """Ensure critic agent for this world exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = f"critic_{self.world_id}"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing world critic agent: {self._agent_id}")
                return self._agent_id

        # Create new agent with world-specific context
        system_prompt = self._get_system_prompt()

        # Get studio block IDs for shared memory
        studio_block_ids = get_studio_block_ids()

        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            include_multi_agent_tools=True,  # Enable multi-agent communication
            tags=["studio", "editor", f"world_{self.world_id}"],  # Tags for agent discovery
            block_ids=studio_block_ids,  # Shared studio blocks
            memory_blocks=[
                {"label": "world_context", "value": f"Critic for {self.world_name}, set in {self.year_setting}."},
                {"label": "evaluation_history", "value": "No evaluations performed yet."},
                {"label": "quality_standards", "value": "Maintaining high standards for this world."},
            ],
        )
        self._agent_id = agent.id
        logger.info(f"Created world critic agent: {self._agent_id}")
        return self._agent_id

    def _get_system_prompt(self) -> str:
        """Generate system prompt with world context."""
        return f"""You are the Critic for "{self.world_name}", a sci-fi world set in {self.year_setting}.

## YOUR WORLD
{self.world_premise[:2000] if self.world_premise else "A sci-fi world with unique rules."}

## YOUR ROLE
You evaluate stories and content within this world for:
1. **Plausibility** (0-10): Does it fit the world's rules and logic?
2. **Coherence** (0-10): Does it connect with established world elements?
3. **Originality** (0-10): Does it avoid clichés and feel fresh?
4. **Engagement** (0-10): Is it compelling and worth watching?
5. **Authenticity** (0-10): Does it feel real, not AI-generated?

## QUALITY THRESHOLD
Stories with overall score < 6 should be revised before publishing.
Be HONEST. The goal is quality, not quantity.

## AI-ISM DETECTION
Watch for vocabulary that reveals AI-generated content:
- "bustling", "cutting-edge", "sleek", "sprawling", "gleaming"
- "tapestry", "symphony", "myriad", "delve", "pivotal"
- "a testament to", "echoed through", "sent shivers"

Watch for structural patterns:
- Em-dash overuse (more than 1 per paragraph)
- "It's not just X, it's Y" pattern
- Lists of three adjectives
- Rhetorical questions that answer themselves

## RESPONSE FORMAT
Provide JSON evaluation:
{{
  "scores": {{
    "plausibility": 0-10,
    "coherence": 0-10,
    "originality": 0-10,
    "engagement": 0-10,
    "authenticity": 0-10
  }},
  "ai_isms_detected": [{{"text": "...", "pattern": "...", "location": "...", "severity": "minor/moderate/major"}}],
  "strengths": ["specific strength"],
  "weaknesses": ["specific weakness"],
  "suggestions": ["actionable improvement"],
  "should_revise": true/false
}}

Be HONEST and SPECIFIC. Don't soften criticism."""

    def _detect_ai_isms(self, text: str) -> list[AIIsm]:
        """Detect AI-isms using rule-based patterns."""
        ai_isms = []

        for pattern, description, severity in AI_ISM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                line_num = text[:match.start()].count('\n') + 1
                ai_isms.append(AIIsm(
                    text=match.group(),
                    pattern=description,
                    location=f"line {line_num}",
                    severity=severity,
                ))

        # Check for banned phrases
        for phrase in BANNED_PHRASES:
            if phrase.lower() in text.lower():
                idx = text.lower().find(phrase.lower())
                line_num = text[:idx].count('\n') + 1
                ai_isms.append(AIIsm(
                    text=phrase,
                    pattern="banned phrase",
                    location=f"line {line_num}",
                    severity="major",
                ))

        return ai_isms

    async def evaluate_story_draft(
        self,
        title: str,
        script: str,
        context: dict | None = None,
    ) -> CriticFeedback:
        """Evaluate a story draft before publishing.

        Called by Storyteller before creating a story. If score < 6,
        Storyteller should revise based on feedback.

        Args:
            title: Story title
            script: Full storyteller script/narration
            context: Optional context (participants, source conversation, etc.)

        Returns:
            CriticFeedback with scores, AI-isms, and revision suggestions
        """
        start_time = time.time()

        try:
            # First, rule-based AI-ism detection
            ai_isms = self._detect_ai_isms(f"{title}\n{script}")

            # Then LLM evaluation
            agent_id = await self._ensure_agent()
            client = self._get_client()

            content = f"""TITLE: {title}

SCRIPT:
{script[:8000]}

CONTEXT:
{json.dumps(context or {}, indent=2) if context else "Direct observation"}"""

            prompt = f"""Evaluate this story draft for {self.world_name}.

{content}

Provide your evaluation as JSON. Be specific and cite examples.
If the overall score would be < 6, set "should_revise": true and provide actionable suggestions."""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            result = self._extract_response(response)
            if not result:
                raise ValueError("No response from critic agent")

            # Parse JSON response
            feedback = self._parse_feedback(result, ai_isms)

            # Log trace
            await log_trace(
                agent_type=AgentType.CRITIC,
                operation="evaluate_story_draft",
                prompt=prompt,
                response=result,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                agent_id=f"critic_{self.world_id}",
                world_id=self.world_id,
                parsed_output={
                    "title": title,
                    "overall_score": feedback.scores.overall,
                    "should_revise": feedback.should_revise,
                    "ai_isms_count": len(feedback.ai_isms),
                },
            )

            # Log activity
            async with SessionLocal() as db:
                activity = AgentActivity(
                    agent_type=AgentType.CRITIC,
                    agent_id=f"critic_{self.world_id}",
                    action="evaluated_story_draft",
                    world_id=self.world_id,
                    details={
                        "title": title,
                        "overall_score": feedback.scores.overall,
                        "should_revise": feedback.should_revise,
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                )
                db.add(activity)
                await db.commit()

            logger.info(
                f"Critic evaluated '{title}': {feedback.scores.overall:.1f}/10 "
                f"(revise: {feedback.should_revise})"
            )
            return feedback

        except Exception as e:
            logger.error(f"Error evaluating story draft: {e}", exc_info=True)
            await log_trace(
                agent_type=AgentType.CRITIC,
                operation="evaluate_story_draft",
                agent_id=f"critic_{self.world_id}",
                world_id=self.world_id,
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )
            # Return default feedback with should_revise=False to not block publishing
            return CriticFeedback(
                scores=EvaluationScores(
                    plausibility=5, coherence=5, originality=5,
                    engagement=5, authenticity=5
                ),
                ai_isms=[],
                strengths=["Unable to evaluate"],
                weaknesses=["Evaluation failed"],
                suggestions=[],
                should_revise=False,
            )

    async def evaluate_conversation(
        self,
        participants: list[dict],
        messages: list[dict],
    ) -> CriticFeedback:
        """Evaluate an ongoing conversation for story potential.

        Used by Storyteller to assess if a conversation is worth
        turning into a story.

        Args:
            participants: List of participant dicts with name, role
            messages: List of message dicts with dweller_id, content

        Returns:
            CriticFeedback with evaluation
        """
        start_time = time.time()

        try:
            # Format conversation
            conv_text = "CONVERSATION:\n"
            for msg in messages[-20:]:  # Last 20 messages
                dweller_name = "Unknown"
                for p in participants:
                    if p.get("id") == msg.get("dweller_id"):
                        dweller_name = p.get("name", "Unknown")
                        break
                conv_text += f"{dweller_name}: {msg.get('content', '')}\n"

            # Rule-based detection
            ai_isms = self._detect_ai_isms(conv_text)

            # LLM evaluation
            agent_id = await self._ensure_agent()
            client = self._get_client()

            prompt = f"""Evaluate this conversation from {self.world_name} for story potential.

{conv_text}

Provide your evaluation as JSON. Consider:
- Is there dramatic tension or emotional resonance?
- Is the dialogue authentic or does it feel AI-generated?
- Would this make a compelling short video?"""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            result = self._extract_response(response)
            if not result:
                raise ValueError("No response from critic agent")

            feedback = self._parse_feedback(result, ai_isms)

            # Log trace
            await log_trace(
                agent_type=AgentType.CRITIC,
                operation="evaluate_conversation",
                prompt=prompt,
                response=result,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                agent_id=f"critic_{self.world_id}",
                world_id=self.world_id,
                parsed_output={
                    "participant_count": len(participants),
                    "message_count": len(messages),
                    "overall_score": feedback.scores.overall,
                },
            )

            return feedback

        except Exception as e:
            logger.error(f"Error evaluating conversation: {e}", exc_info=True)
            return CriticFeedback(
                scores=EvaluationScores(
                    plausibility=5, coherence=5, originality=5,
                    engagement=5, authenticity=5
                ),
                ai_isms=[],
                strengths=[],
                weaknesses=["Evaluation failed"],
                suggestions=[],
                should_revise=False,
            )

    def _parse_feedback(self, result: str, rule_ai_isms: list[AIIsm]) -> CriticFeedback:
        """Parse LLM response into CriticFeedback."""
        try:
            # Find JSON in response
            json_start = result.find('{')
            json_end = result.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(result[json_start:json_end])
            else:
                raise ValueError(f"Could not find JSON in response: {result[:200]}")

            scores = EvaluationScores(
                plausibility=float(data.get("scores", {}).get("plausibility", 5)),
                coherence=float(data.get("scores", {}).get("coherence", 5)),
                originality=float(data.get("scores", {}).get("originality", 5)),
                engagement=float(data.get("scores", {}).get("engagement", 5)),
                authenticity=float(data.get("scores", {}).get("authenticity", 5)),
            )

            llm_ai_isms = [
                AIIsm(
                    text=a.get("text", ""),
                    pattern=a.get("pattern", ""),
                    location=a.get("location", ""),
                    severity=a.get("severity", "minor"),
                )
                for a in data.get("ai_isms_detected", [])
            ]

            # Combine rule-based and LLM-detected AI-isms
            all_ai_isms = rule_ai_isms + llm_ai_isms

            # Determine should_revise based on score or explicit flag
            should_revise = data.get("should_revise", scores.overall < 6)

            return CriticFeedback(
                scores=scores,
                ai_isms=all_ai_isms,
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                suggestions=data.get("suggestions", []),
                should_revise=should_revise,
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(f"Failed to parse feedback: {e}")
            return CriticFeedback(
                scores=EvaluationScores(
                    plausibility=5, coherence=5, originality=5,
                    engagement=5, authenticity=5
                ),
                ai_isms=rule_ai_isms,
                strengths=[],
                weaknesses=["Could not parse evaluation"],
                suggestions=[],
                should_revise=False,
            )

    def _extract_response(self, response: Any) -> str | None:
        """Extract text from Letta response."""
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "assistant_message") and msg.assistant_message:
                        return msg.assistant_message
                    elif hasattr(msg, "content") and msg.content:
                        return msg.content
        return None


# Per-world critic instances
_world_critics: dict[UUID, WorldCritic] = {}


def get_world_critic(
    world_id: UUID,
    world_name: str,
    world_premise: str = "",
    year_setting: int = 2050,
) -> WorldCritic:
    """Get or create a WorldCritic for a specific world."""
    if world_id not in _world_critics:
        _world_critics[world_id] = WorldCritic(
            world_id=world_id,
            world_name=world_name,
            world_premise=world_premise,
            year_setting=year_setting,
        )
    return _world_critics[world_id]


async def get_critic_status_for_world(world_id: UUID) -> dict:
    """Get critic evaluation stats for a specific world."""
    async with SessionLocal() as db:
        # Count evaluations for this world
        # Note: CriticEvaluation doesn't have world_id directly,
        # but we can check via stories
        eval_query = (
            select(func.count())
            .select_from(CriticEvaluation)
            .join(Story, CriticEvaluation.target_id == Story.id)
            .where(Story.world_id == world_id)
        )
        eval_result = await db.execute(eval_query)
        evaluations_count = eval_result.scalar() or 0

        # Get average score
        avg_query = (
            select(func.avg(CriticEvaluation.overall_score))
            .join(Story, CriticEvaluation.target_id == Story.id)
            .where(Story.world_id == world_id)
        )
        avg_result = await db.execute(avg_query)
        average_score = avg_result.scalar()

        # Get last evaluation time
        last_query = (
            select(CriticEvaluation.created_at)
            .join(Story, CriticEvaluation.target_id == Story.id)
            .where(Story.world_id == world_id)
            .order_by(CriticEvaluation.created_at.desc())
            .limit(1)
        )
        last_result = await db.execute(last_query)
        last_eval = last_result.scalar_one_or_none()

        # Check if critic is active (has evaluated recently or agent exists)
        has_recent = last_eval is not None

        return {
            "status": "active" if has_recent else "idle",
            "evaluations_count": evaluations_count,
            "last_evaluation": last_eval.isoformat() if last_eval else None,
            "average_score": round(average_score, 1) if average_score else None,
        }
