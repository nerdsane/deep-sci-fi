"""Production Agent for Deep Sci-Fi platform.

The Production Agent is responsible for deciding WHAT worlds should be created
based on current trends, platform engagement data, and market gaps.

It uses real-time web research (via Exa API through Letta) to stay current
with 2026 developments in technology, climate, society, and more.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    ProductionBrief,
    BriefStatus,
    World,
    Story,
    SocialInteraction,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import get_production_prompt, PRODUCTION_ENGAGEMENT_ANALYSIS_PROMPT
from .tracing import log_trace

logger = logging.getLogger(__name__)


@dataclass
class TrendResearch:
    """Results from trend research."""
    technology: list[dict] = field(default_factory=list)
    climate: list[dict] = field(default_factory=list)
    society: list[dict] = field(default_factory=list)
    geopolitics: list[dict] = field(default_factory=list)
    biotech: list[dict] = field(default_factory=list)
    space: list[dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class EngagementAnalysis:
    """Analysis of platform engagement."""
    top_themes: list[dict] = field(default_factory=list)
    story_performance: list[dict] = field(default_factory=list)
    saturated_themes: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    total_worlds: int = 0
    total_stories: int = 0
    avg_engagement_per_world: float = 0.0


@dataclass
class WorldRecommendation:
    """A single world theme recommendation."""
    theme: str
    premise_sketch: str
    core_question: str
    target_audience: str
    rationale: str
    estimated_appeal: str
    anti_cliche_notes: str


class ProductionAgent:
    """Production Agent - decides what worlds to create.

    Uses Opus 4.5 for high-quality trend analysis and creative briefs.
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

    async def _ensure_agent(self) -> str:
        """Ensure production agent exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = "production_agent"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing production agent: {self._agent_id}")
                return self._agent_id

        # Create new agent with Exa search tool and memory blocks
        system_prompt = get_production_prompt()

        # Create agent with web search capability and persistent memory
        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
            tools=["web_search"],  # Enable web search tool
            memory_blocks=[
                {"label": "platform_state", "value": "Platform just starting. No content yet."},
                {"label": "trend_memory", "value": "No trends researched yet."},
                {"label": "past_briefs", "value": "No briefs generated yet."},
            ],
        )
        self._agent_id = agent.id
        logger.info(f"Created production agent: {self._agent_id}")
        return self._agent_id

    async def research_trends(self) -> TrendResearch:
        """Research current 2026 trends using Exa API.

        Searches for emerging developments in:
        - Technology
        - Climate and environment
        - Society and culture
        - Geopolitics
        - Biotech and health
        - Space exploration
        """
        start_time = time.time()
        research = TrendResearch()

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Research each category
            categories = [
                ("technology", "emerging technology trends 2026 AI robotics"),
                ("climate", "climate change developments 2026 environmental"),
                ("society", "social trends 2026 culture work remote"),
                ("geopolitics", "geopolitical developments 2026 international"),
                ("biotech", "biotech breakthroughs 2026 longevity genetics"),
                ("space", "space exploration 2026 commercial lunar"),
            ]

            for category, query in categories:
                try:
                    response = client.agents.messages.create(
                        agent_id=agent_id,
                        messages=[{
                            "role": "user",
                            "content": f"Search for and summarize the top 5 {category} trends. Query: {query}. Return as JSON array with 'title', 'summary', and 'implication' fields."
                        }],
                    )

                    # Extract response
                    result = self._extract_response(response)
                    if result:
                        # Try to parse as JSON
                        try:
                            trends = json.loads(result)
                            setattr(research, category, trends if isinstance(trends, list) else [])
                        except json.JSONDecodeError:
                            # Store as single item if not JSON
                            setattr(research, category, [{"summary": result}])

                except Exception as e:
                    logger.warning(f"Failed to research {category}: {e}")
                    setattr(research, category, [])

            research.timestamp = datetime.utcnow()

            # Log activity
            await self._log_activity(
                action="researched_trends",
                details={
                    "categories": list(dict(categories).keys()),
                    "total_findings": sum(len(getattr(research, cat)) for cat, _ in categories),
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            return research

        except Exception as e:
            logger.error(f"Trend research failed: {e}", exc_info=True)
            return research

    async def analyze_engagement(self) -> EngagementAnalysis:
        """Analyze platform engagement data.

        Queries the database for:
        - Views, reactions, comments per world
        - What themes resonate
        - What's saturated
        """
        start_time = time.time()
        analysis = EngagementAnalysis()

        try:
            async with SessionLocal() as db:
                # Get total counts
                world_count = await db.execute(
                    select(func.count()).select_from(World).where(World.is_active == True)
                )
                analysis.total_worlds = world_count.scalar() or 0

                story_count = await db.execute(
                    select(func.count()).select_from(Story)
                )
                analysis.total_stories = story_count.scalar() or 0

                # Get worlds with engagement metrics
                worlds = await db.execute(
                    select(World)
                    .where(World.is_active == True)
                    .order_by(World.follower_count.desc())
                    .limit(20)
                )
                worlds_list = worlds.scalars().all()

                # Analyze theme performance
                theme_performance = {}
                for world in worlds_list:
                    # Extract theme keywords from premise
                    theme_keywords = self._extract_theme_keywords(world.premise)
                    engagement_score = (
                        world.follower_count +
                        world.story_count * 2 +
                        world.dweller_count
                    )

                    for keyword in theme_keywords:
                        if keyword not in theme_performance:
                            theme_performance[keyword] = {"count": 0, "total_engagement": 0}
                        theme_performance[keyword]["count"] += 1
                        theme_performance[keyword]["total_engagement"] += engagement_score

                # Sort by average engagement
                analysis.top_themes = sorted(
                    [
                        {
                            "theme": k,
                            "count": v["count"],
                            "avg_engagement": v["total_engagement"] / v["count"] if v["count"] > 0 else 0,
                        }
                        for k, v in theme_performance.items()
                    ],
                    key=lambda x: x["avg_engagement"],
                    reverse=True,
                )[:10]

                # Identify saturated themes (many worlds, declining engagement)
                analysis.saturated_themes = [
                    t["theme"] for t in analysis.top_themes
                    if t["count"] > 3 and t["avg_engagement"] < 10
                ]

                # Calculate average engagement
                if worlds_list:
                    total_engagement = sum(
                        w.follower_count + w.story_count * 2
                        for w in worlds_list
                    )
                    analysis.avg_engagement_per_world = total_engagement / len(worlds_list)

            # Log activity
            await self._log_activity(
                action="analyzed_engagement",
                details={
                    "total_worlds": analysis.total_worlds,
                    "total_stories": analysis.total_stories,
                    "top_themes_count": len(analysis.top_themes),
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            return analysis

        except Exception as e:
            logger.error(f"Engagement analysis failed: {e}", exc_info=True)
            return analysis

    async def generate_brief(
        self,
        trend_research: TrendResearch | None = None,
        engagement_analysis: EngagementAnalysis | None = None,
    ) -> ProductionBrief:
        """Generate a production brief with world recommendations.

        Args:
            trend_research: Optional pre-computed trend research
            engagement_analysis: Optional pre-computed engagement analysis

        Returns:
            ProductionBrief with 3-5 recommendations
        """
        start_time = time.time()

        # Get research if not provided
        if trend_research is None:
            trend_research = await self.research_trends()

        if engagement_analysis is None:
            engagement_analysis = await self.analyze_engagement()

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Format research for the agent
            research_context = self._format_research_context(trend_research, engagement_analysis)

            prompt = f"""Based on this research and engagement data, generate a production brief with 3-5 world theme recommendations.

