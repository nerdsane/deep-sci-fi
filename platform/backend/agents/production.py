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
from .studio_blocks import get_studio_block_ids, update_studio_block
from .studio_tools import get_curator_tool_ids
from .tracing import log_trace

logger = logging.getLogger(__name__)


@dataclass
class TrendResearch:
    """Results from trend research."""
    discoveries: list[dict] = field(default_factory=list)  # What the curator found
    rabbit_holes: list[dict] = field(default_factory=list)  # Connections and surprises
    synthesis: str = ""  # The curator's take on what they found
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
    """Production Agent (Curator) - decides what worlds to create.

    Uses Opus 4.5 for high-quality trend analysis and creative briefs.
    Uses Letta's multi-agent tools for studio collaboration.
    Tags: ["studio", "curator"]
    """

    MODEL = "anthropic/claude-opus-4-5-20251101"

    def __init__(self):
        self._client: Letta | None = None
        self._agent_id: str | None = None

    def _get_client(self) -> Letta:
        """Get or create Letta client."""
        if self._client is None:
            base_url = os.getenv("LETTA_BASE_URL", "http://localhost:8285")
            # Long timeout for Opus 4.5 with web search (can take 2+ minutes)
            self._client = Letta(base_url=base_url, timeout=300.0)
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

        # Create new agent with web search tool and memory blocks
        system_prompt = get_production_prompt()

        # Get studio block IDs for shared memory (optional, may fail)
        try:
            studio_block_ids = get_studio_block_ids()
        except Exception as e:
            logger.warning(f"Failed to get studio blocks: {e}")
            studio_block_ids = []

        # Get communication tool IDs (optional, may fail with Letta API changes)
        communication_tool_ids = []
        try:
            communication_tool_ids = await get_curator_tool_ids()
        except Exception as e:
            logger.warning(f"Failed to get communication tools: {e}. Proceeding without them.")

        # Build agent create kwargs - only include optional params if they have values
        create_kwargs = {
            "name": agent_name,
            "model": self.MODEL,
            "embedding": "openai/text-embedding-ada-002",
            "system": system_prompt,
            "tools": ["web_search", "fetch_webpage"],  # Enable web search and page fetching
            "include_multi_agent_tools": True,  # Enable multi-agent communication
            "tags": ["studio", "curator"],  # Tags for agent discovery
            "memory_blocks": [
                {"label": "platform_state", "value": "Platform just starting. No content yet."},
                {"label": "trend_memory", "value": "No trends researched yet."},
                {"label": "past_briefs", "value": "No briefs generated yet."},
                {"label": "pending_feedback", "value": "No pending feedback from Editor."},
                {"label": "conversation_history", "value": "No conversations with other agents yet."},
                {"label": "learned_patterns", "value": "What I've learned about what works."},
            ],
        }
        # Only add tool_ids and block_ids if they have values (Letta API rejects null)
        if communication_tool_ids:
            create_kwargs["tool_ids"] = communication_tool_ids
        if studio_block_ids:
            create_kwargs["block_ids"] = studio_block_ids

        agent = client.agents.create(**create_kwargs)
        self._agent_id = agent.id
        logger.info(f"Created production agent: {self._agent_id}")
        return self._agent_id

    async def research_trends(self) -> TrendResearch:
        """Let the Curator explore freely.

        Single prompt - no step-by-step micromanagement.
        The Curator knows their job. Let them work.
        """
        start_time = time.time()
        research = TrendResearch()

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # One prompt - let the Curator do their thing
            research_prompt = """Time to do what you do best - go down the rabbit hole.

USE YOUR web_search TOOL. Actually search for things. Don't just talk about searching.

Start with a few searches like:
- "AI agents 2026 breakthroughs"
- "synthetic biology 2026"
- "climate technology working 2026"
- Whatever else catches your curiosity

Then follow threads. Search for more specific things based on what you find. Make connections.

Some areas to explore (but don't let me limit you):
- What's actually shipping in AI right now, not the hype
- Weird biotech that sounds like fiction
- Climate tech that's working
- Space stuff that's real
- How digital culture is shifting
- Any emerging tech that made you go "wait what"

IMPORTANT: Use the web_search tool multiple times. Follow the rabbit holes.

When you're done exploring, tell me:
1. What you found (the interesting stuff, not everything) - cite your sources
2. What surprised you
3. What connections you're seeing
4. What feels like it could be a great sci-fi world seed

Go explore. I'll wait."""

            logger.info("Curator exploring...")

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": research_prompt}],
            )

            # Extract full trace for observability
            full_trace = self._extract_full_trace(response)
            exploration_result = self._extract_response(response)

            if exploration_result:
                research.discoveries.append({
                    "phase": "exploration",
                    "content": exploration_result,
                })
                # The synthesis IS the exploration - no separate step needed
                research.synthesis = exploration_result

            research.timestamp = datetime.utcnow()

            # Log trace with FULL agent activity (thinking, tool calls, results)
            await log_trace(
                agent_type=AgentType.PRODUCTION,
                operation="research_trends",
                prompt=research_prompt,
                response=exploration_result,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                parsed_output={
                    "response_length": len(exploration_result) if exploration_result else 0,
                    "reasoning_steps": len(full_trace["reasoning"]),
                    "tool_calls": full_trace["tool_calls"],
                    "tool_results": full_trace["tool_results"],
                    "full_reasoning": full_trace["reasoning"],
                },
            )

            # Log activity
            await self._log_activity(
                action="researched_trends",
                details={
                    "approach": "free_exploration",
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info("Curator exploration complete")
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

        The Curator synthesizes their research into world seeds.

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

            # Format the curator's research
            research_text = self._format_curator_research(trend_research)

            prompt = f"""Research: {research_text[:500]}

Platform: {engagement_analysis.total_worlds} worlds, avoid: {', '.join(engagement_analysis.saturated_themes[:3]) if engagement_analysis.saturated_themes else 'none'}

Give 3 world ideas as JSON. CRITICAL: Output ONLY the raw JSON array below. NO preamble, NO markdown, NO explanation. Just the array.

[{{"theme":"hook","premise_sketch":"1 sentence","core_question":"what-if","rationale":"why now","target_audience":"who"}}]"""

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract full trace for observability
            full_trace = self._extract_full_trace(response)
            result = self._extract_response(response)
            recommendations = []

            if result:
                try:
                    # Strip markdown code fences if present
                    clean_result = result
                    if '```json' in clean_result:
                        clean_result = clean_result.split('```json', 1)[-1]
                    if '```' in clean_result:
                        clean_result = clean_result.split('```')[0]

                    # Find JSON array in response
                    json_start = clean_result.find('[')
                    json_end = clean_result.rfind(']') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_text = clean_result[json_start:json_end]
                        recommendations = json.loads(json_text)
                    else:
                        logger.warning(f"No complete JSON array found. Start: {json_start}, End: {json_end-1}")
                        logger.warning(f"Response preview: {result[:500]}...")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse recommendations JSON: {e}")
                    logger.warning(f"Attempted to parse: {clean_result[:500] if clean_result else 'empty'}...")

            # Log trace with FULL agent activity
            await log_trace(
                agent_type=AgentType.PRODUCTION,
                operation="generate_brief",
                prompt=prompt,
                response=result,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                parsed_output={
                    "recommendation_count": len(recommendations),
                    "themes": [r.get("theme", "untitled") for r in recommendations] if recommendations else [],
                    "reasoning_steps": len(full_trace["reasoning"]),
                    "tool_calls": full_trace["tool_calls"],
                    "tool_results": full_trace["tool_results"],
                    "full_reasoning": full_trace["reasoning"],
                },
            )

            # Create brief in database
            async with SessionLocal() as db:
                brief = ProductionBrief(
                    research_data={
                        "curator_research": {
                            "discoveries": trend_research.discoveries,
                            "rabbit_holes": trend_research.rabbit_holes,
                            "synthesis": trend_research.synthesis,
                        },
                        "timestamp": trend_research.timestamp.isoformat(),
                    },
                    recommendations=recommendations,
                    status=BriefStatus.PENDING,
                )
                db.add(brief)
                await db.commit()
                await db.refresh(brief)

                # Update shared studio blocks for Architect to see
                brief_summary = f"""
BRIEF {brief.id} - {len(recommendations)} world pitches:
{chr(10).join(f"- {r.get('theme', 'untitled')}: {r.get('premise_sketch', '')[:100]}..." for r in recommendations[:3])}

Status: PENDING - Ready for Architect to build
"""
                update_studio_block("studio_briefs", brief_summary)
                update_studio_block("studio_context", f"Curator created brief with {len(recommendations)} pitches. Architect can begin building.")

                # Log activity
                await self._log_activity(
                    action="generated_brief",
                    details={
                        "brief_id": str(brief.id),
                        "recommendation_count": len(recommendations),
                        "themes": [r.get("theme", "") for r in recommendations][:3],
                    },
                    duration_ms=int((time.time() - start_time) * 1000),
                )

                logger.info(f"Curator created brief {brief.id} with {len(recommendations)} world pitches")
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
        """Extract final assistant response from Letta response."""
        if response and hasattr(response, "messages"):
            for msg in response.messages:
                msg_type = type(msg).__name__
                if msg_type == "AssistantMessage":
                    if hasattr(msg, "assistant_message") and msg.assistant_message:
                        return msg.assistant_message
                    elif hasattr(msg, "content") and msg.content:
                        return msg.content
        return None

    def _extract_full_trace(self, response: Any) -> dict:
        """Extract ALL messages from Letta response for full observability.

        Returns structured trace with reasoning, tool calls, and final response.
        """
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
                # Agent's thinking/reasoning - use 'reasoning' attribute
                if hasattr(msg, "reasoning") and msg.reasoning:
                    trace["reasoning"].append(msg.reasoning)

            elif msg_type == "ToolCallMessage":
                # Tool invocations - tool_call is a ToolCall object with name/arguments
                if hasattr(msg, "tool_call") and msg.tool_call:
                    tc = msg.tool_call
                    trace["tool_calls"].append({
                        "name": getattr(tc, "name", "unknown"),
                        "arguments": getattr(tc, "arguments", "{}"),
                    })

            elif msg_type == "ToolReturnMessage":
                # Tool results - tool_return contains the result
                if hasattr(msg, "tool_return") and msg.tool_return:
                    result = msg.tool_return
                    # Truncate long results for logging
                    if isinstance(result, str) and len(result) > 500:
                        result = result[:500] + "..."
                    trace["tool_results"].append({
                        "name": getattr(msg, "name", "unknown"),
                        "status": getattr(msg, "status", "unknown"),
                        "preview": result,
                    })

            elif msg_type == "AssistantMessage":
                # Final response - use 'content' attribute
                if hasattr(msg, "content") and msg.content:
                    trace["assistant_messages"].append(msg.content)

        return trace

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

    def _format_curator_research(self, research: TrendResearch) -> str:
        """Format the curator's research for brief generation."""
        sections = []

        # Add discoveries
        if research.discoveries:
            sections.append("## YOUR DISCOVERIES\n")
            for disc in research.discoveries:
                content = disc.get("content", "")
                if content:
                    sections.append(content[:2000])
                    sections.append("\n---\n")

        # Add rabbit holes
        if research.rabbit_holes:
            sections.append("## YOUR RABBIT HOLES\n")
            for rh in research.rabbit_holes:
                content = rh.get("content", "")
                if content:
                    sections.append(content[:1500])
                    sections.append("\n---\n")

        # Add synthesis
        if research.synthesis:
            sections.append("## YOUR SYNTHESIS\n")
            sections.append(research.synthesis)

        return "\n".join(sections) if sections else "No research available - generate ideas from your memory and knowledge."

    async def run_collaborative_production(self, max_revisions: int = 3) -> dict:
        """Run full collaborative production workflow with Editor feedback loop.

        Flow:
        1. Curator researches trends (web_search)
        2. Curator generates brief
        3. Send to Editor for review
        4. If REVISE: improve and resend (up to max_revisions times)
        5. If APPROVE: send to Architect to build

        Returns:
            dict with status, brief_id, and collaboration log
        """
        start_time = time.time()
        collaboration_log = []

        try:
            # Ensure all studio agents exist before starting
            from .editor import get_editor
            from .world_creator import get_world_creator

            agent_id = await self._ensure_agent()
            editor = get_editor()
            await editor._ensure_agent()
            architect = get_world_creator()
            await architect._ensure_agent()

            collaboration_log.append({
                "step": "agents_ready",
                "agents": ["curator", "editor", "architect"],
            })

            client = self._get_client()

            # Step 1: Research
            logger.info("Curator starting research...")
            collaboration_log.append({"step": "research_start", "timestamp": datetime.utcnow().isoformat()})

            research = await self.research_trends()
            collaboration_log.append({
                "step": "research_complete",
                "discoveries": len(research.discoveries),
                "synthesis_length": len(research.synthesis),
            })

            # Step 2: Generate initial brief
            logger.info("Curator generating brief...")
            brief = await self.generate_brief(trend_research=research)
            collaboration_log.append({
                "step": "brief_generated",
                "brief_id": str(brief.id),
                "recommendation_count": len(brief.recommendations) if brief.recommendations else 0,
            })

            # Step 3: Send to Editor for review (using multi-agent messaging)
            revision_count = 0
            editor_approved = False

            while revision_count < max_revisions and not editor_approved:
                logger.info(f"Curator sending to Editor (attempt {revision_count + 1}/{max_revisions})...")

                # Format brief for Editor review
                brief_text = json.dumps({
                    "research": {
                        "synthesis": research.synthesis,
                        "discoveries_count": len(research.discoveries),
                    },
                    "recommendations": brief.recommendations or [],
                }, indent=2)

                # Ask Curator to send to Editor
                review_prompt = f"""Send your brief to The Editor for review.

Use the send_message_to_agents_matching_tags tool with tags ["studio", "editor"] to ask for feedback.

Here's what to send:

"Hey Editor, I've got a new brief ready for review. Here's what I found and what I'm recommending:

{brief_text[:3000]}

What do you think? Any issues with the research quality or the world seeds? Be honest - I'd rather fix it now."

Wait for their response and tell me what they said."""

                response = client.agents.messages.create(
                    agent_id=agent_id,
                    messages=[{"role": "user", "content": review_prompt}],
                )

                # Check if Editor was contacted and what they said
                full_trace = self._extract_full_trace(response)
                curator_response = self._extract_response(response)

                # Log the interaction
                await log_trace(
                    agent_type=AgentType.PRODUCTION,
                    operation="editor_review_request",
                    prompt=review_prompt,
                    response=curator_response,
                    model=self.MODEL,
                    duration_ms=int((time.time() - start_time) * 1000),
                    parsed_output={
                        "revision_attempt": revision_count + 1,
                        "tool_calls": full_trace["tool_calls"],
                        "reasoning_steps": len(full_trace["reasoning"]),
                    },
                )

                collaboration_log.append({
                    "step": "editor_review",
                    "attempt": revision_count + 1,
                    "tool_calls": full_trace["tool_calls"],
                    "response_preview": curator_response[:500] if curator_response else None,
                })

                # Check if Editor approved (look for approval indicators in response)
                if curator_response:
                    response_lower = curator_response.lower()
                    if "approve" in response_lower or "looks good" in response_lower or "solid" in response_lower:
                        editor_approved = True
                        logger.info("Editor approved the brief!")
                        collaboration_log.append({"step": "editor_approved"})
                    elif "revise" in response_lower or "needs work" in response_lower or "problem" in response_lower:
                        logger.info("Editor requested revisions...")
                        revision_count += 1

                        # Ask Curator to revise based on feedback
                        if revision_count < max_revisions:
                            revise_prompt = f"""The Editor had feedback. Revise your recommendations.

Their feedback: {curator_response[:2000]}

Update your brief to address their concerns. Use web_search if you need more research.
Then generate updated recommendations as JSON."""

                            revise_response = client.agents.messages.create(
                                agent_id=agent_id,
                                messages=[{"role": "user", "content": revise_prompt}],
                            )

                            # Update brief with revisions
                            revise_result = self._extract_response(revise_response)
                            if revise_result:
                                try:
                                    json_start = revise_result.find('[')
                                    json_end = revise_result.rfind(']') + 1
                                    if json_start >= 0 and json_end > json_start:
                                        new_recommendations = json.loads(revise_result[json_start:json_end])
                                        # Update brief in database
                                        async with SessionLocal() as db:
                                            brief = await db.get(ProductionBrief, brief.id)
                                            if brief:
                                                brief.recommendations = new_recommendations
                                                await db.commit()
                                        collaboration_log.append({
                                            "step": "revision_complete",
                                            "new_recommendation_count": len(new_recommendations),
                                        })
                                except json.JSONDecodeError:
                                    pass
                    else:
                        # Unclear response, try one more time
                        revision_count += 1

            # Step 4: If approved (or max revisions), optionally send to Architect
            final_status = "approved" if editor_approved else "max_revisions_reached"
            collaboration_log.append({
                "step": "workflow_complete",
                "status": final_status,
                "total_revisions": revision_count,
            })

            # Log activity
            await self._log_activity(
                action="collaborative_production",
                details={
                    "status": final_status,
                    "brief_id": str(brief.id),
                    "revisions": revision_count,
                    "editor_approved": editor_approved,
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            return {
                "status": final_status,
                "brief_id": str(brief.id),
                "editor_approved": editor_approved,
                "revisions": revision_count,
                "collaboration_log": collaboration_log,
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        except Exception as e:
            logger.error(f"Collaborative production failed: {e}", exc_info=True)
            collaboration_log.append({"step": "error", "message": str(e)})
            return {
                "status": "error",
                "error": str(e),
                "collaboration_log": collaboration_log,
            }

    async def wake(self, context: dict | None = None) -> dict:
        """Wake the Curator. They decide what to do from their identity.

        No explicit instructions like "research trends" or "give world ideas".
        The agent acts based on who they are and what they remember.

        Args:
            context: Optional external info (platform state, time since last wake)

        Returns:
            dict with actions taken, world ideas found, full trace
        """
        start_time = time.time()

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Gather platform context if not provided
            if context is None:
                context = {}

            # Get platform stats for context
            async with SessionLocal() as db:
                world_count = await db.execute(
                    select(func.count()).select_from(World).where(World.is_active == True)
                )
                context["total_worlds"] = world_count.scalar() or 0

                pending_briefs = await db.execute(
                    select(func.count())
                    .select_from(ProductionBrief)
                    .where(ProductionBrief.status == BriefStatus.PENDING)
                )
                context["pending_briefs"] = pending_briefs.scalar() or 0

                # Get last activity
                last_activity = await db.execute(
                    select(AgentActivity)
                    .where(AgentActivity.agent_type == AgentType.PRODUCTION)
                    .order_by(AgentActivity.timestamp.desc())
                    .limit(1)
                )
                activity = last_activity.scalar_one_or_none()
                if activity:
                    context["last_activity"] = f"{activity.action} at {activity.timestamp.isoformat()}"
                else:
                    context["last_activity"] = "No previous activity"

            # The wake prompt - minimal, identity-based
            # Not "research trends" or "give me world ideas"
            # Just an invitation to act as themselves
            wake_prompt = f"""It's a new day. You're waking up.

Platform status: {context.get('total_worlds', 0)} worlds exist, {context.get('pending_briefs', 0)} briefs pending.
Last activity: {context.get('last_activity', 'Unknown')}

What's on your mind? What do you want to do?"""

            logger.info("Waking Curator...")

            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": wake_prompt}],
            )

            # Extract full trace for observability
            full_trace = self._extract_full_trace(response)
            response_text = self._extract_response(response)

            # Analyze what the agent decided to do
            actions_taken = []
            world_ideas = []

            # Check if they used tools
            for tool_call in full_trace.get("tool_calls", []):
                tool_name = tool_call.get("name", "")
                actions_taken.append({
                    "type": "tool_call",
                    "tool": tool_name,
                    "arguments": tool_call.get("arguments", ""),
                })

                # If they searched for something, note it
                if tool_name == "web_search":
                    actions_taken[-1]["action"] = "researched"

            # Try to extract any world ideas from the response
            if response_text:
                # Simple heuristic: look for JSON arrays or structured ideas
                if "[" in response_text and "]" in response_text:
                    try:
                        json_start = response_text.find("[")
                        json_end = response_text.rfind("]") + 1
                        if json_start >= 0 and json_end > json_start:
                            potential_ideas = json.loads(response_text[json_start:json_end])
                            if isinstance(potential_ideas, list):
                                world_ideas = potential_ideas
                    except json.JSONDecodeError:
                        pass

            # Log trace
            await log_trace(
                agent_type=AgentType.PRODUCTION,
                operation="wake",
                prompt=wake_prompt,
                response=response_text,
                model=self.MODEL,
                duration_ms=int((time.time() - start_time) * 1000),
                parsed_output={
                    "actions_taken": actions_taken,
                    "world_ideas_count": len(world_ideas),
                    "reasoning_steps": len(full_trace.get("reasoning", [])),
                    "tool_calls": full_trace.get("tool_calls", []),
                    "tool_results": full_trace.get("tool_results", []),
                    "full_reasoning": full_trace.get("reasoning", []),
                },
            )

            # Log activity
            await self._log_activity(
                action="woke_up",
                details={
                    "context": context,
                    "actions_taken_count": len(actions_taken),
                    "used_tools": len(full_trace.get("tool_calls", [])) > 0,
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(f"Curator woke up, took {len(actions_taken)} actions")

            return {
                "status": "awake",
                "response": response_text,
                "actions_taken": actions_taken,
                "world_ideas": world_ideas,
                "context": context,
                "trace": {
                    "reasoning": full_trace.get("reasoning", []),
                    "tool_calls": full_trace.get("tool_calls", []),
                    "tool_results": full_trace.get("tool_results", []),
                },
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        except Exception as e:
            logger.error(f"Curator wake failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "duration_ms": int((time.time() - start_time) * 1000),
            }

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
