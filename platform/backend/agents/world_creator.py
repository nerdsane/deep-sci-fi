"""World Creator Agent for Deep Sci-Fi platform.

The World Creator Agent transforms production briefs into complete,
coherent sci-fi worlds with:
- Plausible causal chains from 2026
- Detailed technology, society, and geography
- A cast of 4-6 dweller characters

Uses Opus 4.5 for deep, creative world-building.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from letta_client import Letta
from sqlalchemy import select

from db import (
    ProductionBrief,
    BriefStatus,
    World,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import get_world_creator_prompt, ANTI_CLICHE_RULES

logger = logging.getLogger(__name__)


@dataclass
class DwellerSpec:
    """Specification for a dweller character."""
    name: str
    age: int
    role: str
    background: str
    beliefs: list[str]
    memories: list[str]
    personality: str
    contradictions: str
    daily_life: str


@dataclass
class WorldSpec:
    """Complete specification for a new world."""
    name: str
    premise: str
    year_setting: int
    causal_chain: list[dict]
    technology: dict
    society: dict
    geography: dict
    dweller_specs: list[DwellerSpec]
    validation_notes: list[str] = field(default_factory=list)


class WorldCreatorAgent:
    """World Creator Agent - transforms briefs into complete worlds.

    Uses Opus 4.5 for high-quality, coherent world-building.
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
        """Ensure world creator agent exists, create if not."""
        if self._agent_id:
            return self._agent_id

        client = self._get_client()
        agent_name = "world_creator_agent"

        # Check if agent exists
        agents_list = client.agents.list()
        for agent in agents_list:
            if agent.name == agent_name:
                self._agent_id = agent.id
                logger.info(f"Found existing world creator agent: {self._agent_id}")
                return self._agent_id

        # Create new agent
        system_prompt = get_world_creator_prompt()

        agent = client.agents.create(
            name=agent_name,
            model=self.MODEL,
            embedding="openai/text-embedding-ada-002",
            system=system_prompt,
        )
        self._agent_id = agent.id
        logger.info(f"Created world creator agent: {self._agent_id}")
        return self._agent_id

    async def create_world_from_brief(
        self,
        brief: ProductionBrief,
        recommendation_index: int = 0,
    ) -> WorldSpec:
        """Create a complete world from a production brief.

        Args:
            brief: The production brief with recommendations
            recommendation_index: Which recommendation to use (0-indexed)

        Returns:
            Complete WorldSpec ready for database insertion
        """
        start_time = time.time()

        if not brief.recommendations or recommendation_index >= len(brief.recommendations):
            raise ValueError(f"Invalid recommendation index: {recommendation_index}")

        recommendation = brief.recommendations[recommendation_index]

        try:
            agent_id = await self._ensure_agent()
            client = self._get_client()

            # Update brief status
            async with SessionLocal() as db:
                result = await db.execute(
                    select(ProductionBrief).where(ProductionBrief.id == brief.id)
                )
                db_brief = result.scalar_one()
                db_brief.status = BriefStatus.CREATING
                db_brief.selected_recommendation = recommendation_index
                await db.commit()

            # Step 1: Generate premise and causal chain
            premise_prompt = f"""Create a world based on this recommendation:

THEME: {recommendation.get('theme', '')}
PREMISE SKETCH: {recommendation.get('premise_sketch', '')}
CORE QUESTION: {recommendation.get('core_question', '')}
RATIONALE: {recommendation.get('rationale', '')}

First, develop:
1. A refined, compelling premise (2-3 paragraphs)
2. A specific year setting (2040-2150)
3. A detailed causal chain from 2026 to that year

Return as JSON:
{{
  "name": "World name (culturally appropriate, no Neo-anything)",
  "premise": "Full premise",
  "year_setting": 2075,
  "causal_chain": [
    {{"year": 2026, "event": "...", "cause": "...", "consequence": "..."}}
  ]
}}

CRITICAL: Avoid all cliches listed in your instructions. The causal chain must be PLAUSIBLE."""

            logger.info("Generating world premise and causal chain...")
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": premise_prompt}],
            )

            premise_result = self._extract_json(self._extract_response(response))
            if not premise_result:
                raise ValueError("Failed to generate world premise")

            # Step 2: Define technology, society, geography
            details_prompt = f"""Now define the world's systems for {premise_result.get('name', 'this world')}:

PREMISE: {premise_result.get('premise', '')}
YEAR: {premise_result.get('year_setting', 2075)}
CAUSAL CHAIN: {json.dumps(premise_result.get('causal_chain', []), indent=2)}

Define:
1. TECHNOLOGY: What exists? What are its COSTS and LIMITATIONS?
2. SOCIETY: How do people live, work, form relationships?
3. GEOGRAPHY: What has changed? Major locations?

Return as JSON:
{{
  "technology": {{
    "key_technologies": [...],
    "limitations": [...],
    "costs": [...],
    "daily_tech": "..."
  }},
  "society": {{
    "structure": "...",
    "work": "...",
    "relationships": "...",
    "culture": "..."
  }},
  "geography": {{
    "changes": [...],
    "key_locations": [...],
    "environment": "..."
  }}
}}

Be SPECIFIC. Technology must have real costs and limitations."""

            logger.info("Generating world details...")
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": details_prompt}],
            )

            details_result = self._extract_json(self._extract_response(response))
            if not details_result:
                details_result = {"technology": {}, "society": {}, "geography": {}}

            # Step 3: Create dweller cast
            dwellers_prompt = f"""Create 4-6 dweller characters for {premise_result.get('name', 'this world')}.

WORLD: {premise_result.get('premise', '')}
YEAR: {premise_result.get('year_setting', 2075)}
TECHNOLOGY: {json.dumps(details_result.get('technology', {}), indent=2)}
SOCIETY: {json.dumps(details_result.get('society', {}), indent=2)}

CRITICAL REQUIREMENTS:
1. Names must be culturally appropriate for the setting (NOT mix-and-match cultures)
2. Each character must have CONTRADICTIONS (internal conflicts)
3. Backgrounds must reflect LIVING in this world, not just observing it
4. No archetypes (no "grizzled veteran", "idealistic youth", etc.)

Return as JSON array:
[
  {{
    "name": "Culturally appropriate name",
    "age": 35,
    "role": "Their function in society",
    "background": "2-3 sentences of history",
    "beliefs": ["3-5 core beliefs shaped by this world"],
    "memories": ["3-5 formative experiences"],
    "personality": "Brief personality description",
    "contradictions": "What internal conflicts do they have?",
    "daily_life": "What does a typical day look like?"
  }}
]

Create 4-6 diverse characters who feel REAL, not like sci-fi archetypes."""

            logger.info("Generating dweller cast...")
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": dwellers_prompt}],
            )

            dwellers_result = self._extract_json(self._extract_response(response))
            if not isinstance(dwellers_result, list):
                dwellers_result = []

            # Step 4: Validate against anti-cliche rules
            validation_notes = await self._validate_world(
                name=premise_result.get("name", ""),
                premise=premise_result.get("premise", ""),
                dwellers=dwellers_result,
            )

            # Build final WorldSpec
            world_spec = WorldSpec(
                name=premise_result.get("name", "Unnamed World"),
                premise=premise_result.get("premise", ""),
                year_setting=premise_result.get("year_setting", 2075),
                causal_chain=premise_result.get("causal_chain", []),
                technology=details_result.get("technology", {}),
                society=details_result.get("society", {}),
                geography=details_result.get("geography", {}),
                dweller_specs=[
                    DwellerSpec(
                        name=d.get("name", "Unknown"),
                        age=d.get("age", 35),
                        role=d.get("role", "Unknown"),
                        background=d.get("background", ""),
                        beliefs=d.get("beliefs", []),
                        memories=d.get("memories", []),
                        personality=d.get("personality", ""),
                        contradictions=d.get("contradictions", ""),
                        daily_life=d.get("daily_life", ""),
                    )
                    for d in dwellers_result
                ],
                validation_notes=validation_notes,
            )

            # Log activity
            await self._log_activity(
                action="created_world_spec",
                details={
                    "brief_id": str(brief.id),
                    "world_name": world_spec.name,
                    "dweller_count": len(world_spec.dweller_specs),
                    "causal_chain_length": len(world_spec.causal_chain),
                    "validation_notes": validation_notes,
                },
                duration_ms=int((time.time() - start_time) * 1000),
            )

            logger.info(f"Created world spec: {world_spec.name} with {len(world_spec.dweller_specs)} dwellers")
            return world_spec

        except Exception as e:
            # Update brief status on failure
            async with SessionLocal() as db:
                result = await db.execute(
                    select(ProductionBrief).where(ProductionBrief.id == brief.id)
                )
                db_brief = result.scalar_one()
                db_brief.status = BriefStatus.FAILED
                db_brief.error_message = str(e)
                await db.commit()

            logger.error(f"World creation failed: {e}", exc_info=True)
            raise

    async def _validate_world(
        self,
        name: str,
        premise: str,
        dwellers: list[dict],
    ) -> list[str]:
        """Validate a world against anti-cliche rules.

        Returns list of warnings/issues found.
        """
        notes = []

        # Check name
        name_lower = name.lower()
        if "neo-" in name_lower or "neo " in name_lower:
            notes.append("WARNING: Name contains 'Neo-' pattern")
        if any(f"sector-{i}" in name_lower or f"district-{i}" in name_lower for i in range(20)):
            notes.append("WARNING: Name contains numbered district pattern")

        # Check premise for banned words
        banned_words = [
            "bustling", "cutting-edge", "sleek", "sprawling", "gleaming",
            "dystopian", "utopian", "neural", "synth", "cyber"
        ]
        premise_lower = premise.lower()
        for word in banned_words:
            if word in premise_lower:
                notes.append(f"WARNING: Premise contains banned word '{word}'")

        # Check dweller names for cultural mishmash
        # This is a simplified check - could be enhanced with name origin databases
        for dweller in dwellers:
            dweller_name = dweller.get("name", "")
            # Check for obvious cultural mixing (this is a heuristic)
            # In a real implementation, you'd use a more sophisticated approach
            if dweller_name and len(dweller_name.split()) >= 2:
                # Log for review
                notes.append(f"REVIEW: Verify cultural coherence of name '{dweller_name}'")

        # Check for archetype patterns in roles/backgrounds
        archetype_patterns = [
            "grizzled", "veteran", "idealistic", "young rebel",
            "corrupt official", "wise mentor", "chosen one"
        ]
        for dweller in dwellers:
            background = (dweller.get("background", "") + " " + dweller.get("role", "")).lower()
            for pattern in archetype_patterns:
                if pattern in background:
                    notes.append(f"WARNING: Dweller '{dweller.get('name')}' may be archetype: '{pattern}'")

        return notes

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

    def _extract_json(self, text: str | None) -> dict | list | None:
        """Extract JSON from text response."""
        if not text:
            return None

        try:
            # Try to find JSON object or array
            # Look for outermost { } or [ ]
            brace_start = text.find('{')
            bracket_start = text.find('[')

            if brace_start >= 0 and (bracket_start < 0 or brace_start < bracket_start):
                # Find matching closing brace
                depth = 0
                for i, c in enumerate(text[brace_start:], brace_start):
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[brace_start:i+1])
            elif bracket_start >= 0:
                # Find matching closing bracket
                depth = 0
                for i, c in enumerate(text[bracket_start:], bracket_start):
                    if c == '[':
                        depth += 1
                    elif c == ']':
                        depth -= 1
                        if depth == 0:
                            return json.loads(text[bracket_start:i+1])

            # Fallback: try parsing entire text
            return json.loads(text)

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON: {e}")
            return None

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
                    agent_type=AgentType.WORLD_CREATOR,
                    agent_id="world_creator_agent",
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
_world_creator: WorldCreatorAgent | None = None


def get_world_creator() -> WorldCreatorAgent:
    """Get the world creator agent instance."""
    global _world_creator
    if _world_creator is None:
        _world_creator = WorldCreatorAgent()
    return _world_creator