TREND RESEARCH:
{research_context}

ENGAGEMENT ANALYSIS:
- Total worlds: {engagement_analysis.total_worlds}
- Total stories: {engagement_analysis.total_stories}
- Avg engagement per world: {engagement_analysis.avg_engagement_per_world:.1f}
- Top themes: {', '.join(t['theme'] for t in engagement_analysis.top_themes[:5])}
- Saturated themes to avoid: {', '.join(engagement_analysis.saturated_themes)}

Generate 3-5 world recommendations as a JSON array. Each must have:
- theme: One-line theme description
- premise_sketch: 2-3 sentence world premise
- core_question: The central "what if"
- target_audience: Who would find this compelling
- rationale: Why now? What 2026 trend makes this relevant?
- estimated_appeal: high/medium/low with reasoning
- anti_cliche_notes: How this avoids common sci-fi tropes

Return ONLY the JSON array, no other text."""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            result = self._extract_response(response)
            recommendations = []

            if result:
                try:
                    # Find JSON array in response
                    json_start = result.find('[')
                    json_end = result.rfind(']') + 1
                    if json_start >= 0 and json_end > json_start:
                        recommendations = json.loads(result[json_start:json_end])
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse recommendations JSON: {e}")

            # Log trace for observability
            await log_trace(
                agent_type=AgentType.PRODUCTION,
                operation="generate_brief",
                prompt=prompt,
                response=result,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                parsed_output={"recommendations": recommendations},
            )

            # Create brief in database
            async with SessionLocal() as db:
                brief = ProductionBrief(
                    research_data={
                        "trends": {
                            "technology": trend_research.technology,
                            "climate": trend_research.climate,
                            "society": trend_research.society,
                            "geopolitics": trend_research.geopolitics,
                            "biotech": trend_research.biotech,
                            "space": trend_research.space,
                        },
                        "timestamp": trend_research.timestamp.isoformat(),
                    },
                    recommendations=recommendations,
                    status=BriefStatus.PENDING,
                )
                db.add(brief)
                await db.commit()
                await db.refresh(brief)

                # Log activity
                await self._log_activity(
                    action="generated_brief",
                    details={
                        "brief_id": str(brief.id),
                        "recommendation_count": len(recommendations),
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                )

                logger.info(f"Generated production brief {brief.id} with {len(recommendations)} recommendations")
                return brief

        except Exception as e:
            logger.error(f"Brief generation failed: {e}", exc_info=True)
            raise

    async def evaluate_platform_state(self, metrics: dict) -> bool:
        """Let the production agent evaluate if action is needed.

        Uses the agent's judgment rather than hardcoded thresholds.
        Raises exceptions on failure - no silent defaults.

        Args:
            metrics: Dictionary containing platform metrics:
                - worlds_24h: Worlds created in last 24 hours
                - stories_24h: Stories created in last 24 hours
                - active_worlds: Worlds with recent activity
                - total_worlds: Total active worlds
                - total_stories: Total stories
                - pending_briefs: Number of pending briefs

        Returns:
            True if the agent decides action is needed

        Raises:
            ValueError: If agent fails to respond or gives unclear response
        """
        agent_id = await self._ensure_agent()
        client = self._get_client()

        prompt = f"""PLATFORM STATE EVALUATION

