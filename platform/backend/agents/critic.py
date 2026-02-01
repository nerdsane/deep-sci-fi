"""Critic Agent for Deep Sci-Fi platform.

The Critic Agent evaluates worlds and stories for quality, detecting:
- AI-isms (phrases that sound AI-generated)
- Cliches and tropes
- Plausibility issues
- Coherence problems

Uses Opus 4.5 for nuanced evaluation and feedback.
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
from sqlalchemy import select

from db import (
    CriticEvaluation,
    CriticTargetType,
    World,
    Story,
    Dweller,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import (
    get_critic_prompt,
    get_critic_world_prompt,
    get_critic_story_prompt,
    BANNED_PHRASES,
)
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


class CriticAgent:
    """Critic Agent - evaluates worlds and stories for quality.

    Uses Opus 4.5 for nuanced evaluation and authentic feedback.
    """

    MODEL = "anthropic/claude-opus-4-5-20251101"

    def __init__(self):
        self._client: Letta | None = None
        self._agent_id: str | None = None

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
            self._client = Letta(base_url=base_url)
        return self._client

    async def _ensure_agent(self, target_type: str = "world") -> str:
        """Ensure critic agent exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = "critic_agent"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing critic agent: {self._agent_id}")
                return self._agent_id

        # Create new agent with memory blocks for persistent evaluation context
        system_prompt = get_critic_prompt(target_type)

        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            memory_blocks=[
                {"label": "evaluation_history", "value": "No evaluations performed yet."},
                {"label": "pattern_library", "value": "Common AI-isms and cliches to watch for."},
                {"label": "quality_standards", "value": "Maintaining high standards for plausibility and originality."},
            ],
        )
        self._agent_id = agent.id
        logger.info(f"Created critic agent: {self._agent_id}")
        return self._agent_id

    async def evaluate_world(self, world_id: UUID) -> CriticEvaluation:
        """Evaluate a world for quality.

        Args:
            world_id: UUID of the world to evaluate

        Returns:
            CriticEvaluation database object
        """
        start_time = time.time()

        async with SessionLocal() as db:
            # Get world
            result = await db.execute(
                select(World).where(World.id == world_id)
            )
            world = result.scalar_one_or_none()
            if not world:
                raise ValueError(f"World not found: {world_id}")

            # Get dwellers
            dwellers_result = await db.execute(
                select(Dweller).where(Dweller.world_id == world_id)
            )
            dwellers = dwellers_result.scalars().all()

            # Format content for evaluation
            content = self._format_world_content(world, dwellers)

            # Detect AI-isms first (rule-based)
            ai_isms = self._detect_ai_isms(content)

            # Get LLM evaluation
            feedback = await self._get_llm_evaluation(
                target_type="world",
                content=content,
                world_name=world.name,
            )

            # Combine rule-based AI-isms with LLM-detected ones
            ai_isms_combined = ai_isms + feedback.ai_isms

            # Create evaluation
            evaluation = CriticEvaluation(
                target_type=CriticTargetType.WORLD,
                target_id=world_id,
                evaluation={
                    "scores": {
                        "plausibility": feedback.scores.plausibility,
                        "coherence": feedback.scores.coherence,
                        "originality": feedback.scores.originality,
                        "engagement": feedback.scores.engagement,
                        "authenticity": feedback.scores.authenticity,
                    },
                    "feedback": {
                        "strengths": feedback.strengths,
                        "weaknesses": feedback.weaknesses,
                        "suggestions": feedback.suggestions,
                    },
                    "rubric_version": "1.0",
                },
                ai_isms_detected=[
                    {"text": a.text, "pattern": a.pattern, "location": a.location, "severity": a.severity}
                    for a in ai_isms_combined
                ],
                overall_score=feedback.scores.overall,
            )
            db.add(evaluation)

            # Log activity
            activity = AgentActivity(
                agent_type=AgentType.CRITIC,
                agent_id="critic_agent",
                action="evaluated_world",
                world_id=world_id,
                details={
                    "world_name": world.name,
                    "overall_score": feedback.scores.overall,
                    "ai_isms_count": len(ai_isms_combined),
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )
            db.add(activity)

            await db.commit()
            await db.refresh(evaluation)

            logger.info(f"Evaluated world {world.name}: {feedback.scores.overall:.1f}/10")
            return evaluation

    async def evaluate_story(self, story_id: UUID) -> CriticEvaluation:
        """Evaluate a story for quality.

        Args:
            story_id: UUID of the story to evaluate

        Returns:
            CriticEvaluation database object
        """
        start_time = time.time()

        async with SessionLocal() as db:
            # Get story with world
            result = await db.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if not story:
                raise ValueError(f"Story not found: {story_id}")

            # Get world
            world_result = await db.execute(
                select(World).where(World.id == story.world_id)
            )
            world = world_result.scalar_one_or_none()

            # Format content for evaluation
            content = f"""TITLE: {story.title}
DESCRIPTION: {story.description or 'N/A'}
TRANSCRIPT:
{story.transcript or 'N/A'}"""

            # Detect AI-isms first (rule-based)
            ai_isms = self._detect_ai_isms(content)

            # Get LLM evaluation
            feedback = await self._get_llm_evaluation(
                target_type="story",
                content=content,
                world_name=world.name if world else "Unknown",
            )

            # Combine rule-based AI-isms with LLM-detected ones
            ai_isms_combined = ai_isms + feedback.ai_isms

            # Create evaluation
            evaluation = CriticEvaluation(
                target_type=CriticTargetType.STORY,
                target_id=story_id,
                evaluation={
                    "scores": {
                        "plausibility": feedback.scores.plausibility,
                        "coherence": feedback.scores.coherence,
                        "originality": feedback.scores.originality,
                        "engagement": feedback.scores.engagement,
                        "authenticity": feedback.scores.authenticity,
                    },
                    "feedback": {
                        "strengths": feedback.strengths,
                        "weaknesses": feedback.weaknesses,
                        "suggestions": feedback.suggestions,
                    },
                    "rubric_version": "1.0",
                },
                ai_isms_detected=[
                    {"text": a.text, "pattern": a.pattern, "location": a.location, "severity": a.severity}
                    for a in ai_isms_combined
                ],
                overall_score=feedback.scores.overall,
            )
            db.add(evaluation)

            # Log activity
            activity = AgentActivity(
                agent_type=AgentType.CRITIC,
                agent_id="critic_agent",
                action="evaluated_story",
                world_id=story.world_id,
                details={
                    "story_title": story.title,
                    "overall_score": feedback.scores.overall,
                    "ai_isms_count": len(ai_isms_combined),
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )
            db.add(activity)

            await db.commit()
            await db.refresh(evaluation)

            logger.info(f"Evaluated story '{story.title}': {feedback.scores.overall:.1f}/10")
            return evaluation

    def _detect_ai_isms(self, text: str) -> list[AIIsm]:
        """Detect AI-isms using rule-based patterns.

        Returns list of detected AI-isms with locations.
        """
        ai_isms = []

        for pattern, description, severity in AI_ISM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Find line number
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

    async def _get_llm_evaluation(
        self,
        target_type: str,
        content: str,
        world_name: str,
    ) -> CriticFeedback:
        """Get evaluation from LLM.

        Args:
            target_type: "world" or "story"
            content: The content to evaluate
            world_name: Name of the world

        Returns:
            CriticFeedback with scores and feedback
        """
        start_time = time.time()

        try:
            agent_id = await self._ensure_agent(target_type)
            client = self._get_client()

            prompt = f"""Evaluate this {target_type} for quality. Be specific and cite examples.

CONTENT TO EVALUATE:
{content[:8000]}  # Truncate if too long

Provide your evaluation as JSON:
{{
  "scores": {{
    "plausibility": 0-10,
    "coherence": 0-10,
    "originality": 0-10,
    "engagement": 0-10,
    "authenticity": 0-10
  }},
  "ai_isms_detected": [
    {{"text": "example text", "pattern": "what makes it AI-ish", "location": "where found", "severity": "minor/moderate/major"}}
  ],
  "strengths": ["specific strength with example"],
  "weaknesses": ["specific weakness with example"],
  "suggestions": ["actionable improvement"]
}}

Be HONEST and SPECIFIC. Don't soften criticism."""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            result = self._extract_response(response)
            if not result:
                raise ValueError("No response from critic agent - evaluation failed")

            # Parse JSON response
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

                ai_isms = [
                    AIIsm(
                        text=a.get("text", ""),
                        pattern=a.get("pattern", ""),
                        location=a.get("location", ""),
                        severity=a.get("severity", "minor"),
                    )
                    for a in data.get("ai_isms_detected", [])
                ]

                # Log trace
                await log_trace(
                    agent_type=AgentType.CRITIC,
                    operation=f"evaluate_{target_type}",
                    prompt=prompt,
                    response=result,
                    model=self.MODEL,
                    duration_ms=int((time.time() - start_time) * 1000),
                    agent_id="critic_agent",
                    parsed_output={
                        "target_type": target_type,
                        "world_name": world_name,
                        "overall_score": scores.overall,
                        "ai_isms_count": len(ai_isms),
                        "scores": {
                            "plausibility": scores.plausibility,
                            "coherence": scores.coherence,
                            "originality": scores.originality,
                            "engagement": scores.engagement,
                            "authenticity": scores.authenticity,
                        },
                    },
                )

                return CriticFeedback(
                    scores=scores,
                    ai_isms=ai_isms,
                    strengths=data.get("strengths", []),
                    weaknesses=data.get("weaknesses", []),
                    suggestions=data.get("suggestions", []),
                )

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse LLM evaluation response: {e}")
                raise ValueError(f"Failed to parse LLM evaluation: {e}")

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}", exc_info=True)
            # Log error trace
            await log_trace(
                agent_type=AgentType.CRITIC,
                operation=f"evaluate_{target_type}",
                agent_id="critic_agent",
                duration_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )
            raise


    def _format_world_content(self, world: World, dwellers: list[Dweller]) -> str:
        """Format world content for evaluation."""
        content = f"""WORLD: {world.name}
PREMISE: {world.premise}
YEAR: {world.year_setting}

CAUSAL CHAIN:
{json.dumps(world.causal_chain, indent=2)}

DWELLERS:
"""
        for d in dwellers:
            persona = d.persona
            content += f"""
- {persona.get('name', 'Unknown')} ({persona.get('role', 'Unknown')})
  Background: {persona.get('background', 'N/A')}
  Beliefs: {', '.join(persona.get('beliefs', []))}
"""
        return content

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

# Singleton instance
_critic: CriticAgent | None = None


def get_critic() -> CriticAgent:
    """Get the critic agent instance."""
    global _critic
    if _critic is None:
        _critic = CriticAgent()
    return _critic
