"""World Creator Agent for Deep Sci-Fi platform.

Creates worlds with:
- World name
- World document (markdown describing the world)
- Dweller cast (name + system prompt for each)
"""

import logging
import os
import time
from dataclasses import dataclass, field
from uuid import UUID

from anthropic import Anthropic
from sqlalchemy import select

from db import (
    ProductionBrief,
    BriefStatus,
    AgentActivity,
    AgentType,
)
from db.database import SessionLocal
from .prompts import get_world_creator_prompt, ANTI_CLICHE_RULES

logger = logging.getLogger(__name__)


@dataclass
class DwellerSpec:
    """A dweller: name and system prompt."""
    name: str
    system_prompt: str


@dataclass
class WorldSpec:
    """A world: name, document, and dwellers."""
    name: str
    document: str  # Full markdown describing the world
    year_setting: int
    dwellers: list[DwellerSpec]


class WorldCreatorAgent:
    """Creates worlds from briefs.

    Uses Anthropic API directly for simplicity.
    """

    def __init__(self):
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic()
        return self._client

    async def create_world_from_brief(
        self,
        brief: ProductionBrief,
        recommendation_index: int = 0,
    ) -> WorldSpec:
        """Create a world from a production brief."""
        start_time = time.time()

        if not brief.recommendations or recommendation_index >= len(brief.recommendations):
            raise ValueError(f"Invalid recommendation index: {recommendation_index}")

        recommendation = brief.recommendations[recommendation_index]
        client = self._get_client()

        # Step 1: Generate world name and document
        world_prompt = f"""Create a sci-fi world based on this brief:

THEME: {recommendation.get('theme', '')}
PREMISE: {recommendation.get('premise_sketch', '')}
CORE QUESTION: {recommendation.get('core_question', '')}

Write a world document in markdown. Include:
- The world's name (first line, as # heading)
- Year setting
- What happened (causal chain from 2026)
- How society works now
- Technology and its limitations
- Daily life details

{ANTI_CLICHE_RULES}

Write naturally. No JSON. Just markdown."""

        logger.info("Generating world document...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": world_prompt}]
        )

        world_doc = response.content[0].text

        # Extract name from first heading
        lines = world_doc.strip().split('\n')
        world_name = "Unnamed World"
        for line in lines:
            if line.startswith('# '):
                world_name = line[2:].strip()
                break

        # Extract year if mentioned
        year_setting = 2075  # default
        import re
        year_match = re.search(r'\b(20[3-9]\d|21\d\d)\b', world_doc)
        if year_match:
            year_setting = int(year_match.group(1))

        # Step 2: Generate dwellers
        dwellers_prompt = f"""Based on this world, create 4-5 characters who live there.

WORLD:
{world_doc}

For each character, write:
---
NAME: [Full name]
SYSTEM PROMPT:
[Complete system prompt for this character as an AI agent. Include their background, beliefs, personality, and how they should behave in conversations. Write in second person ("You are...")]
---

Make them diverse in age, role, and perspective. Give them contradictions - no one is purely good or purely evil, optimistic or pessimistic.

{ANTI_CLICHE_RULES}"""

        logger.info("Generating dweller cast...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": dwellers_prompt}]
        )

        dwellers_text = response.content[0].text
        dwellers = self._parse_dwellers(dwellers_text)

        if not dwellers:
            raise ValueError("Failed to generate dwellers")

        # Log activity
        await self._log_activity(
            action="created_world",
            details={
                "brief_id": str(brief.id),
                "world_name": world_name,
                "dweller_count": len(dwellers),
            },
            duration_ms=int((time.time() - start_time) * 1000),
        )

        logger.info(f"Created world: {world_name} with {len(dwellers)} dwellers")

        return WorldSpec(
            name=world_name,
            document=world_doc,
            year_setting=year_setting,
            dwellers=dwellers,
        )

    def _parse_dwellers(self, text: str) -> list[DwellerSpec]:
        """Parse dwellers from text format."""
        dwellers = []

        # Split by --- separator
        sections = text.split('---')

        for section in sections:
            section = section.strip()
            if not section or 'NAME:' not in section:
                continue

            # Extract name
            name = ""
            system_prompt = ""

            lines = section.split('\n')
            in_prompt = False
            prompt_lines = []

            for line in lines:
                if line.startswith('NAME:'):
                    name = line[5:].strip()
                elif line.startswith('SYSTEM PROMPT:'):
                    in_prompt = True
                elif in_prompt:
                    prompt_lines.append(line)

            system_prompt = '\n'.join(prompt_lines).strip()

            if name and system_prompt:
                dwellers.append(DwellerSpec(name=name, system_prompt=system_prompt))

        return dwellers

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
                    agent_type=AgentType.WORLD_CREATOR,
                    agent_id="world_creator",
                    action=action,
                    details=details,
                    world_id=world_id,
                    duration_ms=duration_ms,
                )
                db.add(activity)
                await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log activity: {e}")


_world_creator: WorldCreatorAgent | None = None


def get_world_creator() -> WorldCreatorAgent:
    """Get the world creator instance."""
    global _world_creator
    if _world_creator is None:
        _world_creator = WorldCreatorAgent()
    return _world_creator