You are the Production Agent. Review these metrics and decide if action is needed.

CURRENT METRICS:
- Worlds created in last 24h: {metrics.get('worlds_24h', 0)}
- Stories created in last 24h: {metrics.get('stories_24h', 0)}
- Active worlds (recent activity): {metrics.get('active_worlds', 0)}
- Total worlds: {metrics.get('total_worlds', 0)}
- Total stories: {metrics.get('total_stories', 0)}
- Pending briefs awaiting approval: {metrics.get('pending_briefs', 0)}

DECISION CRITERIA (use your judgment):
- Is the platform feeling stale? (no new content)
- Are there enough active worlds to maintain engagement?
- Would new content enhance the platform right now?
- Are there already pending briefs that should be processed first?

Respond with exactly one of:
ACTION_NEEDED - [brief reason]
NO_ACTION - [brief reason]

Trust your judgment. Don't wait for arbitrary thresholds."""

        response = client.agents.messages.create(
            agent_id=agent_id,
            messages=[{"role": "user", "content": prompt}],
        )

        result = self._extract_response(response)
        if not result:
            raise ValueError("No response from production agent - evaluation failed")

        logger.info(f"Production agent decision: {result[:100]}")

        # Parse the decision
        result_upper = result.upper().strip()
        action_needed = result_upper.startswith("ACTION_NEEDED")
        no_action = result_upper.startswith("NO_ACTION")

        # Log trace
        await log_trace(
            agent_type=AgentType.PRODUCTION,
            operation="evaluate_platform_state",
            prompt=prompt,
            response=result,
            model=self.MODEL,
            parsed_output={"decision": "ACTION_NEEDED" if action_needed else "NO_ACTION" if no_action else "UNCLEAR"},
        )

        if action_needed:
            return True
        elif no_action:
            return False
        else:
            raise ValueError(f"Unclear response from production agent: {result[:200]}")

    async def should_create_world(self) -> bool:
        """Check if conditions are right for creating a new world.

        Legacy method - still used by daily_production_check.
        Uses simple heuristics for quick checks.
        """
        try:
            async with SessionLocal() as db:
                # Check time since last world
                latest_world = await db.execute(
                    select(World)
                    .order_by(World.created_at.desc())
                    .limit(1)
                )
                world = latest_world.scalar_one_or_none()

                if world:
                    hours_since_last = (datetime.utcnow() - world.created_at).total_seconds() / 3600
                    # Don't create more than one world per 24 hours
                    if hours_since_last < 24:
                        logger.info(f"Too soon since last world ({hours_since_last:.1f}h ago)")
                        return False

                # Check for pending briefs
                pending_briefs = await db.execute(
                    select(func.count())
                    .select_from(ProductionBrief)
                    .where(ProductionBrief.status == BriefStatus.PENDING)
                )
                pending_count = pending_briefs.scalar() or 0

                if pending_count > 0:
                    logger.info(f"Already have {pending_count} pending briefs")
                    return False

                return True

        except Exception as e:
            logger.error(f"Error checking world creation conditions: {e}")
            return False

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

    def _extract_theme_keywords(self, premise: str) -> list[str]:
        """Extract theme keywords from a world premise."""
        # Simple keyword extraction - could be enhanced with NLP
        keywords = []
        theme_words = [
            "climate", "ai", "genetic", "space", "ocean", "migration",
            "pandemic", "automation", "virtual", "memory", "longevity",
            "colony", "nuclear", "renewable", "drought", "flood",
            "biotech", "quantum", "neural", "corporate", "democratic",
        ]
        premise_lower = premise.lower()
        for word in theme_words:
            if word in premise_lower:
                keywords.append(word)
        return keywords[:5]  # Max 5 keywords

    def _format_research_context(
        self,
        trends: TrendResearch,
        engagement: EngagementAnalysis,
    ) -> str:
        """Format research data for the agent."""
        sections = []

        for category in ["technology", "climate", "society", "geopolitics", "biotech", "space"]:
            items = getattr(trends, category, [])
            if items:
                section = f"\n{category.upper()}:\n"
                for item in items[:3]:  # Top 3 per category
                    if isinstance(item, dict):
                        title = item.get("title", "")
                        summary = item.get("summary", str(item))
                        section += f"- {title}: {summary[:200]}\n" if title else f"- {summary[:200]}\n"
                    else:
                        section += f"- {str(item)[:200]}\n"
                sections.append(section)

        return "\n".join(sections)

    async def _log_activity(
        self,
        action: str,
        details: dict | None = None,
        world_id: UUID | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log agent activity for observability."""
        try:
            async with SessionLocal() as db:
                activity = AgentActivity(
                    agent_type=AgentType.PRODUCTION,
                    agent_id="production_agent",
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
_production_agent: ProductionAgent | None = None


def get_production_agent() -> ProductionAgent:
    """Get the production agent instance."""
    global _production_agent
    if _production_agent is None:
        _production_agent = ProductionAgent()
    return _production_agent
